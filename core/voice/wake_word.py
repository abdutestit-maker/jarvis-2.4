"""Wake-word (слово-пробуждение) — реальная детекция через OpenWakeWord (MIT).

Respectful port of the MIT-licensed pattern from `Shaan-alpha/jarvis-py`
(https://github.com/Shaan-alpha/jarvis-py) — openWakeWord binary, native-rate
mic capture + resample-to-16k, and a consecutive-frame debounce. Adapted to
this project's conventions: lazy MIT imports (same as STT), config from
``settings.WakeWordConfig``, and the existing ``WakeWordDetector`` interface.

Contract:
    * ``build_wake_word_detector(settings, on_detected)`` — фабрика: если
      ``wake_word.enabled`` и ``openwakeword``+``sounddevice`` установлены,
      вернёт рабочую реализацию; иначе — ``NoOpWakeWord`` с честным флагом.
    * Никогда не роняет импорт проекта: тяжёлые зависимости (pyaudio,
      numpy, scipy, openwakeword) импортируются лениво.
    * Детекция работает в отдельном потоке; ``start()/stop()`` — идемпотентны.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

from core.utils.logger import get_logger

__all__ = [
    "WakeWordDetector",
    "NoOpWakeWord",
    "OpenWakeWordDetector",
    "build_wake_word_detector",
]

log = get_logger(__name__)

#: Целевая частота openWakeWord.
_RATE = 16000
#: Кадр openWakeWord (семплов).
_CHUNK = 1280
#: Сколько кадров «прогрева» на свежей тишине (не ретриггерить прошлую речь).
_DRAIN_CHUNKS = 12
#: Блок чтения микрофона ~80 мс.
_READ_BLOCK_S = 0.08
#: ID модели openWakeWord по умолчанию (если конфиг пуст).
_DEFAULT_WAKE_MODEL = "hey_jarvis"


class WakeWordDetector:
    """Базовый контракт детектора слова-пробуждения."""

    def __init__(self, *, enabled: bool = False, phrase: str = "ATLAS",
                 sensitivity: float = 0.5,
                 on_detected: Optional[Callable[[], None]] = None) -> None:
        self.enabled = enabled
        self.phrase = phrase
        self.sensitivity = sensitivity
        self.on_detected = on_detected

    def start(self) -> None:
        """Начать (идемпотентно)."""
        raise NotImplementedError

    def stop(self) -> None:
        """Остановить (идемпотентно)."""
        raise NotImplementedError

    @property
    def available(self) -> bool:
        """Доступен ли реальный движок (не заглушка)."""
        return False


class NoOpWakeWord(WakeWordDetector):
    """Заглушка: детектор выключен или зависимость не установлена."""

    def start(self) -> None:
        log.debug("NoOp wake word: cannot start (disabled/unavailable)")

    def stop(self) -> None:
        return None


# --------------------------------------------------------------------------- #
#  Реальная реализация (OpenWakeWord)
# --------------------------------------------------------------------------- #


#: Порог срабатывания по умолчанию (0..1). sensitivity ниже = чувствительнее.
def _threshold_for(sensitivity: float) -> float:
    # sensitivity 0..1 у нас: больше = точность выше (нужен лучший скор).
    # Маппим: sensitivity 0.5 -> порог 0.5; 0 -> 0.3; 1 -> 0.8.
    s = max(0.05, min(0.95, float(sensitivity)))
    return round(0.3 + s * 0.5, 2)


class OpenWakeWordDetector(WakeWordDetector):
    """Детектор на openWakeWord (MIT) в отдельном потоке.

    Обратите внимание: этот класс лениво импортирует pyaudio/numpy/scipy и
    загружает ONNX-модель openWakeWord при старте — поэтому создание класса
    дёшево, а вся тяжёлая работа происходит в ``start()``.
    """

    def __init__(self, *, model_id: Optional[str] = None, device_index: Optional[int] = None,
                 on_detected: Optional[Callable[[], None]] = None,
                 phrase: str = "ATLAS", sensitivity: float = 0.5,
                 enabled: bool = True, model_path: Optional[str] = None) -> None:
        super().__init__(enabled=enabled, phrase=phrase, sensitivity=sensitivity,
                         on_detected=on_detected)
        self._model_id = model_id or _DEFAULT_WAKE_MODEL
        self._device_index = device_index
        self._model_path = model_path
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._model = None
        self._load_error: Optional[str] = None

    # ------------------------------------------------------------------ #
    @property
    def available(self) -> bool:
        return self._load_error is None and self.enabled

    def _swallow_import_fail(self, exc: Exception, what: str) -> bool:
        log.warning("Wake word: %s недоступен (%s). Установите: "
                    "pip install openwakeword pyaudio numpy scipy", what, exc)
        self._load_error = f"{what}: {exc}"
        return False

    # ------------------------------------------------------------------ #
    def start(self) -> None:
        if not self.enabled:
            log.info("Wake word выключен (settings.wake_word.enabled=False)")
            return
        if self._thread is not None and self._thread.is_alive():
            log.debug("Wake word уже запущен")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, name="jarvis-wake-word", daemon=True,
        )
        self._thread.start()
        log.info("Wake word thread запущен (phrase='%s', model='%s')",
                 self.phrase, self._model_id)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None

    # ------------------------------------------------------------------ #
    def _load_model(self):
        """Лениво загрузить модель openWakeWord (кэш в self._model)."""
        if self._model is not None:
            return self._model, None
        try:
            import openwakeword  # noqa: F401  (MIT; лениво)
            from openwakeword.model import Model  # type: ignore
            from openwakeword.utils import (
                download_models as _oww_download,  # type: ignore
            )
        except Exception as exc:  # noqa: BLE001
            self._swallow_import_fail(exc, "openwakeword")
            return None, self._load_error

        # Путь модели: явный > в проекте > пакетный > скачать.
        path = self._model_path
        try:
            if not path:
                import os  # noqa: F401
                import openwakeword as _oww  # noqa: F401
                base = os.path.dirname(os.path.abspath(_oww.__file__))
                pkg = os.path.join(base, "resources", "models",
                                   f"{self._model_id}_v0.1.onnx")
                if os.path.exists(pkg):
                    path = pkg
            if not path:
                _oww_download([self._model_id])
                import openwakeword as _oww2  # noqa: F401
                base2 = os.path.dirname(os.path.abspath(_oww2.__file__))
                path = os.path.join(base2, "resources", "models",
                                    f"{self._model_id}_v0.1.onnx")
        except Exception as exc:  # noqa: BLE001
            self._swallow_import_fail(exc, "модель openWakeWord")
            return None, self._load_error

        try:
            model = Model(wakeword_models=[path], inference_framework="onnx")
        except Exception as exc:  # noqa: BLE001
            self._swallow_import_fail(exc, "инициализация модели")
            return None, self._load_error
        self._model = model
        self._load_error = None
        return model, None

    # ------------------------------------------------------------------ #
    def _run(self) -> None:
        model, err = self._load_model()
        if model is None:
            log.warning("Wake word: не запустился — %s", err)
            return

        try:
            import pyaudio  # type: ignore
            import numpy as np  # type: ignore
            from scipy.signal import resample_poly  # type: ignore
        except Exception as exc:  # noqa: BLE001
            self._swallow_import_fail(exc, "pyaudio/numpy/scipy")
            return

        try:
            self._listen(model, np, pyaudio, resample_poly)
        except Exception as exc:  # noqa: BLE001
            if not self._stop_event.is_set():
                log.exception("Wake word: ошибка цикла прослушивания: %s", exc)

    # ------------------------------------------------------------------ #
    def _listen(self, model, np, pyaudio, resample_poly) -> None:
        from math import gcd

        threshold = _threshold_for(self.sensitivity)

        audio = pyaudio.PyAudio()
        try:
            idx = self._device_index
            info = (audio.get_default_input_device_info() if idx is None
                    else audio.get_device_info_by_index(idx))
            src_rate = int(info["defaultSampleRate"])
            channels = max(1, int(info.get("maxInputChannels", 1)))
            read_size = max(1, int(src_rate * _READ_BLOCK_S))

            stream = audio.open(
                format=pyaudio.paInt16, channels=channels, rate=src_rate,
                input=True, input_device_index=idx,
                frames_per_buffer=read_size,
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("Wake word: не удалось открыть микрофон: %s", exc)
            audio.terminate()
            return

        log.info("Wake word слушает: мик %s @ %s Hz, порог %.2f, ждёт '%s'",
                 idx, src_rate, threshold, self.phrase)

        def resample(samples, src):
            if src == _RATE:
                return samples
            div = gcd(int(src), _RATE)
            return resample_poly(samples.astype(np.float64),
                                 _RATE // div, int(src) // div).astype(np.int16)

        def frames():
            pending = np.empty(0, dtype=np.int16)
            while not self._stop_event.is_set():
                try:
                    data = stream.read(read_size, exception_on_overflow=False)
                except Exception:  # noqa: BLE001
                    return
                block = np.frombuffer(data, dtype=np.int16)
                if channels > 1:
                    block = block.reshape(-1, channels).mean(axis=1).astype(np.int16)
                pending = np.concatenate([pending, resample(block, src_rate)])
                while len(pending) >= _CHUNK:
                    yield pending[:_CHUNK]
                    pending = pending[_CHUNK:]

        try:
            # Прогрев: отсечь эхо прошлой сессии/TTS.
            fgen = frames()
            for _ in range(_DRAIN_CHUNKS):
                if self._stop_event.is_set():
                    return
                model.predict(next(fgen))

            streak = 0
            for frame in fgen:
                if self._stop_event.is_set():
                    return
                pred = model.predict(frame)
                best = max(pred.items(), key=lambda kv: kv[1], default=(None, 0.0))
                name, score = best
                if score and score > threshold:
                    streak += 1
                    if streak >= 2:  # debounce: 2 подряд кадра
                        log.info("Wake word распознан: %s (%.2f)",
                                 name, score)
                        self._fire(name, score)
                        streak = 0
                else:
                    streak = 0
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()

    def _fire(self, name: str, score: float) -> None:
        if self.on_detected is not None:
            try:
                self.on_detected()
            except Exception as exc:  # noqa: BLE001
                log.debug("Wake word: callback не смог выполниться: %s", exc)


# --------------------------------------------------------------------------- #
#  Фабрика
# --------------------------------------------------------------------------- #


def build_wake_word_detector(settings, on_detected: Optional[Callable[[], None]] = None,
                             *, backend: Optional[str] = None) -> WakeWordDetector:
    """Построить детектор по конфигу (lazy): реальный или NoOp.

    ``backend`` = "openwakeword" (по умолчанию) или "noop" (принудительно).
    """
    ww = getattr(settings, "wake_word", None)
    enabled = bool(getattr(ww, "enabled", False))
    phrase = getattr(ww, "phrase", "ATLAS")
    sensitivity = float(getattr(ww, "sensitivity", 0.5))

    chosen = backend or ("openwakeword" if enabled else "noop")
    if chosen == "noop":
        return NoOpWakeWord(enabled=enabled, phrase=phrase,
                            sensitivity=sensitivity, on_detected=on_detected)

    model_id = _DEFAULT_WAKE_MODEL
    # "ATLAS" — не встроенная модель openWakeWord. Если конфиг не меняли,
    # берём hey_jarvis как рабочую stock-модель (Training для своего слова — потом).
    if phrase and phrase.strip().casefold() not in {"atlas", ""}:
        model_id = phrase.strip().strip("_").casefold().replace(" ", "_")
    input_dev = getattr(getattr(settings, "voice", None), "input_device_index", None)
    return OpenWakeWordDetector(
        model_id=model_id, phrase=phrase, sensitivity=sensitivity,
        enabled=enabled, on_detected=on_detected, device_index=input_dev,
    )
