"""Deterministic local smoke for Executive Mind audit fixes."""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import Settings
from core.executive import ExecutiveMind
from core.orchestrator import Orchestrator


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="jarvis-executive-smoke-"))
    settings = Settings()
    settings.paths.data_dir = str(root / "data")
    settings.paths.profile_dir = str(root / "profile")
    settings.paths.graph_dir = str(root / "graph")
    settings.paths.memory_dir = str(root / "memory")
    settings.paths.documents_dir = str(root / "documents")
    settings.voice.tts_enabled = False
    settings.voice.tts_always_on = False
    output: list[str] = []
    orchestrator = Orchestrator(settings, output_callback=output.append)
    records = []
    try:
        for command in ("Который час", "Поставь музыку, настроения нет"):
            started = time.perf_counter()
            state = orchestrator.handle_input(command)
            records.append({
                "command": command,
                "intent": state.get("intent"),
                "response": state.get("response"),
                "executive": state.get("executive", {}),
                "reminder_tool_used": "add_reminder" in str(state.get("response")),
                "tool": state.get("tool"),
                "verified": state.get("verified"),
                "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                "evidence": state.get("evidence", []),
            })
    finally:
        orchestrator.shutdown()
    # Restart the executive store and prove that an equivalent goal reuses its
    # existing node rather than creating a second copy.
    first = ExecutiveMind(settings.data_dir / "executive")
    one = first.begin_turn("подготовь отчёт", intent="file")
    second = ExecutiveMind(settings.data_dir / "executive")
    two = second.begin_turn("подготовь отчёт", intent="file")
    second_run_reuse = first.goals.resume("подготовь отчёт").id == second.goals.resume("подготовь отчёт").id
    report = {"live": True, "offline": True, "records": records,
              "runtime_diagnostics": orchestrator.runtime_diagnostics(),
              "second_run_reuse": second_run_reuse,
              "pass": records[0]["intent"] == "system" and records[1]["intent"] == "media"
              and not records[1]["reminder_tool_used"] and second_run_reuse}
    (PROJECT_ROOT / "artifacts" / "executive_mind_live_smoke_result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
