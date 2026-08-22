"""Voice (TTS/STT/Notifications) — публичный контракт.

Импорт::

    from core.voice import PiperTTS, TTSQueue, STTEngine, show_toast
"""

from __future__ import annotations

from core.voice.notifications import show_toast
from core.voice.stt import STTEngine, STT_DISABLED_MSG, VoiceActivityDetector
from core.voice.wake_word import (
    WakeWordDetector,
    NoOpWakeWord,
    OpenWakeWordDetector,
    build_wake_word_detector,
)
from core.voice.tts import PiperTTS
from core.voice.tts_queue import TTSQueue
from core.voice.output import (
    AssistantOutput, ErrorCategory, ErrorInfo, UserFriendlyErrorMapper,
    assistant_output_from_outcome,
)
from core.voice.speech_renderer import RenderedSpeech, SpeechRenderer

__all__ = [
    "PiperTTS",
    "TTSQueue",
    "STTEngine",
    "STT_DISABLED_MSG",
    "VoiceActivityDetector",
    "WakeWordDetector",
    "NoOpWakeWord",
    "OpenWakeWordDetector",
    "build_wake_word_detector",
    "AssistantOutput",
    "ErrorCategory",
    "ErrorInfo",
    "UserFriendlyErrorMapper",
    "RenderedSpeech",
    "SpeechRenderer",
    "assistant_output_from_outcome",
    "show_toast",
]
