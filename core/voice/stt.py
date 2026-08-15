"""Speech-to-Text (STT) — заглушка.

Реальная реализация (faster-whisper / whisper.cpp) будет добавлена позже.
Пока флаг ``settings.voice.stt_enabled`` = False (по умолчанию).

Если STT отключён — методы выбрасывают ``NotImplementedError`` с понятным сообщением.
"""

from __future__ import annotations

from config.settings import Settings
from core.utils.logger import get_logger

__all__ = ["STTEngine", "STT_DISABLED_MSG"]

log = get_logger(__name__)

STT_DISABLED_MSG = (
    "STT не реализован. Включите settings.voice.stt_enabled=True "
    "и установите faster-whisper / whisper.cpp для работы."
)


class STTEngine:
    """Заглушка STT движка."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._enabled = getattr(getattr(settings, "voice", None), "stt_enabled", False)
        if not self._enabled:
            log.info("STT отключён (settings.voice.stt_enabled=False)")

    def is_available(self) -> bool:
        return self._enabled

    def transcribe_file(self, audio_path: str) -> str:
        """Транскрибирует аудиофайл в текст."""
        if not self._enabled:
            raise NotImplementedError(STT_DISABLED_MSG)
        raise NotImplementedError("STE transcribe_file: реализация будет позже")

    def transcribe_stream(self, audio_stream) -> str:
        """Транскрибирует аудиопоток (микрофон)."""
        if not self._enabled:
            raise NotImplementedError(STT_DISABLED_MSG)
        raise NotImplementedError("STE transcribe_stream: реализация будет позже")

    def listen_once(self, timeout: float = 5.0) -> str:
        """Одноразовое прослушивание с микрофона."""
        if not self._enabled:
            raise NotImplementedError(STT_DISABLED_MSG)
        raise NotImplementedError("STE listen_once: реализация будет позже")