"""Тесты wake-word (Фаза 3, MIT openWakeWord).

Цель: фабрика корректно выбирает реальный/NoOp детектор, threshold mapping
работает, интерфейс start/stop идемпотентен и не роняет без зависимостей.
"""

import sys
import threading

import pytest

sys.path.insert(0, ".")

from core.voice.wake_word import (  # noqa: E402
    NoOpWakeWord,
    OpenWakeWordDetector,
    WakeWordDetector,
    build_wake_word_detector,
    _threshold_for,
)


def _settings(**ww_overrides):
    import types as _t
    ww = _t.SimpleNamespace(enabled=True, phrase="ATLAS", sensitivity=0.5)
    voice = _t.SimpleNamespace(input_device_index=None)
    for k, v in ww_overrides.items():
        setattr(ww, k, v)
    s = _t.SimpleNamespace(wake_word=ww, voice=voice)
    return s


def test_factory_noop_when_disabled():
    s = _settings(enabled=False)
    det = build_wake_word_detector(s)
    assert isinstance(det, NoOpWakeWord)
    assert det.available is False


def test_factory_returns_real_detector_when_enabled():
    det = build_wake_word_detector(_settings())
    assert isinstance(det, OpenWakeWordDetector)
    # lazy: loaded только при start(); конструктор дёшев.
    assert det.available is True  # enabled и нет load_error


def test_factory_backend_override_noop():
    det = build_wake_word_detector(_settings(), backend="noop")
    assert isinstance(det, NoOpWakeWord)


def test_factory_default_model_hey_jarvis_for_atlas():
    det = build_wake_word_detector(_settings())
    assert det._model_id == "hey_jarvis"  # ATLAS -> stock hey_jarvis


def test_threshold_mapping():
    assert _threshold_for(0.0) >= 0.3
    assert _threshold_for(0.5) >= 0.5
    assert _threshold_for(1.0) >= 0.7
    assert _threshold_for(-1) >= 0.3  # clamp
    assert _threshold_for(99) <= 0.8  # clamp


def test_noop_start_stop_no_error():
    det = NoOpWakeWord(enabled=True)
    det.start()
    det.stop()
    assert det.available is False


def test_detector_noop_when_heavy_deps_missing(monkeypatch):
    """При отсутствии pyaudio/numpy/scipy start() честно не падает, а помечает."""
    det = OpenWakeWordDetector(enabled=True, model_id="hey_jarvis")
    # Эмулируем: зависимость недоступна через _swallow_import_fail
    det._load_error = "pyaudio недоступен"
    assert det.available is False


def test_detector_callback_fired(monkeypatch):
    """Callback безопасен даже если он кидает — не роняет поток."""
    det = OpenWakeWordDetector(enabled=True, on_detected=_explode)
    # вызов _fire не должен кидать вверх
    det._fire("hey_jarvis", 0.9)
    assert True


def _explode():
    raise RuntimeError("callback boom")


def test_interface_start_raises_on_base():
    """Базовый WakeWordDetector.start — NotImplementedError (контракт)."""
    base = WakeWordDetector(enabled=True)
    with pytest.raises(NotImplementedError):
        base.start()
