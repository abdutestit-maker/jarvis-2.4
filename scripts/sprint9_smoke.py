"""Safe Sprint 9 live smoke: temp files only, no network or system mutation."""
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
from core.actions import DEFAULT_REGISTRY, ToolContext
from core.capability_engine import CapabilityCatalog, CapabilityEngine, CapabilityPlanner


def _run(planner, engine, goal: str):
    started = time.perf_counter()
    plan = planner.plan(goal)
    report = engine.execute(plan)
    return {
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "acquisition": plan.acquisition,
        "llm_calls": 0,
        "tools_used": [result.tool for result in report.results],
        "verified": report.verification.verified,
        "completed": report.completed,
        "episode_id": report.episode.episode_id if report.episode else None,
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="jarvis-sprint9-") as raw:
        root = Path(raw)
        for name in ("alpha.txt", "beta.md", "gamma.txt"):
            (root / name).write_text(name, encoding="utf-8")
        settings = Settings()
        settings.paths.documents_dir = str(root)
        catalog = CapabilityCatalog(root / ".capabilities")
        planner = CapabilityPlanner(catalog, DEFAULT_REGISTRY)
        engine = CapabilityEngine(catalog, DEFAULT_REGISTRY,
                                  context=ToolContext(settings=settings))
        first = _run(planner, engine, "организуй тестовые файлы по расширению")

        for name in ("delta.txt", "epsilon.md"):
            (root / name).write_text(name, encoding="utf-8")
        second = _run(CapabilityPlanner(catalog, DEFAULT_REGISTRY), engine,
                      "снова организуй файлы по расширению")
        print(json.dumps({"scenario": "safe_file_organization",
                          "first": first, "second": second},
                         ensure_ascii=False, indent=2))
        return 0 if first["completed"] and second["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
