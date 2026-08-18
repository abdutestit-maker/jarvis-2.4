"""Windows capability adapters ordered by reliability, not coordinates."""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProviderResult:
    ok: bool
    value: Any = None
    error: str | None = None
    provider: str = ""


class WindowsAutomationProvider:
    name = "provider"
    ladder_level = 99
    def supports(self, operation: str) -> bool: return False
    def invoke(self, operation: str, **kwargs: Any) -> ProviderResult:
        return ProviderResult(False, error=f"{operation} unsupported", provider=self.name)


class ProviderChain:
    """Native API → CLI → config → UIA → DOM → vision → coordinates."""

    def __init__(self, providers: list[WindowsAutomationProvider]) -> None:
        self.providers = sorted(providers, key=lambda item: item.ladder_level)

    def invoke(self, operation: str, **kwargs: Any) -> ProviderResult:
        errors = []
        for provider in self.providers:
            if not provider.supports(operation):
                continue
            result = provider.invoke(operation, **kwargs)
            if result.ok:
                return ProviderResult(True, result.value, provider=provider.name)
            errors.append(result.error or provider.name)
        return ProviderResult(False, error="; ".join(errors) or f"no provider for {operation}")


class NativeWindowsProvider(WindowsAutomationProvider):
    """Native/CLI primitives. Mutating calls are still gated by core.safety."""

    name = "native_windows"
    ladder_level = 1
    _operations = {
        "process.list", "process.launch", "process.stop", "window.list", "window.active",
        "window.inspect", "window.focus", "file.read", "file.write", "file.copy", "file.move",
        "registry.read", "registry.write", "service.inspect", "shell.run",
        "installer.detect", "installer.run", "app.discover",
    }

    def supports(self, operation: str) -> bool: return operation in self._operations

    def invoke(self, operation: str, **kwargs: Any) -> ProviderResult:
        try:
            method = getattr(self, operation.replace(".", "_"))
            return ProviderResult(True, method(**kwargs), provider=self.name)
        except Exception as exc:
            return ProviderResult(False, error=f"{type(exc).__name__}: {exc}", provider=self.name)

    @staticmethod
    def process_list() -> list[dict[str, Any]]:
        import psutil
        return [{"pid": item.info["pid"], "name": item.info.get("name", "")}
                for item in psutil.process_iter(["pid", "name"])]

    @staticmethod
    def process_launch(command: list[str], cwd: str | None = None) -> dict[str, Any]:
        proc = subprocess.Popen(command, cwd=cwd, shell=False)
        return {"pid": proc.pid, "command": command}

    @staticmethod
    def process_stop(pid: int) -> dict[str, Any]:
        import psutil
        psutil.Process(pid).terminate()
        return {"pid": pid, "stopped": True}

    @staticmethod
    def window_list() -> list[str]:
        import pygetwindow
        return [str(title) for title in pygetwindow.getAllTitles() if title]

    @staticmethod
    def window_active() -> str:
        import pygetwindow
        return str(getattr(pygetwindow.getActiveWindow(), "title", "") or "")

    def window_inspect(self) -> dict[str, Any]: return {"title": self.window_active()}

    @staticmethod
    def window_focus(title: str) -> dict[str, Any]:
        import pygetwindow
        matches = pygetwindow.getWindowsWithTitle(title)
        if not matches: raise ValueError(f"window not found: {title}")
        matches[0].activate()
        return {"focused": title}

    @staticmethod
    def file_read(path: str) -> str: return Path(path).read_text(encoding="utf-8")
    @staticmethod
    def file_write(path: str, content: str) -> str:
        target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8"); return str(target)
    @staticmethod
    def file_copy(source: str, destination: str) -> str:
        target = Path(destination); target.parent.mkdir(parents=True, exist_ok=True)
        return str(shutil.copy2(source, target))
    @staticmethod
    def file_move(source: str, destination: str) -> str:
        target = Path(destination); target.parent.mkdir(parents=True, exist_ok=True)
        return str(shutil.move(source, target))

    @staticmethod
    def registry_read(root: str, path: str, name: str) -> Any:
        import winreg
        hive = getattr(winreg, root)
        with winreg.OpenKey(hive, path) as key: return winreg.QueryValueEx(key, name)[0]

    @staticmethod
    def registry_write(root: str, path: str, name: str, value: Any) -> bool:
        import winreg
        hive = getattr(winreg, root)
        with winreg.CreateKey(hive, path) as key:
            kind = winreg.REG_DWORD if isinstance(value, int) else winreg.REG_SZ
            winreg.SetValueEx(key, name, 0, kind, value)
        return True

    @staticmethod
    def service_inspect(name: str) -> dict[str, Any]:
        done = subprocess.run(["sc", "query", name], capture_output=True, text=True,
                              timeout=10, check=False)
        return {"exit_code": done.returncode, "output": done.stdout}

    @staticmethod
    def shell_run(command: list[str], cwd: str | None = None) -> dict[str, Any]:
        done = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                              timeout=60, shell=False, check=False)
        return {"exit_code": done.returncode, "stdout": done.stdout, "stderr": done.stderr}

    @staticmethod
    def installer_detect(path: str) -> dict[str, Any]:
        suffix = Path(path).suffix.lower()
        return {"path": path, "kind": suffix.lstrip("."), "supported": suffix in {".msi", ".exe"}}
    def installer_run(self, path: str, arguments: list[str] | None = None) -> dict[str, Any]:
        return self.process_launch([path, *(arguments or [])])
    @staticmethod
    def app_discover(name: str) -> dict[str, Any]:
        resolved = shutil.which(name)
        return {"name": name, "path": resolved, "found": bool(resolved)}


