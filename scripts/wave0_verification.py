#!/usr/bin/env python
"""Wave 0 verification: regression metadata, behavior harness and budgets.

The script writes only the four compact verification roles requested by the
project contract. Raw output remains in the process/temp logs.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Running from the Hermes venv prepends Hermes' own repository to sys.path.
# Put this checkout first before pytest imports ``tests.conftest``.
ROOT = Path(__file__).resolve().parents[1]
root_text = str(ROOT)
while root_text in sys.path:
    sys.path.remove(root_text)
sys.path.insert(0, root_text)

OUT = ROOT / "artifacts" / "verification" / "wave0"


def _run(command: list[str], *, timeout: int = 180) -> dict:
    started = time.perf_counter()
    env = dict(os.environ)
    # Hermes' venv injects its own repository ahead of cwd. Ensure pytest
    # imports this checkout's ``tests.conftest`` rather than Hermes' tests.
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + existing_pythonpath if existing_pythonpath else "")
    # For Python subprocesses, run a tiny bootstrap that force-loads this
    # checkout's tests package before pytest sees Hermes' own tests package.
    actual_command = command
    if len(command) >= 3 and command[1:3] == ["-m", "pytest"]:
        bootstrap = (
            "import pathlib,runpy,sys; "
            f"root=pathlib.Path({str(ROOT)!r}); "
            "sys.path.insert(0,str(root)); "
            "spec=__import__('importlib.util',fromlist=['x']).spec_from_file_location("
            "'tests.conftest',root/'tests'/'conftest.py'); "
            "mod=__import__('importlib.util',fromlist=['x']).module_from_spec(spec); "
            "sys.modules['tests.conftest']=mod; spec.loader.exec_module(mod); "
            "sys.argv=['pytest',*sys.argv[1:]]; runpy.run_module('pytest',run_name='__main__')"
        )
        actual_command = [command[0], "-c", bootstrap, *command[3:]]
    done = subprocess.run(actual_command, cwd=ROOT, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    return {
        "command": command,
        "exit_code": done.returncode,
        "duration_ms": round((time.perf_counter() - started) * 1000, 3),
        "stdout_tail": done.stdout[-2000:],
        "stderr_tail": done.stderr[-1000:],
    }


def _git_provenance() -> dict:
    """Capture the exact source tree this verification ran against."""
    def run(args):
        try:
            done = subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=30)
            return done.stdout.strip()
        except Exception:
            return ""
    head = run(["git", "rev-parse", "HEAD"])
    short = head[:7] if head else ""
    branch = run(["git", "branch", "--show-current"])
    dirty = run(["git", "status", "--porcelain"])
    return {
        "source_commit": head,
        "source_short": short,
        "source_branch": branch or "detached",
        "dirty": False,
        "dirty_files": [],
    } if dirty == "" else {
        "source_commit": head,
        "source_short": short,
        "source_branch": branch or "detached",
        "dirty": True,
        "dirty_files": [line for line in dirty.splitlines() if line][:200],
    }


def _source_diff(provenance: dict) -> str:
    """Return the source commit diff without including generated artifacts."""
    commit = str(provenance.get("source_commit") or "")
    if not commit:
        return ""
    parent = subprocess.run(
        ["git", "rev-parse", f"{commit}^"], cwd=ROOT, capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    ).stdout.strip()
    if not parent:
        return ""
    diff = subprocess.run(
        ["git", "diff", "--binary", f"{parent}..{commit}", "--",
         "core", "config", "scripts", "tests"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return diff.stdout


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    provenance = _git_provenance()
    with tempfile.TemporaryDirectory(prefix="jarvis-wave0-") as temp:
        # This gate uses the real local deterministic tools.  The historical
        # _live_probe --dry-run fixture remains a visual protocol fixture and
        # is deliberately not counted as behavioral evidence.
        behavior = _run([sys.executable, "scripts/quality_probe.py", "--output", str(Path(temp) / "behavior.json")])
        latency = _run([sys.executable, "scripts/measure_latency_budgets.py", "--output", str(Path(temp) / "latency.json")])
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
        "provenance": provenance,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        # Captured immediately before the v4 wave on the clean tree.
        "baseline": {"before_passed": 528, "before_skipped": 2, "before_failed": 0,
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
    passed = regression["exit_code"] == 0 and behavior["exit_code"] == 0 and latency["exit_code"] == 0
    report["pass"] = passed
    (OUT / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "manifest.json").write_text(json.dumps({"wave": 0, "pass": passed, "provenance": provenance, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "roles": ["manifest.json", "verification.json", "diff.patch", "rollback.ps1"]}, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "diff.patch").write_text(_source_diff(provenance), encoding="utf-8")
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
