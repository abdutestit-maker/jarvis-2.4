"""Small local-only performance probe used by the hardening verification record."""
from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.update(PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    samples: list[float] = []
    for _ in range(5):
        started = time.perf_counter()
        subprocess.run(
            [sys.executable, "-c", "import core.orchestrator"],
            cwd=root, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        samples.append((time.perf_counter() - started) * 1000)
    metrics: dict[str, object] = {
        "cold_start_ms": round(statistics.median(samples), 2),
        "cold_start_samples_ms": [round(item, 2) for item in samples],
    }
    try:
        import psutil
        process = psutil.Process(os.getpid())
        metrics.update({
            "pid": process.pid,
            "rss_mb": round(process.memory_info().rss / 1048576, 2),
            "threads": process.num_threads(),
            "cpu_percent_sample": process.cpu_percent(interval=0.15),
        })
    except Exception as exc:  # pragma: no cover - platform dependent
        metrics["process_metrics_error"] = f"{type(exc).__name__}: {exc}"
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
