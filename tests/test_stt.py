"""P5 §5.9 — минимальная рабочая STT-версия.

Тесты проверяют контракт STTEngine БЕЗ обязательной тяжёлой нагрузки модели:
    * при stt_enabled=False -> is_available()=False, вызовы кидают
      NotImplementedError с понятным сообщением (обратная совместимость);
    * при stt_enabled=True -> is_available() отражает РЕАЛЬНУЮ доступность
      бэкенда (faster-whisper установлен ИЛИ нет); если бэкенд есть —
      движок помечается доступным (реальная интеграция готова к работе).

Реальное распознавание (faster-whisper) покрывается вручную при наличии
модели; здесь фиксируем корректный контракт движка в обоих состояниях.
"""

from __future__ import annotations

import importlib.util

from config.settings import Settings
from core.voice.stt import STTEngine, STT_DISABLED_MSG

_HAS_FASTER_WHISPER = importlib.util.find_spec("faster_whisper") is not None


def _settings_with_stt(enabled: bool) -> Settings:
    s = Settings()
    s.voice.stt_enabled = enabled
    return s


def test_stt_disabled_is_not_available():
    """По умолчанию (stt_enabled=False) движок недоступен."""
    eng = STTEngine(_settings_with_stt(False))
    assert eng.is_available() is False


def test_stt_disabled_raises_clear_error():
    """Отключённый STT кидает понятный NotImplementedError."""
    eng = STTEngine(_settings_with_stt(False))
    try:
        eng.transcribe_file("dummy.wav")
        raise AssertionError("ожидалось NotImplementedError")
    except NotImplementedError as exc:
        assert STT_DISABLED_MSG in str(exc)


def test_stt_enabled_reflects_real_backend():
    """stt_enabled=True -> is_available() == (faster-whisper реально доступен)."""
    eng = STTEngine(_settings_with_stt(True))
    assert eng.is_available() is _HAS_FASTER_WHISPER, (
        "is_available() должен точно отражать наличие бэкенда faster-whisper"
    )


def test_stt_enabled_without_backend_raises_runtime_error():
    """stt_enabled=True, но бэкенд НЕ установлен -> RuntimeError с инструкцией."""
    if _HAS_FASTER_WHISPER:
        # В этом окружении бэкенд есть — пропускаем проверку отсутствия.
        return
    eng = STTEngine(_settings_with_stt(True))
    try:
        eng.listen_once(timeout=0.1)
        raise AssertionError("ожидалось RuntimeError (нет бэкенда)")
    except RuntimeError as exc:
        assert "faster-whisper" in str(exc)
