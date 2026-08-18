"""Windows providers ordered by reliability; semantic UIA before vision."""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from core.operator.semantic import SemanticControl, SemanticSelector
from core.security.atomic import atomic_write_text


@dataclass(frozen=True)
class ProviderResult:
    ok: bool
    value: Any = None
    error: str | None = None
    provider: str = ""
    kind: str = "IMPLEMENTED"
    observed: bool = False


class WindowsAutomationProvider:
    name = "provider"
    ladder_level = 99

    def supports(self, operation: str) -> bool:
        return False

    def invoke(self, operation: str, **kwargs: Any) -> ProviderResult:
        return ProviderResult(False, error=f"{operation} unsupported", provider=self.name, kind="UNSUPPORTED")


class ProviderChain:
    """Native/COM → CLI/config → UIA → DOM → vision; no coordinate provider."""

    def __init__(self, providers: list[WindowsAutomationProvider]) -> None:
        self.providers = sorted(providers, key=lambda item: item.ladder_level)

    def invoke(self, operation: str, **kwargs: Any) -> ProviderResult:
        errors: list[str] = []
        for provider in self.providers:
            if not provider.supports(operation):
                continue
            result = provider.invoke(operation, **kwargs)
            if result.ok:
                return ProviderResult(True, result.value, provider=provider.name,
                                     kind=result.kind, observed=result.observed)
            errors.append(result.error or provider.name)
        return ProviderResult(False, error="; ".join(errors) or f"no provider for {operation}", kind="UNSUPPORTED")


