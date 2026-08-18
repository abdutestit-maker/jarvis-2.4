"""Safe real Sprint 10 demo on Notepad++ (winget + UIA + config + verify)."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.actions.registry import DEFAULT_REGISTRY
from core.capability_engine import CapabilityCatalog, CapabilityEngine
from core.operator.adapters import XmlConfigAdapter, XmlSetting
from core.operator.knowledge import AppKnowledgeStore
from core.operator.mission import OperatorMission
from core.operator.software import CheckpointManager, InstallerEngine, SoftwareResolver
from core.operator.windows import AppExplorer
from core.platform.windows import NativeWindowsProvider, WindowsCapabilityLayer


APP = "Notepad++"
PACKAGE_ID = "Notepad++.Notepad++"
DESIRED = {"remember_last_session": False, "word_wrap": True}


class DemoProcess:
    """Tracks only the process created by this demo; unrelated windows stay untouched."""

    def __init__(self) -> None:
        self.pid: int | None = None
        self.executable = Path(r"C:\Program Files\Notepad++\notepad++.exe")

    def adopt(self, pid: int | None, executable: str) -> None:
        self.pid = int(pid) if pid else None
        if executable:
            self.executable = Path(executable)

    def close(self) -> None:
        if not self.pid or not psutil.pid_exists(self.pid):
            return
        import win32con
        import win32gui

        handles: list[int] = []

        def collect(handle: int, _extra: Any) -> bool:
            _thread, process_id = __import__("win32process").GetWindowThreadProcessId(handle)
            if process_id == self.pid and win32gui.IsWindowVisible(handle):
                handles.append(handle)
            return True

        win32gui.EnumWindows(collect, None)
        for handle in handles:
            win32gui.PostMessage(handle, win32con.WM_CLOSE, 0, 0)
        deadline = time.monotonic() + 10
        while psutil.pid_exists(self.pid) and time.monotonic() < deadline:
            time.sleep(0.1)
        if psutil.pid_exists(self.pid):
            raise RuntimeError(f"demo process {self.pid} did not close cleanly")
        self.pid = None

    def launch(self) -> dict[str, Any]:
        process = subprocess.Popen(
            [str(self.executable), "-multiInst", "-nosession"], shell=False,
        )
        self.pid = process.pid
        deadline = time.monotonic() + 20
        window = None
        while time.monotonic() < deadline:
            window = next(
                (item for item in NativeWindowsProvider.window_list()
                 if item.get("process_id") == process.pid),
                None,
            )
            if window:
                break
            time.sleep(0.2)
        if not window:
            raise RuntimeError("Notepad++ window did not appear after configuration")
        return window


class TrackedInstaller(InstallerEngine):
    def __init__(self, tracker: DemoProcess) -> None:
        super().__init__()
        self.tracker = tracker
        self.calls = 0

    def install(self, candidate, **kwargs):
        self.calls += 1
        candidate.expected_executable = "notepad++.exe"
        candidate.launch_args = ["-multiInst", "-nosession"]
        evidence = super().install(candidate, **kwargs)
        self.tracker.adopt(evidence.process_id, evidence.executable)
        return evidence


class CountingResolver(SoftwareResolver):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def resolve(self, *args, **kwargs):
        self.calls += 1
        return super().resolve(*args, **kwargs)


class CountingExplorer(AppExplorer):
    def __init__(self, windows: WindowsCapabilityLayer) -> None:
        super().__init__(windows)
        self.calls = 0

    def explore(self, *args, **kwargs):
        self.calls += 1
        return super().explore(*args, **kwargs)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _clear_live_learning(catalog: CapabilityCatalog, store: AppKnowledgeStore) -> None:
    for path in (
        store.path_for(APP),
        catalog.directory / "operator_Notepad.json",
        catalog.directory / "operator_Notepad_.json",
    ):
        resolved = path.resolve()
        if resolved.parent in {store.directory.resolve(), catalog.directory.resolve()}:
            resolved.unlink(missing_ok=True)
    for path in catalog.episodes_dir.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if payload.get("capability") in {"operator_Notepad", "operator_Notepad_"}:
            path.resolve().unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh-knowledge", action="store_true")
    args = parser.parse_args()

    artifact_dir = ROOT / "artifacts" / "sprint10"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    reference = artifact_dir / "notepadpp_reference.txt"
    reference.write_text(
        "application: Notepad++\nremember_last_session: false\nword_wrap: true\n",
        encoding="utf-8",
    )
    config = Path.home() / "AppData" / "Roaming" / "Notepad++" / "config.xml"

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    catalog = CapabilityCatalog(ROOT / "data" / "capabilities")
    store = AppKnowledgeStore(ROOT / "data" / "app_knowledge")
    if args.fresh_knowledge:
        _clear_live_learning(catalog, store)

    windows = WindowsCapabilityLayer()
    resolver = CountingResolver()
    tracker = DemoProcess()
    installer = TrackedInstaller(tracker)
    explorer = CountingExplorer(windows)
    engine = CapabilityEngine(catalog, DEFAULT_REGISTRY)
    adapter = XmlConfigAdapter(
        config_path=config,
        settings={
            "remember_last_session": XmlSetting(
                ".//GUIConfig[@name='RememberLastSession']", kind="text", value_type="bool",
            ),
            "word_wrap": XmlSetting(
                ".//GUIConfig[@name='ScintillaPrimaryView']", kind="attribute",
                attribute="Wrap", value_type="bool",
            ),
        },
        checkpoints=CheckpointManager(artifact_dir / "live_checkpoints" / run_id),
        close_application=tracker.close,
        launch_application=tracker.launch,
        window_title=APP,
    )
    mission = OperatorMission(
        capability_engine=engine,
        knowledge_store=store,
        resolver=resolver,
        installer=installer,
        explorer=explorer,
        windows=windows,
    )
    request = "Установи тестовую программу Notepad++ и настрой её как в этой reference."
    print("Сейчас разберусь, сэр.", flush=True)
    before_hash = _sha256(config) if config.is_file() else "missing"
    first = mission.run(
        request=request, application=APP, reference=reference, adapter=adapter,
        package_id=PACKAGE_ID,
    )
    if not first.completed:
        raise RuntimeError(json.dumps(asdict(first), ensure_ascii=False))

    knowledge = store.load(APP)
    if knowledge is None:
        raise RuntimeError("AppKnowledge was not persisted")
    first_counts = {
        "resolver": resolver.calls, "installer": installer.calls, "explorer": explorer.calls,
    }

    # Deliberately drift both fields, then repeat the same request. The second
    # mission must reuse learned source/UI knowledge and still observe the app.
    drift_checkpoint = adapter.checkpoint(list(DESIRED))
    adapter.apply_setting("remember_last_session", True)
    adapter.apply_setting("word_wrap", False)
    drifted = adapter.observe()
    if drifted == DESIRED:
        raise RuntimeError("live second-run drift was not created")

    second = mission.run(
        request=request, application=APP, reference=reference, adapter=adapter,
        package_id=PACKAGE_ID,
    )
    final_state = adapter.observe()
    windows_now = [
        item for item in NativeWindowsProvider.window_list()
        if item.get("process_id") == tracker.pid
    ]
    reuse_proof = {
        "reused_knowledge": second.reused_knowledge,
        "reused_episode": second.reused_episode,
        "calls_after_first": first_counts,
        "calls_after_second": {
            "resolver": resolver.calls, "installer": installer.calls, "explorer": explorer.calls,
        },
        "research_calls": [first.metrics.get("research_calls"), second.metrics.get("research_calls")],
        "discovery_steps": [first.metrics.get("discovery_steps"), second.metrics.get("discovery_steps")],
    }
    verified = all((
        second.completed,
        final_state == DESIRED,
        bool(windows_now),
        second.reused_knowledge,
        second.reused_episode,
        first_counts == reuse_proof["calls_after_second"],
        bool(first.installer and first.installer.get("verified")),
    ))
    report = {
        "run_id": run_id,
        "application": APP,
        "package_id": PACKAGE_ID,
        "reference": str(reference),
        "execution_ladder": ["package_manager", "config", "uia"],
        "raw_coordinates_used": False,
        "config": str(config),
        "config_sha256_before": before_hash,
        "config_sha256_after": _sha256(config),
        "first_run": asdict(first),
        "deliberate_drift": drifted,
        "drift_rollback_checkpoint": asdict(drift_checkpoint),
        "second_run": asdict(second),
        "app_knowledge": {
            "path": str(store.path_for(APP)),
            "controls": len(knowledge.controls),
            "menus": len(knowledge.menus),
            "best_execution_method": knowledge.best_execution_method,
            "reuse_count": (store.load(APP) or knowledge).reuse_count,
        },
        "final_state": final_state,
        "final_window": windows_now[0] if windows_now else None,
        "second_run_reuse": reuse_proof,
        "verified": verified,
    }
    report_path = artifact_dir / "live_demo_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "verified": verified,
        "report": str(report_path),
        "installer": first.installer,
        "ui_controls": len(knowledge.controls),
        "final_state": final_state,
        "second_run_reuse": reuse_proof,
    }, ensure_ascii=False, indent=2))
    if verified:
        print("Готово. Проверяйте, сэр.")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
