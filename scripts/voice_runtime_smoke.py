"""Offline acoustic smoke test for the pinned Russian Piper runtime."""

from __future__ import annotations

import json
import sys
import wave
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import load_config  # noqa: E402
from core.voice.tts import PiperTTS  # noqa: E402


PHRASE = "Сэр, я вас понял. Это тестовый ответ АТЛАСА."


def main() -> int:
    output = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) > 1
        else PROJECT_ROOT / "artifacts" / "voice_runtime_hotfix" / "smoke.wav"
    )
    expected_runtime = (
        PROJECT_ROOT / "data" / "runtime" / "piper" / "piper.exe"
    ).resolve()
    tts = PiperTTS(load_config())
    actual_runtime = Path(tts._binary).resolve() if tts._binary else None

    result: dict[str, object] = {
        "success": False,
        "input": PHRASE,
        "runtime": str(actual_runtime) if actual_runtime else None,
        "expected_runtime": str(expected_runtime),
        "output": str(output),
    }
    if actual_runtime != expected_runtime:
        result["error"] = "unvalidated_piper_runtime"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2
    if not tts.synthesize_to_file(PHRASE, output):
        result["error"] = "synthesis_failed"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 3

    with wave.open(str(output), "rb") as wav:
        duration = wav.getnframes() / float(wav.getframerate())
        result.update(
            channels=wav.getnchannels(),
            sample_rate=wav.getframerate(),
            sample_width=wav.getsampwidth(),
            frames=wav.getnframes(),
            duration_seconds=round(duration, 3),
        )

    # The broken Piper 1.3.0 path generated ~13 seconds of digital tones for
    # this 48-character phrase. The validated runtime produces ~3.3 seconds.
    structurally_valid = (
        result["channels"] == 1
        and result["sample_rate"] == 22_050
        and result["sample_width"] == 2
        and 1.5 <= duration <= 6.0
    )
    result["success"] = structurally_valid
    result["error"] = None if structurally_valid else "acoustic_smoke_failed"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if structurally_valid else 4


if __name__ == "__main__":
    raise SystemExit(main())
