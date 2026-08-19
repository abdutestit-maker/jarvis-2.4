#!/usr/bin/env python
"""Real local quality probe for the single-model runtime.

``_live_probe.py --dry-run`` is a fixture and stays separate.  This module
executes only bounded, local checks: deterministic system tools, unknown-task
planning, memory relevance, and (when ``--real`` is passed) the configured
GGUF after warmup.  It never opens a browser, sends a network request, or
creates a reminder.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _timed(fn: Callable[[], Any]) -> tuple[Any, float]:
    started = time.perf_counter()
    value = fn()
    return value, (time.perf_counter() - started) * 1000.0


def _percentiles(values: Iterable[float]) -> Dict[str, float]:
    samples = sorted(float(value) for value in values)
    if not samples:
        return {"count": 0, "p50_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0}
    p50 = statistics.median(samples)
    # nearest-rank percentile; deterministic for a small probe sample
    index = max(0, min(len(samples) - 1, int((len(samples) * 0.95 + 0.999999) - 1)))
    return {
        "count": len(samples),
        "p50_ms": round(p50, 3),
        "p95_ms": round(samples[index], 3),
        "max_ms": round(max(samples), 3),
    }


def _tool(settings: Any, name: str, args: Dict[str, Any] | None = None):
    from core.actions import DEFAULT_REGISTRY, ToolContext, execute_tool

    return execute_tool(
        DEFAULT_REGISTRY,
        name,
        dict(args or {}),
        ToolContext(settings=settings),
        max_retries=0,
    )


def probe_current_time(settings: Any) -> Dict[str, Any]:
    from core.actions.time import current_time

    result, elapsed = _timed(lambda: _tool(settings, "current_time"))
    now = datetime.now().astimezone()
    output = str(result.output or "")
    verified = bool(
        result.ok
        and now.strftime("%Y-%m-%d") in output
        and now.strftime("%H:") in output
        and result.tool == "current_time"
    )
    return {
        "name": "current_time",
        "ok": bool(result.ok),
        "tool": result.tool,
        "output": output,
        "expected_date": now.strftime("%Y-%m-%d"),
        "verified": verified,
        "latency_ms": round(elapsed, 3),
        "implementation": current_time.__module__,
        "foreign_tool": False,
    }


def probe_system_status(settings: Any) -> Dict[str, Any]:
    result, elapsed = _timed(lambda: _tool(settings, "system_status"))
    output = str(result.output or "")
    markers = ("CPU:", "RAM:", "Диск", "disk", "RAM")
    verified = bool(result.ok and "CPU:" in output and "RAM:" in output)
    return {
        "name": "system_status",
        "ok": bool(result.ok),
        "tool": result.tool,
        "output": output,
        "markers_present": [marker for marker in markers if marker in output],
        "verified": verified,
        "latency_ms": round(elapsed, 3),
        "foreign_tool": False,
    }


def probe_media_safety(settings: Any) -> Dict[str, Any]:
    # A named track with allow_network=False must stop at the policy boundary;
    # this deliberately avoids the local-player launch path.
    result, elapsed = _timed(
        lambda: _tool(
            settings,
            "play_music",
            {"query": "quality probe track", "allow_network": False},
        )
    )
    error = str(result.error or "")
    blocked = "разреш" in error.casefold() or "сет" in error.casefold()
    return {
        "name": "media_policy",
        "ok": bool(result.ok),
        "tool": result.tool,
        "error": error,
        "action_taken": bool(result.ok),
        "reminder_called": False,
        "verified": bool(not result.ok and blocked and result.tool == "play_music"),
        "latency_ms": round(elapsed, 3),
        "foreign_tool": result.tool != "play_music",
    }


def probe_unknown_task(settings: Any) -> Dict[str, Any]:
    from core.actions.registry import DEFAULT_REGISTRY
    from core.capability_engine import CapabilityCatalog, CapabilityPlanner

    goal = "синхронизируй локальный голографический проектор с неизвестным протоколом"
    with TemporaryDirectory(prefix="jarvis-quality-capability-") as directory:
        planner = CapabilityPlanner(CapabilityCatalog(Path(directory)), DEFAULT_REGISTRY)
        plan, elapsed = _timed(lambda: planner.plan(goal))
    foreign = plan.acquisition != "research" and bool(plan.steps)
    verified = plan.acquisition == "research" and not foreign
    return {
        "name": "unknown_task",
        "acquisition": plan.acquisition,
        "steps": [step.tool for step in plan.steps],
        "research_pending": verified,
        "success": False,
        "foreign_tool_call": foreign,
        "verified": verified,
        "latency_ms": round(elapsed, 3),
    }


def probe_memory_relevance() -> Dict[str, Any]:
    from core.memory.relationship.store import RelationshipMemoryStore

    with TemporaryDirectory(prefix="jarvis-quality-memory-") as directory:
        store = RelationshipMemoryStore(Path(directory))
        store.remember(
            "Пользователь любит краткие ответы",
            source="quality_probe",
            confidence=0.95,
            importance=0.7,
            key="communication_style",
        )
        store.remember(
            "GTA 5 установлен на рабочем компьютере",
            source="quality_probe",
            confidence=0.95,
            importance=0.4,
            key="game_installation",
        )
        relevant, elapsed = _timed(lambda: store.retrieve("объясни энтропию", limit=4))
    facts = [item.fact for item in relevant]
    verified = not any("GTA 5" in fact for fact in facts)
    return {
        "name": "memory_relevance",
        "facts": facts,
        "irrelevant_fact_leaked": not verified,
        "verified": verified,
        "latency_ms": round(elapsed, 3),
    }


def probe_model(settings: Any, samples: int) -> Dict[str, Any]:
    from core.llm import Tier, clear_backend_cache, get_llm_backend
    from core.llm.hardware_profile import apply_profile

    apply_profile(settings)
    started = time.perf_counter()
    try:
        backend = get_llm_backend(settings, Tier.FAST)
        load_started = time.perf_counter()
        backend.warm_up()
        warmup_ms = (time.perf_counter() - load_started) * 1000.0
        prompts = [
            "Коротко объясни энтропию одним бытовым примером.",
            "Реши 2 + 2 и ответь только числом.",
            "Назови два шага безопасной установки локальной программы.",
        ][: max(1, min(int(samples), 3))]
        timings: List[float] = []
        outputs: List[str] = []
        for prompt in prompts:
            text, elapsed = _timed(
                lambda prompt=prompt: backend.direct(
                    prompt,
                    system="Отвечай по-русски. Не используй <think>. Будь точным и кратким.",
                    max_tokens=64,
                    temperature=0.1,
                )
            )
            timings.append(elapsed)
            outputs.append(str(text).strip())
        info = dict(getattr(backend, "runtime_info", lambda: {})() or {})
        result = {
            "status": "ready",
            "model": str(getattr(backend, "model", "")),
            "path": str(getattr(settings.local_model, "resolved_gguf_path", "")),
            "runtime": info,
            "warmup_ms": round(warmup_ms, 3),
            "startup_to_ready_ms": round((time.perf_counter() - started) * 1000.0, 3),
            "generation": _percentiles(timings),
            "outputs": outputs,
            "quality_verified": bool(outputs and all(outputs) and not any("<think>" in item for item in outputs)),
        }
    except Exception as exc:
        result = {
            "status": "unavailable",
            "error": f"{type(exc).__name__}: {exc}",
            "quality_verified": False,
        }
    finally:
        clear_backend_cache()
    return result


def run_probe(*, real: bool = False, samples: int = 3) -> Dict[str, Any]:
    from config import load_config

    settings = load_config()
    checks = [
        probe_current_time(settings),
        probe_system_status(settings),
        probe_media_safety(settings),
        probe_unknown_task(settings),
        probe_memory_relevance(),
    ]
    fast = [item["latency_ms"] for item in checks[:3]]
    report: Dict[str, Any] = {
        "probe": "real_local_quality",
        "fixture": False,
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "config": {
            "offline_mode": bool(settings.offline_mode),
            "primary_brain": str(settings.primary_brain),
            "model": str(settings.get_model_id("fast")),
            "model_path": str(settings.local_model.resolved_gguf_path),
        },
        "checks": checks,
        "fast_tools": _percentiles(fast),
        "model": None,
    }
    if real:
        report["model"] = probe_model(settings, samples)
    checks_ok = all(bool(item.get("verified")) for item in checks)
    report["verified"] = bool(checks_ok and (not real or bool(report["model"].get("quality_verified"))))
    report["note"] = (
        "Тесты инструментов локальные и детерминированные; запуск модели включается только --real."
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real", action="store_true", help="загрузить и прогреть локальный GGUF")
    parser.add_argument("--samples", type=int, default=3, help="число коротких генераций модели (1..3)")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "diagnostics" / "quality_probe.json")
    args = parser.parse_args()
    report = run_probe(real=args.real, samples=args.samples)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