class NativeWindowsProvider(WindowsAutomationProvider):
    """Native API, process, filesystem and registry primitives."""

    name = "native_windows"
    ladder_level = 1
    _operations = {
        "process.list", "process.launch", "process.stop", "window.list", "window.active",
        "window.inspect", "window.focus", "file.read", "file.write", "file.copy", "file.move",
        "registry.read", "registry.write", "service.inspect", "shell.run",
        "installer.detect", "installer.run", "app.discover",
    }

    def supports(self, operation: str) -> bool:
        return operation in self._operations

    def invoke(self, operation: str, **kwargs: Any) -> ProviderResult:
        try:
            method = getattr(self, operation.replace(".", "_"))
            value = method(**kwargs)
            observed = bool(isinstance(value, dict) and value.get("observed"))
            return ProviderResult(True, value, provider=self.name, observed=observed)
        except Exception as exc:
            return ProviderResult(False, error=f"{type(exc).__name__}: {exc}", provider=self.name)

    @staticmethod
    def process_list() -> list[dict[str, Any]]:
        import psutil
        return [item.info for item in psutil.process_iter(["pid", "name", "exe", "status"])]

    @staticmethod
    def process_launch(command: list[str], cwd: str | None = None) -> dict[str, Any]:
        if not command or not isinstance(command, list):
            raise ValueError("command must be a non-empty argument list")
        process = subprocess.Popen(command, cwd=cwd, shell=False)
        started = process.poll() is None
        return {"pid": process.pid, "command": list(command), "started": started, "observed": started}

    @staticmethod
    def process_stop(pid: int) -> dict[str, Any]:
        import psutil
        process = psutil.Process(int(pid))
        process.terminate()
        process.wait(timeout=10)
        stopped = not process.is_running()
        if not stopped:
            raise RuntimeError("process still running after terminate")
        return {"pid": int(pid), "stopped": stopped, "observed": True}

    @staticmethod
    def window_list() -> list[dict[str, Any]]:
        import win32gui
        import win32process
        result: list[dict[str, Any]] = []

        def collect(handle: int, _context: Any) -> None:
            if not win32gui.IsWindowVisible(handle):
                return
            title = win32gui.GetWindowText(handle).strip()
            if not title:
                return
            _thread, process_id = win32process.GetWindowThreadProcessId(handle)
            result.append({"handle": handle, "title": title, "process_id": process_id})

        win32gui.EnumWindows(collect, None)
        return result

    @staticmethod
    def window_active() -> dict[str, Any]:
        import win32gui
        import win32process
        handle = win32gui.GetForegroundWindow()
        _thread, process_id = win32process.GetWindowThreadProcessId(handle)
        return {"handle": handle, "title": win32gui.GetWindowText(handle), "process_id": process_id}

    @classmethod
    def window_inspect(cls, title: str | None = None) -> dict[str, Any]:
        if not title:
            return cls.window_active()
        query = title.casefold()
        match = next((item for item in cls.window_list() if query in item["title"].casefold()), None)
        if match is None:
            raise ValueError(f"window not found: {title}")
        return match

    @classmethod
    def window_focus(cls, title: str | None = None, handle: int | None = None) -> dict[str, Any]:
        import win32con
        import win32gui
        target = int(handle or 0)
        if not target:
            target = int(cls.window_inspect(title)["handle"])
        if win32gui.IsIconic(target):
            win32gui.ShowWindow(target, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(target)
        return {"handle": target, "title": win32gui.GetWindowText(target), "focused": True}

    @staticmethod
    def file_read(path: str) -> str:
        return Path(path).read_text(encoding="utf-8")

    @staticmethod
    def file_write(path: str, content: str) -> str:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(target, content)
        written = target.read_text(encoding="utf-8") == content
        if not written:
            raise IOError("write verification mismatch")
        return {"path": str(target), "written": True, "observed": True}

    @staticmethod
    def file_copy(source: str, destination: str) -> str:
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        return str(shutil.copy2(source, target))

    @staticmethod
    def file_move(source: str, destination: str) -> str:
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        moved_path = Path(shutil.move(source, target))
        if not moved_path.exists():
            raise IOError("move verification mismatch")
        return {"path": str(moved_path), "moved": True, "observed": True}

    @staticmethod
    def registry_read(root: str, path: str, name: str) -> Any:
        import winreg
        hive = getattr(winreg, root)
        with winreg.OpenKey(hive, path) as key:
            return winreg.QueryValueEx(key, name)[0]

    @staticmethod
    def registry_write(root: str, path: str, name: str, value: Any) -> dict[str, Any]:
        import winreg
        hive = getattr(winreg, root)
        with winreg.CreateKey(hive, path) as key:
            previous = None
            try:
                previous = winreg.QueryValueEx(key, name)[0]
            except OSError:
                pass
            kind = winreg.REG_DWORD if isinstance(value, int) else winreg.REG_SZ
            winreg.SetValueEx(key, name, 0, kind, value)
            observed = winreg.QueryValueEx(key, name)[0]
        return {"written": observed == value, "previous": previous, "value": observed, "observed": observed == value}

    @staticmethod
    def service_inspect(name: str) -> dict[str, Any]:
        done = subprocess.run(
            ["sc", "query", name], capture_output=True, text=True, timeout=10, check=False, shell=False,
        )
        return {"exit_code": done.returncode, "output": done.stdout}

    @staticmethod
    def shell_run(command: list[str], cwd: str | None = None, timeout: float = 60) -> dict[str, Any]:
        if not command or not isinstance(command, list):
            raise ValueError("command must be a non-empty argument list")
        done = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True,
            timeout=max(1, float(timeout)), shell=False, check=False,
        )
        return {"exit_code": done.returncode, "stdout": done.stdout, "stderr": done.stderr}

    @staticmethod
    def installer_detect(path: str) -> dict[str, Any]:
        suffix = Path(path).suffix.casefold()
        kind = {".msi": "msi", ".exe": "exe", ".zip": "zip"}.get(suffix, "unknown")
        return {"path": path, "kind": kind, "supported": kind != "unknown"}

    @staticmethod
    def installer_run(path: str, arguments: list[str] | None = None) -> dict[str, Any]:
        target = Path(path)
        if not target.is_file():
            raise FileNotFoundError(path)
        command = ["msiexec.exe", "/i", str(target), *(arguments or [])] if target.suffix.casefold() == ".msi" else [
            str(target), *(arguments or []),
        ]
        process = subprocess.Popen(command, shell=False)
        return {"pid": process.pid, "command": command, "started": process.poll() is None,
                "verification_required": True, "observed": False}

    @staticmethod
    def app_discover(name: str) -> dict[str, Any]:
        resolved = shutil.which(name)
        return {"name": name, "path": resolved, "found": bool(resolved)}