class WinAppProvider(WindowsAutomationProvider):
    name, ladder_level = "winapp", 4
    def supports(self, operation: str) -> bool:
        return operation.startswith("ui.") and shutil.which("winapp") is not None


class UIAutomationProvider(WindowsAutomationProvider):
    name, ladder_level = "uia", 4
    def supports(self, operation: str) -> bool:
        if not operation.startswith("ui."): return False
        try:
            import uiautomation  # noqa: F401
            return True
        except ImportError: return False


class VisionFallbackProvider(WindowsAutomationProvider):
    name, ladder_level = "vision", 6
    def __init__(self, capture: Any = None) -> None: self.capture = capture
    def supports(self, operation: str) -> bool:
        return operation == "ui.inspect" and self.capture is not None
    def invoke(self, operation: str, **kwargs: Any) -> ProviderResult:
        try: return ProviderResult(True, self.capture(**kwargs), provider=self.name)
        except Exception as exc: return ProviderResult(False, error=str(exc), provider=self.name)


class WindowsCapabilityLayer:
    """Named Sprint 9 primitives backed by the reliability-ordered chain."""

    def __init__(self, chain: ProviderChain | None = None) -> None:
        self.chain = chain or ProviderChain([
            NativeWindowsProvider(), WinAppProvider(), UIAutomationProvider(),
            VisionFallbackProvider(),
        ])

    def _call(self, operation: str, **kwargs: Any) -> ProviderResult:
        return self.chain.invoke(operation, **kwargs)

    def process_list(self): return self._call("process.list")
    def process_launch(self, command, cwd=None): return self._call("process.launch", command=command, cwd=cwd)
    def process_stop(self, pid): return self._call("process.stop", pid=pid)
    def window_list(self): return self._call("window.list")
    def window_active(self): return self._call("window.active")
    def window_inspect(self): return self._call("window.inspect")
    def window_focus(self, title): return self._call("window.focus", title=title)
    def file_read(self, path): return self._call("file.read", path=path)
    def file_write(self, path, content): return self._call("file.write", path=path, content=content)
    def file_copy(self, source, destination): return self._call("file.copy", source=source, destination=destination)
    def file_move(self, source, destination): return self._call("file.move", source=source, destination=destination)
    def registry_read(self, root, path, name): return self._call("registry.read", root=root, path=path, name=name)
    def registry_write(self, root, path, name, value): return self._call("registry.write", root=root, path=path, name=name, value=value)
    def service_inspect(self, name): return self._call("service.inspect", name=name)
    def shell_run(self, command, cwd=None): return self._call("shell.run", command=command, cwd=cwd)
    def installer_detect(self, path): return self._call("installer.detect", path=path)
    def installer_run(self, path, arguments=None): return self._call("installer.run", path=path, arguments=arguments)
    def app_discover(self, name): return self._call("app.discover", name=name)
    def ui_inspect(self): return self._call("ui.inspect")
    def ui_invoke(self, **kwargs): return self._call("ui.invoke", **kwargs)
    def ui_set_value(self, **kwargs): return self._call("ui.set_value", **kwargs)
    def ui_select(self, **kwargs): return self._call("ui.select", **kwargs)
    def ui_wait_for(self, **kwargs): return self._call("ui.wait_for", **kwargs)
