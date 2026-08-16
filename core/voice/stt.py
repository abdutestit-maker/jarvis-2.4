"""Speech-to-Text (STT) — минимальная рабочая версия (P5 §5.9).

Реализация поверх ``faster-whisper`` (MIT, быстрая локальная интеграция).
Все тяжёлые зависимости импортируются LAZY — модуль не падает при
отсутствии библиотек, а честно сообщает, что нужно установить.

Поведение:
    * ``settings.voice.stt_enabled = False`` (по умолчанию) ->
      ``is_available()`` возвращает False, вызовы кидают ``NotImplementedError``
      с понятным сообщением (обратная совместимость со старой заглушкой).
    * ``stt_enabled = True`` и ``faster-whisper`` установлен ->
      РЕАЛЬНОЕ распознавание (``transcribe_file`` / ``listen_once``).
    * ``stt_enabled = True``, но библиотека не стоит ->
      ``is_available()`` = False, вызовы кидают ``RuntimeError`` с инструкцией
      по установке (а не молча «не реализовано»).

Бэкенд выбирается автоматически:
    ``faster-whisper`` (приоритет, MIT, локально, без юр. рисков).
"""

from __future__ import annotations

import io
import tempfile
import time
from typing import List, Optional, Tuple

from config.settings import Settings
from core.utils.logger import get_logger

__all__ = ["STTEngine", "STT_DISABLED_MSG"]

log = get_logger(__name__)

#: Сообщение, когда STT отключён флагом.
STT_DISABLED_MSG = (
    "STT отключён. Установите settings.voice.stt_enabled=True "
    "для работы распознавания речи."
)

#: Инструкция, когда включено, но библиотека не установлена.
STT_NEED_BACKEND_MSG = (
    "STT включён (settings.voice.stt_enabled=True), но не найден движок. "
    "Установите: pip install faster-whisper sounddevice scipy\n"
    "(faster-whisper — MIT, локальное распознавание без юридических рисков)."
)

#: Модель faster-whisper по умолчанию (small — баланс точность/скорость).
DEFAULT_WHISPER_MODEL = "small"


class STTEngine:
    """Минимальный, но РАБОЧИЙ STT-движок поверх faster-whisper."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._enabled = bool(
            getattr(getattr(settings, "voice", None), "stt_enabled", False)
        )
        if not self._enabled:
            log.info("STT отключён (settings.voice.stt_enabled=False)")
        else:
            # Проверяем доступность бэкенда сразу, чтобы is_available() было
            # точным (а не падало в рантайме неожиданно).
            self._backend_ok = self._probe_backend()
            if not self._backend_ok:
                log.warning("STT включён, но движок недоступен: %s", STT_NEED_BACKEND_MSG)

    # ------------------------------------------------------------------ #
    #  Доступность
    # ------------------------------------------------------------------ #

    def is_available(self) -> bool:
        """True, если STT включён И движок реально доступен."""
        return self._enabled and getattr(self, "_backend_ok", False)

    def _probe_backend(self) -> bool:
        """Пробует лениво импортировать faster-whisper (без загрузки модели)."""
        try:
            import faster_whisper  # noqa: F401
            return True
        except Exception as exc:  # pragma: no cover - зависит от окружения
            log.debug("faster-whisper недоступен: %s", exc)
            return False

    # ------------------------------------------------------------------ #
    #  Транскрипция файла
    # ------------------------------------------------------------------ #

    def transcribe_file(self, audio_path: str) -> str:
        """Транскрибирует аудиофайл в текст (реально, если движок доступен)."""
        if not self._enabled:
            raise NotImplementedError(STT_DISABLED_MSG)
        if not self.is_available():
            raise RuntimeError(STT_NEED_BACKEND_MSG)

        try:
            from faster_whisper import WhisperModel
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(STT_NEED_BACKEND_MSG) from exc

        model_size = getattr(
            getattr(self._settings, "voice", None), "stt_model", DEFAULT_WHISPER_MODEL
        ) or DEFAULT_WHISPER_MODEL
        device = getattr(getattr(self._settings, "voice", None), "stt_device", "cpu") or "cpu"

        log.info("STT: загрузка модели '%s' на %s...", model_size, device)
        model = WhisperModel(model_size, device=device, compute_type="int8")
        segments: List[Tuple[float, float, str]] = []
        for seg in model.transcribe(audio_path, language="ru", beam_size=5)[0]:
            segments.append((seg.start, seg.end, seg.text))
        text = " ".join(s.strip() for _, _, s in segments if s and s.strip())
        log.info("STT: распознано %d сегментов, %d символов", len(segments), len(text))
        return text.strip()

    # ------------------------------------------------------------------ #
    #  Потоковое / одноразовое прослушивание с микрофона
    # ------------------------------------------------------------------ #

    def listen_once(self, timeout: float = 5.0, sample_rate: int = 16000) -> str:
        """Одноразовое прослушивание с микрофона -> текст.

        Записывает ``timeout`` секунд через sounddevice, сохраняет во временный
        WAV и прогоняет через :meth:`transcribe_file`.
        """
        if not self._enabled:
            raise NotImplementedError(STT_DISABLED_MSG)
        if not self.is_available():
            raise RuntimeError(STT_NEED_BACKEND_MSG)

        try:
            import sounddevice as sd  # type: ignore
            import scipy.io.wavfile as wav  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Для listen_once нужны sounddevice и scipy: "
                "pip install sounddevice scipy"
            ) from exc

        log.info("STT: слушаю микрофон %.1fс...", timeout)
        recording = sd.rec(
            int(timeout * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
        )
        sd.wait()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav.write(tmp.name, sample_rate, recording)
            tmp_path = tmp.name
        try:
            return self.transcribe_file(tmp_path)
        finally:
            import os

            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    # ------------------------------------------------------------------ #
    #  Потоковая транскрипция (минимальный hook — делегирует в файл)
    # ------------------------------------------------------------------ #

    def transcribe_stream(self, audio_stream) -> str:
        """Транскрибирует аудиопоток.

        Минимальная версия (P5 §5.9): принимает уже записанный буфер
        (bytes/bytearray/.wav) и делегирует в ``transcribe_file`` через
        временный файл. Полноценный VAD-streaming — расширение на будущее.
        """
        if not self._enabled:
            raise NotImplementedError(STT_DISABLED_MSG)
        if not self.is_available():
            raise RuntimeError(STT_NEED_BACKEND_MSG)

        import os

        data = audio_stream.read() if hasattr(audio_stream, "read") else audio_stream
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            if isinstance(data, (bytes, bytearray)):
                tmp.write(bytes(data))
            elif isinstance(data, io.BytesIO):
                tmp.write(data.getvalue())
            else:
                raise ValueError("transcribe_stream: неподдерживаемый тип потока")
            tmp_path = tmp.name
        try:
            return self.transcribe_file(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