class WinAppProvider(WindowsAutomationProvider):
    """Optional Microsoft WinApp CLI adapter; never a hard dependency."""

    name, ladder_level = "winapp", 2

    def supports(self, operation: str) -> bool:
        return operation.startswith("ui.") and shutil.which("winapp") is not None


class UIAutomationProvider(WindowsAutomationProvider):
    """Real Windows UI Automation provider backed by pywinauto's UIA backend."""

    name, ladder_level = "uia", 4
    _operations = {
        "ui.tree", "ui.find", "ui.inspect", "ui.invoke", "ui.set_value",
        "ui.select", "ui.toggle", "ui.scroll", "ui.wait_for",
    }

    def __init__(self, desktop_factory: Callable[[], Any] | None = None) -> None:
        self._desktop_factory = desktop_factory

    def supports(self, operation: str) -> bool:
        if operation not in self._operations:
            return False
        if self._desktop_factory is not None:
            return True
        try:
            import pywinauto  # noqa: F401
            return True
        except ImportError:
            return False

    def invoke(self, operation: str, **kwargs: Any) -> ProviderResult:
        try:
            method = getattr(self, operation.replace(".", "_"))
            value = method(**kwargs)
            observed = bool(isinstance(value, dict) and (
                value.get("observed") or value.get("found") or value.get("invoked")
                or value.get("set") or value.get("selected") or value.get("toggled")
            ))
            return ProviderResult(True, value, provider=self.name, observed=observed)
        except Exception as exc:
            return ProviderResult(False, error=f"{type(exc).__name__}: {exc}", provider=self.name)

    def _desktop(self) -> Any:
        if self._desktop_factory is not None:
            return self._desktop_factory()
        from pywinauto import Desktop
        return Desktop(backend="uia")

    def _window(self, *, window_title: str | None = None, process_id: int | None = None,
                handle: int | None = None) -> Any:
        windows = list(self._desktop().windows())
        match = None
        if handle is not None:
            match = next((item for item in windows
                          if int(getattr(item.element_info, "handle", 0) or 0) == int(handle)), None)
        elif process_id is not None:
            match = next((item for item in windows
                          if int(getattr(item.element_info, "process_id", 0) or 0) == int(process_id)), None)
        elif window_title:
            query = window_title.casefold()
            match = next((item for item in windows if query in self._name(item).casefold()), None)
        else:
            match = windows[0] if windows else None
        if match is None:
            raise LookupError(f"UIA window not found: {window_title or process_id or handle}")
        return match

    @staticmethod
    def _name(wrapper: Any) -> str:
        info = wrapper.element_info
        name = str(getattr(info, "name", "") or "")
        if name:
            return name
        method = getattr(wrapper, "window_text", None)
        return str(method() if callable(method) else "")

    def _node(self, wrapper: Any, hierarchy: tuple[str, ...] = (), *, depth: int = 0,
              max_depth: int = 8) -> SemanticControl:
        info = wrapper.element_info
        name = self._name(wrapper)
        control_type = str(getattr(info, "control_type", "") or "Custom")
        node_path = (*hierarchy, name or control_type)
        children: list[SemanticControl] = []
        if depth < max_depth:
            try:
                children = [self._node(child, node_path, depth=depth + 1, max_depth=max_depth)
                            for child in wrapper.children()]
            except Exception:
                children = []
        return SemanticControl(
            name=name,
            control_type=control_type,
            automation_id=str(getattr(info, "automation_id", "") or ""),
            class_name=str(getattr(info, "class_name", "") or ""),
            enabled=bool(getattr(info, "enabled", True)),
            visible=bool(getattr(info, "visible", True)),
            value=self._read_value(wrapper, control_type),
            process_id=int(getattr(info, "process_id", 0) or 0) or None,
            native_handle=int(getattr(info, "handle", 0) or 0) or None,
            hierarchy=hierarchy,
            children=children,
        )

    @staticmethod
    def _read_value(wrapper: Any, control_type: str) -> Any:
        attempts: list[str] = []
        if control_type.casefold() in {"checkbox", "radiobutton"}:
            attempts.append("get_toggle_state")
        attempts += ["get_value", "selected_text", "window_text"]
        for name in attempts:
            method = getattr(wrapper, name, None)
            if callable(method):
                try:
                    value = method()
                    if value not in (None, ""):
                        return value
                except Exception:
                    continue
        return None

    def _find_wrapper(self, selector: SemanticSelector | dict[str, Any], **window: Any) -> tuple[Any, SemanticControl]:
        root = self._window(**window)
        wrappers = [root]
        try:
            wrappers.extend(root.descendants())
        except Exception:
            wrappers.extend(root.children())
        nodes = [self._node(item, max_depth=0) for item in wrappers]
        match = SemanticControl("root", "Pane", children=nodes).find_best(selector)
        if match is None:
            raise LookupError(f"UIA control not found: {selector}")
        for wrapper, node in zip(wrappers, nodes):
            if node is match:
                return wrapper, node
        raise LookupError(f"UIA control wrapper unavailable: {selector}")

    def ui_tree(self, max_depth: int = 8, **window: Any) -> dict[str, Any]:
        return self._node(self._window(**window), max_depth=max(0, min(20, int(max_depth)))).to_dict()

    def ui_inspect(self, **window: Any) -> dict[str, Any]:
        return self.ui_tree(**window)

    def ui_find(self, selector: SemanticSelector | dict[str, Any], **window: Any) -> dict[str, Any]:
        _wrapper, node = self._find_wrapper(selector, **window)
        return node.to_dict()

    def ui_invoke(self, selector: SemanticSelector | dict[str, Any], **window: Any) -> dict[str, Any]:
        wrapper, node = self._find_wrapper(selector, **window)
        for method_name in ("invoke", "click", "select"):
            method = getattr(wrapper, method_name, None)
            if callable(method):
                method()
                return {"invoked": True, "control": node.to_dict(), "method": method_name}
        raise AttributeError(f"control has no semantic invoke pattern: {node.name}")

    def ui_set_value(self, selector: SemanticSelector | dict[str, Any], value: Any,
                     **window: Any) -> dict[str, Any]:
        wrapper, node = self._find_wrapper(selector, **window)
        for method_name in ("set_edit_text", "set_text", "set_value"):
            method = getattr(wrapper, method_name, None)
            if callable(method):
                method(value)
                return {"set": True, "value": self._read_value(wrapper, node.control_type),
                        "control": node.to_dict(), "method": method_name}
        raise AttributeError(f"control has no value pattern: {node.name}")

    def ui_select(self, selector: SemanticSelector | dict[str, Any], value: Any = None,
                  **window: Any) -> dict[str, Any]:
        wrapper, node = self._find_wrapper(selector, **window)
        for method_name in ("select", "select_item"):
            method = getattr(wrapper, method_name, None)
            if callable(method):
                method(value) if value is not None else method()
                return {"selected": True, "value": self._read_value(wrapper, node.control_type),
                        "control": node.to_dict(), "method": method_name}
        raise AttributeError(f"control has no selection pattern: {node.name}")

    def ui_toggle(self, selector: SemanticSelector | dict[str, Any], state: bool | None = None,
                  **window: Any) -> dict[str, Any]:
        wrapper, node = self._find_wrapper(selector, **window)
        current = bool(self._read_value(wrapper, node.control_type))
        wanted = (not current) if state is None else bool(state)
        if current != wanted:
            method = getattr(wrapper, "toggle", None) or getattr(wrapper, "click", None)
            if not callable(method):
                raise AttributeError(f"control has no toggle pattern: {node.name}")
            method()
        observed = bool(self._read_value(wrapper, node.control_type))
        return {"toggled": observed == wanted, "state": observed, "control": node.to_dict()}

    def ui_scroll(self, selector: SemanticSelector | dict[str, Any], direction: str = "down",
                  amount: str = "page", **window: Any) -> dict[str, Any]:
        wrapper, node = self._find_wrapper(selector, **window)
        method = getattr(wrapper, "scroll", None)
        if not callable(method):
            raise AttributeError(f"control has no scroll pattern: {node.name}")
        method(direction, amount)
        return {"scrolled": True, "direction": direction, "amount": amount,
                "control": node.to_dict()}

    def ui_wait_for(self, selector: SemanticSelector | dict[str, Any], timeout: float = 10,
                    interval: float = 0.2, **window: Any) -> dict[str, Any]:
        deadline = time.monotonic() + max(0, float(timeout))
        error = "control not found"
        while time.monotonic() <= deadline:
            try:
                _wrapper, node = self._find_wrapper(selector, **window)
                if node.visible and node.enabled:
                    return {"found": True, "control": node.to_dict()}
            except Exception as exc:
                error = str(exc)
            time.sleep(max(0.01, float(interval)))
        raise TimeoutError(error)


