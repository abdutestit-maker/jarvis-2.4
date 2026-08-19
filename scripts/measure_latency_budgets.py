#!/usr/bin/env python
"""Measure the real JARVIS latency budgets.

The old non-dry path measured ``sleep(0)`` and could therefore certify a
latency budget without touching the runtime. This script now uses the same
Orchestrator and action registry as the desktop app. A one-time GUI preflight
warms Windows shell process creation; the 20 recorded samples are then real
post-warm command turns and remain reproducible in a release report.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.intelligence import LatencyBudget, latency_summary  # noqa: E402


COMMANDS = (
    "Который час?",
    "Поставь музыку",
    "Открой блокнот",
    "Системный статус",
) * 5


def _dry_report() -> dict[str, Any]:
    values = [120.0 + (index % 7) * 35.0 for index in range(20)]
    check = LatencyBudget("fast", 600, 1000, 1500).check(values)
    return {
        "pass": check["pass"],
        "fixture": True,
        "path": "fast",
        "observations": values,
        "summary": latency_summary(values, path="fast"),
        "budget": {"p50_ms": 600, "p95_ms": 1000, "hard_max_ms": 1500},
        "warmup_excluded": True,
    }


def _real_report() -> dict[str, Any]:
    from config import load_config
    from core.orchestrator import Orchestrator
    from core.utils.logger import setup_logging

    setup_logging(level="ERROR", console=False)
    settings = load_config(Path("config/settings.json"))
    settings.voice.tts_enabled = False
    settings.voice.tts_always_on = False
    settings.shadow.enabled = False
    settings.warmup_local_on_start = True

    orchestrator: Orchestrator | None = None
    started = time.perf_counter()
    try:
        orchestrator = Orchestrator(settings, output_callback=lambda _text: None)
        orchestrator.start()
        boot_ms = (time.perf_counter() - started) * 1000.0
        ready = orchestrator.wait_for_runtime_ready(timeout=120.0)

        # Shell process creation is startup work, not a user-turn budget. It
        # is recorded separately instead of silently disappearing.
        preflight_started = time.perf_counter()
        preflight_state = orchestrator.handle_input("Открой блокнот")
        preflight_ms = (time.perf_counter() - preflight_started) * 1000.0

        observations: list[dict[str, Any]] = []
        for command in COMMANDS:
            turn_started = time.perf_counter()
            error = ""
            state: dict[str, Any] = {}
            try:
                raw = orchestrator.handle_input(command)
                state = dict(raw) if isinstance(raw, dict) else {}
            except Exception as exc:  # noqa: BLE001
                error = f"{type(exc).__name__}: {exc}"
            elapsed = (time.perf_counter() - turn_started) * 1000.0
            observations.append({
                "command": command,
                "latency_ms": round(elapsed, 3),
                "intent": state.get("intent"),
                "tool": state.get("tool"),
                "verified": state.get("verified"),
                "mode": state.get("mode"),
                "error": error,
            })

        values = sorted(float(item["latency_ms"]) for item in observations)
        check = LatencyBudget("fast", 600, 1000, 1500).check(values)
        return {
            "pass": bool(check["pass"] and ready == "ready" and all(not item["error"] for item in observations)),
            "fixture": False,
            "path": "fast",
            "count": len(observations),
            "boot_ms": round(boot_ms, 3),
            "runtime_ready": ready,
            "preflight": {
                "command": "Открой блокнот",
                "latency_ms": round(preflight_ms, 3),
                "cold_start": True,
                "verified": bool(preflight_state.get("verified")) if isinstance(preflight_state, dict) else False,
            },
            "warmup_excluded": True,
            "observations": observations,
            "summary": latency_summary(values, path="fast"),
            "budget": {"p50_ms": 600, "p95_ms": 1000, "hard_max_ms": 1500},
        }
    finally:
        if orchestrator is not None:
            orchestrator.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="use deterministic fixture values; never a release proof")
    parser.add_argument("--real", action="store_true", help="explicitly document that the local runtime is exercised")
    parser.add_argument("--output", default="latency_report.json")
    args = parser.parse_args()
    report = _dry_report() if args.dry_run else _real_report()
    target = Path(args.output)
    if not target.is_absolute():
        target = ROOT / target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
