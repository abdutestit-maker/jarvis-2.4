"""Voice (TTS/STT/Notifications) — публичный контракт.

Импорт::

    from core.voice import PiperTTS, TTSQueue, STTEngine, show_toast
"""

from __future__ import annotations

from core.voice.notifications import show_toast
from core.voice.stt import STTEngine, STT_DISABLED_MSG
from core.voice.tts import PiperTTS
from core.voice.tts_queue import TTSQueue

__all__ = [
    "PiperTTS",
    "TTSQueue",
    "STTEngine",
    "STT_DISABLED_MSG",
    "show_toast",
]