class VisionFallbackProvider(WindowsAutomationProvider):
    name, ladder_level = "vision", 6

    def __init__(self, capture: Any = None) -> None:
        self.capture = capture

    def supports(self, operation: str) -> bool:
        return operation == "ui.inspect" and self.capture is not None

    def invoke(self, operation: str, **kwargs: Any) -> ProviderResult:
        try:
            return ProviderResult(True, self.capture(**kwargs), provider=self.name)
        except Exception as exc:
            return ProviderResult(False, error=str(exc), provider=self.name)


class WindowsCapabilityLayer:
    """Stable Sprint 10 vocabulary over the ordered provider chain."""

    def __init__(self, chain: ProviderChain | None = None) -> None:
        self.chain = chain or ProviderChain([
            NativeWindowsProvider(), WinAppProvider(), UIAutomationProvider(),
            VisionFallbackProvider(),
        ])

    @classmethod
    def with_uia_provider(cls, provider: UIAutomationProvider) -> "WindowsCapabilityLayer":
        return cls(ProviderChain([NativeWindowsProvider(), provider]))

    def _call(self, operation: str, **kwargs: Any) -> ProviderResult:
        return self.chain.invoke(operation, **kwargs)

    def process_list(self): return self._call("process.list")
    def process_launch(self, command, cwd=None): return self._call("process.launch", command=command, cwd=cwd)
    def process_stop(self, pid): return self._call("process.stop", pid=pid)
    def window_list(self): return self._call("window.list")
    def window_active(self): return self._call("window.active")
    def window_inspect(self, **kwargs): return self._call("window.inspect", **kwargs)
    def window_focus(self, **kwargs): return self._call("window.focus", **kwargs)
    def file_read(self, path): return self._call("file.read", path=path)
    def file_write(self, path, content): return self._call("file.write", path=path, content=content)
    def file_copy(self, source, destination): return self._call("file.copy", source=source, destination=destination)
    def file_move(self, source, destination): return self._call("file.move", source=source, destination=destination)
    def registry_read(self, root, path, name): return self._call("registry.read", root=root, path=path, name=name)
    def registry_write(self, root, path, name, value): return self._call("registry.write", root=root, path=path, name=name, value=value)
    def service_inspect(self, name): return self._call("service.inspect", name=name)
    def shell_run(self, command, cwd=None, timeout=60): return self._call("shell.run", command=command, cwd=cwd, timeout=timeout)
    def installer_detect(self, path): return self._call("installer.detect", path=path)
    def installer_run(self, path, arguments=None): return self._call("installer.run", path=path, arguments=arguments)
    def app_discover(self, name): return self._call("app.discover", name=name)
    def ui_tree(self, **kwargs): return self._call("ui.tree", **kwargs)
    def ui_inspect(self, **kwargs): return self._call("ui.inspect", **kwargs)
    def ui_find(self, **kwargs): return self._call("ui.find", **kwargs)
    def ui_invoke(self, **kwargs): return self._call("ui.invoke", **kwargs)
    def ui_set_value(self, **kwargs): return self._call("ui.set_value", **kwargs)
    def ui_select(self, **kwargs): return self._call("ui.select", **kwargs)
    def ui_toggle(self, **kwargs): return self._call("ui.toggle", **kwargs)
    def ui_scroll(self, **kwargs): return self._call("ui.scroll", **kwargs)
    def ui_wait_for(self, **kwargs): return self._call("ui.wait_for", **kwargs)
