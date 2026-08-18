"""Natural-language speech rendering after the typed response boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from core.voice.output import AssistantOutput
from core.voice.tts_sanitizer import sanitize_for_tts


@dataclass(frozen=True)
class VoiceMode:
    rate: float
    volume: float


@dataclass(frozen=True)
class RenderedSpeech:
    text: str
    mode: str = "normal"
    rate: float = 1.0
    volume: float = 1.0


DEFAULT_MODES: dict[str, VoiceMode] = {
    "normal": VoiceMode(1.00, 1.00),
    "focused": VoiceMode(1.03, 1.00),
    "quiet": VoiceMode(0.96, 0.72),
    "urgent": VoiceMode(1.04, 1.00),
    "amused": VoiceMode(1.02, 0.95),
    "background": VoiceMode(0.98, 0.85),
}


class SpeechRenderer:
    def __init__(self, voice_settings: Any = None) -> None:
        self._modes = dict(DEFAULT_MODES)
        configured = getattr(voice_settings, "modes", None)
        if configured:
            items = configured.items() if hasattr(configured, "items") else []
            for name, raw in items:
                rate = raw.get("rate", 1.0) if isinstance(raw, dict) else getattr(raw, "rate", 1.0)
                volume = raw.get("volume", 1.0) if isinstance(raw, dict) else getattr(raw, "volume", 1.0)
                self._modes[str(name)] = VoiceMode(
                    max(0.9, min(1.1, float(rate))),
                    max(0.05, min(1.0, float(volume))),
                )

    def render(self, output: AssistantOutput) -> Optional[RenderedSpeech]:
        if not isinstance(output, AssistantOutput):
            raise TypeError("SpeechRenderer accepts AssistantOutput only")
        if not output.speak or not output.speech_text:
            return None
        text = sanitize_for_tts(output.speech_text, fallback="")
        if not text:
            return None
        mode_name = output.speech_mode if output.speech_mode in self._modes else "normal"
        mode = self._modes[mode_name]
        return RenderedSpeech(text, mode_name, mode.rate, mode.volume)


__all__ = ["DEFAULT_MODES", "RenderedSpeech", "SpeechRenderer", "VoiceMode"]
