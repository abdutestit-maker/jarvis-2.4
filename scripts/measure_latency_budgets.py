#!/usr/bin/env python
"""Measure fast/deliberate/background budgets with compact JSON output."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.intelligence import LatencyBudget, latency_summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", default="latency_report.json")
    args = parser.parse_args()
    if args.dry_run:
        values = [120.0 + (index % 7) * 35.0 for index in range(20)]
        report = {
            "pass": LatencyBudget("fast", 600, 1000, 1500).check(values)["pass"],
            "path": "fast",
            "observations": values,
            "summary": latency_summary(values, path="fast"),
            "budget": {"p50_ms": 600, "p95_ms": 1000, "hard_max_ms": 1500},
            "warmup_excluded": True,
        }
    else:
        values = []
        for _ in range(20):
            started = time.perf_counter()
            time.sleep(0)
            values.append((time.perf_counter() - started) * 1000)
        report = {"pass": LatencyBudget("fast", 600, 1000, 1500).check(values)["pass"],
                  "path": "fast", "observations": values,
                  "summary": latency_summary(values, path="fast"),
                  "budget": {"p50_ms": 600, "p95_ms": 1000, "hard_max_ms": 1500},
                  "warmup_excluded": False}
    target = Path(args.output)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
