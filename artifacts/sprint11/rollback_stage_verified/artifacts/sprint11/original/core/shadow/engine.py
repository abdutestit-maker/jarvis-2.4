"""Quiet background coordinator for patterns, generated tools and registration."""
from __future__ import annotations

import importlib.util
import json
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from core.actions.base import ActionResult, Tool, ToolContext
from core.actions.registry import DEFAULT_REGISTRY, ToolRegistry
from core.safety import assess_risk

from .generator import ToolGenerator
from .patterns import Pattern, PatternWatcher
from .sandbox import SandboxReport, SandboxTester
from .backlog import ShadowBacklog


@dataclass(frozen=True)
class ToolPreparation:
    name: str
    status: str  # registered | proposed | rejected
    confidence: int
    report: SandboxReport
    path: Optional[Path] = None


class GeneratedShadowTool(Tool):
    """Adapter that presents a verified generated module as a normal Tool."""

    generated_by_shadow = True

    def __init__(self, name: str, description: str, path: Path) -> None:
        self._name, self._description, self.path = name, description, path

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> dict[str, Any]:
        return {"type": "object", "additionalProperties": True}

    def run(self, args: dict[str, Any], context: ToolContext) -> ActionResult:
        try:
            spec = importlib.util.spec_from_file_location(f"jarvis_shadow_{self._name}", self.path)
            if spec is None or spec.loader is None:
                raise RuntimeError("не удалось загрузить shadow tool")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            result = module.run(dict(args))
            if not isinstance(result, dict) or not isinstance(result.get("success"), bool):
                raise RuntimeError("tool returned invalid contract")
            return ActionResult(tool=self.name, args=args, ok=result["success"],
                                output=result.get("result"), error=result.get("error"))
        except Exception as exc:  # generated code never escapes the executor
            return ActionResult(tool=self.name, args=args, ok=False, error=str(exc))


