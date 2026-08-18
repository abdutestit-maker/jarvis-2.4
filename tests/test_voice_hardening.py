"""Voice/TTS hardening regression and contract tests."""

from __future__ import annotations

import time
import wave
from array import array
from pathlib import Path
from types import SimpleNamespace

import pytest

from config.settings import load_config
from core.voice.output import (
    AssistantOutput,
    ErrorCategory,
    ErrorInfo,
    UserFriendlyErrorMapper,
    assistant_output_from_outcome,
)
from core.voice.speech_renderer import RenderedSpeech, SpeechRenderer
from core.voice.tts import PiperTTS, VoiceConfig
from core.voice.tts_queue import TTSQueue


HTTP_CODES = (401, 403, 404, 408, 429, 455, 500, 503)


@pytest.mark.parametrize("code", HTTP_CODES)
def test_raw_http_error_codes_never_become_speech(code: int) -> None:
    renderer = SpeechRenderer()

    rendered = renderer.render(AssistantOutput(display_text=f"Error {code}", speech_text=f"Error {code}"))

    assert rendered is None


@pytest.mark.parametrize(
    "technical",
    [
        'Traceback (most recent call last):\n  File "worker.py", line 7\nValueError: bad',
        r"C:\Users\WwW\AppData\Local\secret.txt",
        "/home/user/.config/private.json",
        "https://provider.invalid/request?id=123",
        "request_id=8a595baf-6f80-46b8-b150-2eb333cab08a",
        "8a595baf-6f80-46b8-b150-2eb333cab08a",
        '{"error": "provider unavailable", "status": 455}',
        "2026-08-17 10:01:02 | ERROR | internal.provider | failed",
        "```python\nraise RuntimeError('boom')\n```",
    ],
)
def test_technical_payloads_are_not_spoken(technical: str) -> None:
    renderer = SpeechRenderer()

    rendered = renderer.render(AssistantOutput(display_text=technical, speech_text=technical))

    assert rendered is None


def test_markdown_is_reduced_to_natural_text() -> None:
    renderer = SpeechRenderer()
    output = AssistantOutput(
        display_text="**Готово**, сэр. [Отчёт](https://internal.invalid/report)",
        speech_text="**Готово**, сэр. [Отчёт](https://internal.invalid/report)",
    )

    rendered = renderer.render(output)

    assert rendered is not None
    assert rendered.text == "Готово, сэр. Отчёт"


def test_assistant_output_keeps_technical_error_out_of_speech_contract() -> None:
    output = AssistantOutput.failure(
        display_text="Операция завершилась с ошибкой.",
        error=ErrorInfo(
            category=ErrorCategory.MODEL_FAILURE,
            technical_message="HTTP 455 provider=request-123",
            provider="remote_api",
            request_id="request-123",
        ),
    )

    assert output.speech_text is None
    assert output.error is not None
    assert "455" in output.error.technical_message


def test_recovered_provider_failure_is_silent_but_final_answer_is_spoken() -> None:
    mapper = UserFriendlyErrorMapper()
    renderer = SpeechRenderer()
    recovered = mapper.map(
        ErrorInfo(
            category=ErrorCategory.PROVIDER_UNAVAILABLE,
            technical_message="HTTP 455",
            recovered=True,
        )
    )
    final = AssistantOutput.natural("Готово, сэр.")

    assert renderer.render(recovered) is None
    assert renderer.render(final).text == "Готово, сэр."


def test_agent_outcome_conversion_keeps_trace_in_debug_not_speech() -> None:
    outcome = SimpleNamespace(
        text="Сэр, здесь возникла проблема.",
        mode="model_error",
        trace=["provider remote_api returned HTTP 455 request_id=abc"],
        verified=False,
        needs_confirmation=False,
    )

    output = assistant_output_from_outcome(outcome)

    assert output.error is not None
    assert "455" in output.debug["trace"][0]
    assert "455" not in (output.speech_text or "")
    assert SpeechRenderer().render(output).text.startswith("Сэр,")


def test_terminal_failure_uses_short_natural_russian_sentence() -> None:
    mapper = UserFriendlyErrorMapper()

    output = mapper.map(ErrorInfo(
        category=ErrorCategory.UNKNOWN_FAILURE,
        technical_message="Exception: HTTP 455 request_id=abc",
    ))

    assert output.speech_text == "Сэр, здесь что-то пошло не так. Я пока не смог это обойти."
    assert "455" not in output.speech_text
    assert "error" not in output.speech_text.lower()


@pytest.mark.parametrize("mode", ("normal", "focused", "quiet", "urgent", "amused", "background"))
def test_all_voice_personality_modes_produce_bounded_profiles(mode: str) -> None:
    rendered = SpeechRenderer().render(AssistantOutput.natural("Готово, сэр.", speech_mode=mode))

    assert isinstance(rendered, RenderedSpeech)
    assert rendered.mode == mode
    assert 0.9 <= rendered.rate <= 1.1
    assert 0.0 < rendered.volume <= 1.0


