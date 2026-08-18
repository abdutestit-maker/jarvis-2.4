"""Reproduce the pre-fix Windows stdin decoding defect with Python Piper."""

from __future__ import annotations

import json
import os
import subprocess
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = Path(
    r"C:\Users\WwW\AppData\Local\hermes\hermes-agent\venv\Scripts\piper.exe"
)
MODEL = ROOT / "data" / "models" / "piper" / "ru_RU-dmitri-medium.onnx"
OUTPUT = Path(__file__).with_name("baseline_probe.wav")
TEXT = "Сэр, я вас понял. Это тестовый ответ Джарвиса."

environment = os.environ.copy()
environment.pop("PYTHONIOENCODING", None)
environment.pop("PYTHONUTF8", None)
process = subprocess.run(
    [str(RUNTIME), "--model", str(MODEL), "--output_file", str(OUTPUT)],
    input=(TEXT + "\n").encode("utf-8"),
    capture_output=True,
    env=environment,
    timeout=30,
)
with wave.open(str(OUTPUT), "rb") as wav:
    duration = wav.getnframes() / float(wav.getframerate())

valid = process.returncode == 0 and 1.5 <= duration <= 6.0
print(json.dumps({
    "success": valid,
    "input": TEXT,
    "runtime": str(RUNTIME),
    "output": str(OUTPUT),
    "process_exit": process.returncode,
    "duration_seconds": round(duration, 3),
    "error": None if valid else "acoustic_smoke_failed",
}, ensure_ascii=False, indent=2))
raise SystemExit(0 if valid else 4)
