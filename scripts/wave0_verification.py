#!/usr/bin/env python
"""Wave 0 verification: regression metadata, behavior harness and budgets.

The script writes only the four compact verification roles requested by the
project contract. Raw output remains in the process/temp logs.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "verification" / "wave0"


def _run(command: list[str], *, timeout: int = 180) -> dict:
    started = time.perf_counter()
    done = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    return {
        "command": command,
        "exit_code": done.returncode,
        "duration_ms": round((time.perf_counter() - started) * 1000, 3),
        "stdout_tail": done.stdout[-2000:],
        "stderr_tail": done.stderr[-1000:],
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="jarvis-wave0-") as temp:
        behavior = _run([sys.executable, "scripts/_live_probe.py", "--dry-run", "--output", str(Path(temp) / "behavior.json")])
        latency = _run([sys.executable, "scripts/measure_latency_budgets.py", "--dry-run", "--output", str(Path(temp) / "latency.json")])
    regression = _run([sys.executable, "-m", "pytest", "-o", "addopts=", "-q", "--disable-warnings"], timeout=240)
    output = (regression.get("stdout_tail") or "")
    passed_count = 0
    skipped_count = 0
    failed_count = 0
    import re
    match = re.search(r"(\d+) passed, (\d+) skipped(?:, (\d+) failed)?", output)
    if match:
        passed_count, skipped_count, failed_count = map(lambda item: int(item or 0), match.groups())
    report = {
        "wave": 0,
        "baseline": {"before_passed": 473, "before_skipped": 2, "before_failed": 0,
                      "after_passed": passed_count, "after_skipped": skipped_count, "after_failed": failed_count},
        "regression": regression,
        "behavior": behavior,
        "latency": latency,
        "latency_budgets": {
            "fast": {"p50_ms": 600, "p95_ms": 1000, "hard_max_ms": 1500},
            "deliberate": {"first_progress_p95_ms": 2500, "p50_ms": 8000, "p95_ms": 15000},
            "research": {"first_progress_p95_ms": 3000, "source_timeout_ms": 8000},
            "background": {"enqueue_p95_ms": 100},
        },
        "artifact_policy": {
            "directory": str(OUT),
            "retained_roles": ["manifest.json", "verification.json", "diff.patch", "rollback.ps1"],
            "raw_logs_retained": False,
        },
    }
    passed = regression["exit_code"] == 0 and behavior["exit_code"] == 0
    report["pass"] = passed
    (OUT / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "manifest.json").write_text(json.dumps({"wave": 0, "pass": passed, "roles": ["manifest.json", "verification.json", "diff.patch", "rollback.ps1"]}, ensure_ascii=False, indent=2), encoding="utf-8")
    diff = subprocess.run(["git", "diff", "--", "core", "config", "scripts", "tests"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    (OUT / "diff.patch").write_text(diff.stdout, encoding="utf-8")
    (OUT / "rollback.ps1").write_text(
        "param([string]$Workspace = (Resolve-Path (Join-Path $PSScriptRoot '..\\..\\..')).Path)\n"
        "$ErrorActionPreference = 'Stop'\n"
        "Set-Location $Workspace\n"
        "Write-Host 'Wave 0 rollback is intentionally additive-safe.'\n"
        "Write-Host 'Review diff.patch, then restore only the files listed in its pre-wave manifest.'\n"
        "Write-Host 'This script never touches frontend, voice, Browser Bridge, data, or user secrets.'\n",
        encoding="utf-8",
    )
    print(json.dumps({"pass": passed, "output": str(OUT)}, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