def test_runtime_config_selects_local_russian_piper_and_no_english_fallback() -> None:
    settings = load_config()
    tts = PiperTTS(settings)

    selected = tts._select_voice("English text must not select an English system voice")

    assert settings.voice.provider == "piper"
    assert settings.voice.language == "ru"
    assert settings.voice.fallback == "none"
    assert settings.voice.resolved_piper_model.name == "ru_RU-dmitri-medium.onnx"
    assert selected is not None
    assert selected.language == "ru"
    assert "jarvis-medium" not in tts.available_voices


def test_piper_prefers_project_runtime_over_unversioned_path_binary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A random PATH piper must not silently replace the validated runtime."""
    models_dir = tmp_path / "data" / "models"
    bundled = models_dir.parent / "runtime" / "piper" / "piper.exe"
    bundled.parent.mkdir(parents=True)
    bundled.write_bytes(b"validated local runtime fixture")

    tts = PiperTTS.__new__(PiperTTS)
    tts._settings = SimpleNamespace(
        models_dir=models_dir,
        voice=SimpleNamespace(piper_binary_path="piper"),
    )
    monkeypatch.setattr(PiperTTS, "_which", staticmethod(lambda _cmd: True))

    assert tts._resolve_binary() == bundled


def test_piper_subprocess_forces_utf8_stdin_on_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cyrillic bytes must not be decoded through the Windows code page."""
    voice = VoiceConfig(
        "ru_RU-dmitri-medium",
        tmp_path / "voice.onnx",
        tmp_path / "voice.onnx.json",
        language="ru",
        noise_scale=0.0,
        noise_w=0.0,
    )
    tts = PiperTTS.__new__(PiperTTS)
    tts._available = True
    tts._target_language = "ru"
    tts._binary = Path("piper.exe")
    tts._select_voice = lambda _text: voice
    captured: dict[str, object] = {}

    def fake_run(cmd, **kwargs):
        captured.update(kwargs)
        output = Path(cmd[cmd.index("--output_file") + 1])
        output.write_bytes(b"generated wav fixture")
        return SimpleNamespace(returncode=0, stderr=b"")

    monkeypatch.setattr("core.voice.tts.subprocess.run", fake_run)

    assert tts.synthesize_to_file("Сэр, я вас понял.", tmp_path / "out.wav")
    assert captured["env"]["PYTHONIOENCODING"] == "utf-8"
    assert captured["env"]["PYTHONUTF8"] == "1"


def test_missing_russian_voice_never_falls_back_to_english_voice(tmp_path: Path) -> None:
    tts = PiperTTS.__new__(PiperTTS)
    english = VoiceConfig("english", tmp_path / "english.onnx",
                          tmp_path / "english.json", language="en")
    tts._voices = {"english": english}
    tts._default_voice = "english"
    tts._target_language = "ru"
    tts._voice_settings = SimpleNamespace(voice="english", fallback="none")

    assert tts._select_voice("Hello") is None


def test_piper_personality_volume_scales_pcm_wav(tmp_path: Path) -> None:
    path = tmp_path / "quiet.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(22050)
        wav.writeframes(array("h", [1000, -1000, 2000, -2000]).tobytes())

    PiperTTS._apply_volume(path, 0.5)

    with wave.open(str(path), "rb") as wav:
        samples = array("h", wav.readframes(wav.getnframes()))
    assert list(samples) == [500, -500, 1000, -1000]


class _RecordingTTS:
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.stopped = 0

    def speak_rendered(self, item: RenderedSpeech) -> None:
        self.spoken.append(item.text)

    def stop_speaking(self) -> None:
        self.stopped += 1


def test_queue_accepts_structured_output_and_barge_in_still_interrupts() -> None:
    engine = _RecordingTTS()
    queue = TTSQueue(engine, renderer=SpeechRenderer())
    queue.start()
    try:
        queue.add_output(AssistantOutput.natural("Готово, сэр."))
        deadline = time.time() + 1
        while not engine.spoken and time.time() < deadline:
            time.sleep(0.01)
        queue.interrupt()
    finally:
        queue.stop()

    assert engine.spoken == ["Готово, сэр."]
    assert engine.stopped >= 1


def test_queue_defense_in_depth_blocks_legacy_raw_error() -> None:
    engine = _RecordingTTS()
    queue = TTSQueue(engine, renderer=SpeechRenderer())
    queue.start()
    try:
        queue.add_to_queue("Error 455")
        time.sleep(0.05)
    finally:
        queue.stop()

    assert engine.spoken == []


def test_websocket_speech_boundary_rejects_raw_event_messages() -> None:
    from core.ws_server import JarvisWSServer

    queued = []
    server = JarvisWSServer.__new__(JarvisWSServer)
    server._settings = SimpleNamespace(
        voice=SimpleNamespace(tts_enabled=True, tts_always_on=True)
    )
    server._orch = SimpleNamespace(
        _tts_queue=SimpleNamespace(add_output=lambda output: queued.append(output))
    )

    server._speak("Error 455")
    server._speak(AssistantOutput.natural("Готово, сэр."))

    assert len(queued) == 1
    assert queued[0].speech_text == "Готово, сэр."
