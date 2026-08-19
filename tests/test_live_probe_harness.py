from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_behavior_harness_dry_run_covers_verified_batch(tmp_path: Path):
    output = tmp_path / "live-probe.json"
    completed = subprocess.run(
        [sys.executable, "scripts/_live_probe.py", "--dry-run", "--output", str(output)],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert completed.returncode == 0, (completed.stdout or "") + (completed.stderr or "")
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["pass"] is True
    assert report["latency"]["path"] == "fast"
    assert any(item["meta"]["tool"] == "command_batch" for item in report["results"])
    assert all(not item["failures"] for item in report["results"])
