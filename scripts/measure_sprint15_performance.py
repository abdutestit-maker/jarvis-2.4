"""Objective Sprint 15 performance probe with one selected local model only."""
from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import load_config  # noqa: E402
from core.security.atomic import atomic_json_write  # noqa: E402


def main() -> int:
    env = os.environ.copy()
    env.update(PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    cold_samples = []
    for _ in range(5):
        started = time.perf_counter()
        completed = subprocess.run(
            [sys.executable, "-c", "import core.orchestrator"], cwd=ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"cold import failed with exit {completed.returncode}")
        cold_samples.append((time.perf_counter() - started) * 1000)

    live_path = ROOT / "artifacts" / "sprint15" / "live" / "live_demo_report.json"
    live = json.loads(live_path.read_text(encoding="utf-8")) if live_path.is_file() else {}
    metrics = {
        "cold_atlas_start_ms": round(statistics.median(cold_samples), 3),
        "cold_atlas_samples_ms": [round(value, 3) for value in cold_samples],
        "simple_chat_latency_ms": live.get("latency_ms", {}).get("simple_chat"),
        "provider_failover_latency_ms": live.get("failover", {}).get("latency_ms"),
        "local_model": {"measured": False},
    }
    try:
        import psutil
        process = psutil.Process(os.getpid())
        metrics["probe_rss_before_mb"] = round(process.memory_info().rss / 1048576, 3)
        from core.llm import clear_backend_cache, get_offline_backend
        settings = load_config()
        clear_backend_cache()
        backend = get_offline_backend(settings)
        model_path = str(settings.local_model.resolved_gguf_path or "")
        started = time.perf_counter()
        backend.warm_up()
        cold_load = (time.perf_counter() - started) * 1000
        rss_loaded = process.memory_info().rss / 1048576
        started = time.perf_counter()
        answer = backend.direct(
            "Ответь одним словом по-русски: готов.",
            system="Ты — ATLAS. Ответь только одним словом.",
            max_tokens=8, temperature=0.0,
        )
        warm_inference = (time.perf_counter() - started) * 1000
        metrics["local_model"] = {
            "measured": True,
            "model": backend.model,
            "path": model_path,
            "cold_load_and_warm_ms": round(cold_load, 3),
            "warm_inference_ms": round(warm_inference, 3),
            "rss_loaded_mb": round(rss_loaded, 3),
            "output": answer[:80],
        }
        backend.close()
        metrics["probe_rss_after_unload_mb"] = round(process.memory_info().rss / 1048576, 3)
    except Exception as exc:
        metrics["local_model"] = {
            "measured": False,
            "error": f"{type(exc).__name__}: {exc}"[:400],
        }

    output = ROOT / "artifacts" / "sprint15" / "performance_after.json"
    atomic_json_write(output, metrics)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"REPORT={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

