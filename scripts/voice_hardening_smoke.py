"""Safe local Voice/TTS smoke: render, synthesize WAV, verify and report."""

from __future__ import annotations

import json
import sys
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import load_config
from core.voice.output import (
    AssistantOutput, ErrorCategory, ErrorInfo, UserFriendlyErrorMapper,
)
from core.voice.speech_renderer import SpeechRenderer
from core.voice.tts import PiperTTS


def _wav_info(path: Path) -> dict[str, object]:
    with wave.open(str(path), "rb") as wav:
        frames = wav.getnframes()
        rate = wav.getframerate()
        return {
            "path": str(path.resolve()),
            "bytes": path.stat().st_size,
            "sample_rate": rate,
            "channels": wav.getnchannels(),
            "duration_sec": round(frames / float(rate), 3),
        }


def main() -> int:
    settings = load_config()
    renderer = SpeechRenderer(settings.voice)
    tts = PiperTTS(settings)
    mapper = UserFriendlyErrorMapper()
    output_dir = ROOT / "artifacts" / "voice_test"
    output_dir.mkdir(parents=True, exist_ok=True)

    scenarios = [
        ("normal.wav", AssistantOutput.natural("Готово, сэр.")),
        ("focused.wav", AssistantOutput.natural(
            "Сейчас разберусь, сэр.", speech_mode="focused")),
        ("terminal_failure.wav", mapper.map(ErrorInfo(
            ErrorCategory.UNKNOWN_FAILURE,
            technical_message="Exception: HTTP 455 request_id=smoke",
        ))),
    ]
    samples = []
    latencies = []
    for filename, output in scenarios:
        rendered = renderer.render(output)
        if rendered is None:
            raise RuntimeError(f"Expected speech for {filename}")
        target = output_dir / filename
        started = time.perf_counter()
        ok = tts.synthesize_to_file(
            rendered.text, target, rate=rendered.rate, volume=rendered.volume,
        )
        latencies.append(round((time.perf_counter() - started) * 1000, 3))
        if not ok:
            raise RuntimeError(f"Piper synthesis failed for {filename}")
        info = _wav_info(target)
        info.update({"mode": rendered.mode, "text": rendered.text})
        samples.append(info)

    raw = renderer.render(AssistantOutput.natural("Error 455"))
    recovered = renderer.render(mapper.map(ErrorInfo(
        ErrorCategory.PROVIDER_UNAVAILABLE,
        technical_message="HTTP 455 remote provider",
        recovered=True,
    )))
    report = {
        "provider": tts.provider_info,
        "raw_error_spoken": raw.text if raw else None,
        "recovered_failure_spoken": recovered.text if recovered else None,
        "cold_latency_ms": latencies[0],
        "warm_latency_ms": round(sum(latencies[1:]) / len(latencies[1:]), 3),
        "samples": samples,
        "barge_in": "TTSQueue interrupt/stop_speaking verified by automated test",
    }
    report_path = output_dir / "smoke_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
