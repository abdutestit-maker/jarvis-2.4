"""Crash-interruption probe for atomic JSON persistence."""
from __future__ import annotations

import multiprocessing as mp
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.security.atomic import atomic_json_write, load_json


def writer(path: str) -> None:
    target = Path(path)
    for index in range(1000):
        atomic_json_write(target, {"index": index, "records": list(range(32))})


def main() -> None:
    path = ROOT / "artifacts" / "hardening_crash_probe.json"
    atomic_json_write(path, {"index": -1, "records": []})
    process = mp.Process(target=writer, args=(str(path),))
    process.start()
    time.sleep(0.08)
    process.terminate()
    process.join(timeout=3)
    value = load_json(path, default=None)
    valid = isinstance(value, dict) and isinstance(value.get("records"), list)
    print({"child_exit": process.exitcode, "json_valid_after_termination": valid, "index": value.get("index") if isinstance(value, dict) else None})
    raise SystemExit(0 if valid else 1)


if __name__ == "__main__":
    main()