class ShadowEngine:
    """Local-only Shadow Engine. It does no capture and emits no noisy events."""

    def __init__(self, *, data_dir: Path | str, registry: Optional[ToolRegistry] = None,
                 settings: Any = None, enabled: bool = False,
                 generator: Optional[ToolGenerator] = None,
                 tester: Optional[SandboxTester] = None) -> None:
        self.root = Path(data_dir) / "shadow"
        self.root.mkdir(parents=True, exist_ok=True)
        self.tools_dir = Path(data_dir) / "tools" / "shadow"
        self.tools_dir.mkdir(parents=True, exist_ok=True)
        self.registry = registry or DEFAULT_REGISTRY
        self.enabled = enabled
        self.watcher = PatternWatcher(self.root)
        self.backlog = ShadowBacklog(self.root)
        self.generator = generator or ToolGenerator(self.root, settings=settings)
        self.tester = tester or SandboxTester()
        self._settings = settings
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._load_registered_tools()

    def observe_command(self, text: str, *, outcome: str) -> None:
        if self.enabled:
            self.watcher.record_command(text, outcome=outcome)

    def observe_manual_workaround(self, text: str) -> None:
        """Accepts a workaround only when another authorized component links it."""
        if self.enabled:
            self.watcher.record_manual_workaround(text)

    def observe_screen(self, *, active_window: str, permission: bool, ocr_summary: str = "") -> bool:
        if not self.enabled:
            return False
        return self.watcher.record_screen_context(active_window=active_window, permission=permission,
                                                  ocr_summary=ocr_summary)

    def start(self, interval_sec: int = 300) -> None:
        if not self.enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, args=(max(30, interval_sec),),
                                        daemon=True, name="ShadowEngine")
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        self._thread = None

    def tick(self) -> list[ToolPreparation]:
        if not self.enabled or not bool(getattr(getattr(self._settings, "shadow", None), "auto_generate", True)):
            return []
        prepared: list[ToolPreparation] = []
        for pattern in self.watcher.analyze():
            if pattern.frequency <= 2 or pattern.confidence <= 0.8 or self.registry.get(pattern.suggested_tool):
                continue
            try:
                prepared.append(self._generate_and_prepare(
                    name=pattern.suggested_tool, description=pattern.description,
                    confidence=pattern.confidence, params={}, test_params={},
                ))
            except Exception:
                # Shadow mode stays silent. The unfulfilled pattern remains for
                # a later pass when the local coder model is available.
                continue
        return prepared

    def prepare_on_demand(self, goal: str) -> Optional[ToolPreparation]:
        """Try a new low-risk request immediately, using only the local coder.

        The caller still applies the normal JARVIS risk gate before execution.
        If Qwen or validation is unavailable this returns ``None`` quietly,
        leaving Active mode responsive.
        """
        if not self.enabled or not (goal or "").strip():
            return None
        name = self._safe_name("shadow_" + "_".join(re.findall(r"[a-zA-Z0-9]+", goal)[:4]))
        if self.registry.get(name) is not None:
            return None
        try:
            return self._generate_and_prepare(
                name=name, description=goal, confidence=0.81,
                params={"request": "string"}, test_params={"request": "test"},
            )
        except Exception:
            return None

    def _generate_and_prepare(self, *, name: str, description: str, confidence: float,
                              params: dict[str, Any], test_params: dict[str, Any]) -> ToolPreparation:
        """Regenerates at most three times after a functional-only failure."""
        latest: Optional[ToolPreparation] = None
        for _ in range(3):
            source = self.generator.generate(
                name=name, description=description, confidence=confidence, params=params,
                expected_output="user-friendly result", examples=self._existing_tool_examples(),
            )
            latest = self.prepare_tool(name=name, description=description, source=source,
                                       test_params=test_params)
            if latest.status != "rejected" or not latest.report.safety.passed or latest.report.functional.passed:
                return latest
        assert latest is not None
        return latest

    def prepare_tool(self, *, name: str, description: str, source: str,
                     test_params: dict[str, Any]) -> ToolPreparation:
        safe_name = self._safe_name(name)
        if "def run(params: dict)" not in source:
            source = ToolGenerator.wrap(name=safe_name, description=description,
                                        confidence=1.0, body=source)
        report = self.tester.test_source(source, test_params)
        if report.confidence >= 90:
            path = self._register(safe_name, description, source)
            return ToolPreparation(safe_name, "registered", report.confidence, report, path)
        if report.confidence >= 70:
            self._save_candidate(safe_name, source, report)
            return ToolPreparation(safe_name, "proposed", report.confidence, report)
        self._save_rejected(safe_name, source, report)
        return ToolPreparation(safe_name, "rejected", report.confidence, report)

    def suggestion_for(self, goal: str, *, now: Optional[datetime] = None) -> Optional[str]:
        """One quiet, cooldown-protected suggestion for a relevant new tool."""
        goal_l = (goal or "").lower()
        for tool in self.registry.list_tools():
            if not getattr(tool, "generated_by_shadow", False):
                continue
            tokens = set(re.findall(r"[\w]+", (tool.name + " " + tool.description).lower()))
            if tokens and any(token in goal_l for token in tokens if len(token) > 3):
                if self._cooldown_allows(tool.name, now=now):
                    return f"Кстати, я подготовил «{tool.name}». Хочешь попробуешь?"
        return None

    def _loop(self, interval_sec: int) -> None:
        while not self._stop.wait(interval_sec):
            self.tick()

    def _register(self, name: str, description: str, source: str) -> Path:
        path = self.tools_dir / f"{name}.py"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(source, encoding="utf-8")
        tmp.replace(path)
        if self.registry.get(name) is None:
            tool = GeneratedShadowTool(name, description, path)
            self.registry.register(tool)
            self._register_capability(tool)
        self._write_metadata(name, description, path)
        return path

    def _load_registered_tools(self) -> None:
        for path in self.tools_dir.glob("*.py"):
            name = self._safe_name(path.stem)
            if self.registry.get(name) is None:
                tool = GeneratedShadowTool(name, f"Shadow-generated tool: {name}", path)
                self.registry.register(tool)
                self._register_capability(tool)

    @staticmethod
    def _register_capability(tool: Tool) -> None:
        try:
            from core.capabilities import CAPABILITIES, Capability
            CAPABILITIES.register(Capability.from_tool(tool, tags=tool.name.split("_")))
        except Exception:
            pass

    def _existing_tool_examples(self) -> str:
        examples = []
        for tool in self.registry.list_tools()[:5]:
            examples.append(f"{tool.name}: {tool.description}")
        return "\n".join(examples)

    def _save_candidate(self, name: str, source: str, report: SandboxReport) -> None:
        path = self.root / "candidates"
        path.mkdir(exist_ok=True)
        (path / f"{name}.py").write_text(source, encoding="utf-8")
        self._write_json(path / f"{name}.json", {"confidence": report.confidence, "status": "proposed"})

    def _save_rejected(self, name: str, source: str, report: SandboxReport) -> None:
        path = self.root / "rejected"
        path.mkdir(exist_ok=True)
        (path / f"{name}.py").write_text(source, encoding="utf-8")
        self._write_json(path / f"{name}.json", {"confidence": report.confidence, "status": "rejected"})
        self.backlog.add(name, priority=0.8, reason="generated capability failed validation")

    def _write_metadata(self, name: str, description: str, path: Path) -> None:
        manifest = self.root / "tools.json"
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {"tools": []}
        tools = [item for item in data.get("tools", []) if item.get("name") != name]
        tools.append({"name": name, "description": description, "path": str(path),
                      "generated_by_shadow": True})
        self._write_json(manifest, {"tools": tools})

    def _cooldown_allows(self, name: str, *, now: Optional[datetime]) -> bool:
        path = self.root / "notification_cooldowns.json"
        current = now or datetime.now(timezone.utc)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            then = datetime.fromisoformat(data.get(name, ""))
            if current - then < timedelta(days=7):
                return False
        except (OSError, ValueError, TypeError):
            data = {}
        data[name] = current.isoformat()
        self._write_json(path, data)
        return True

    @staticmethod
    def _safe_name(name: str) -> str:
        clean = re.sub(r"[^a-zA-Z0-9_]", "_", name).strip("_").lower()
        return clean[:64] or "shadow_tool"

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)


def active_mode_message(goal: str) -> str:
    """Fallback wording for a novel request; never frames learning as inability."""
    risk = assess_risk(goal)
    if risk.needs_confirmation:
        return "Сейчас разберусь, сэр. Перед опасной операцией потребуется ваше подтверждение."
    return "Сейчас разберусь, сэр. Подготовлю безопасный способ и проверю его."
