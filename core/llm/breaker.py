"""Circuit Breaker для LLM-моделей (Sprint 3, STEP 5.3).

Если модель провайдера падает N раз ПОДРЯД — она временно исключается из
цепочки выбора тиров (breaker «разомкнут»). Ключ — ``provider:model``:
несколько тиров часто сидят на одном провайдере, и падение одной модели
(am/free) не должно блокировать остальные (cx/gpt-5.5). Через
``cooldown_sec`` breaker снова пропускает запрос (half-open probe):
успех — сброс счётчика, новая ошибка — снова размыкание. Локальная
модель (офлайн-фолбэк TIER 4) никогда не проходит через breaker —
офлайн-ответ гарантирован всегда.

Модуль потокобезопасен и не падает ни при каких ошибках: breaker — это
оптимизация маршрутизации, а не критический путь.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict

from core.utils.logger import get_logger

__all__ = [
    "FAILURE_THRESHOLD",
    "COOLDOWN_SEC",
    "is_open",
    "record_success",
    "record_failure",
    "status",
    "reset",
]

log = get_logger(__name__)

#: Сколько подряд неудач размыкают цепь провайдера.
FAILURE_THRESHOLD = 3

#: Сколько секунд провайдер исключается из выбора после размыкания.
COOLDOWN_SEC = 60.0


class _BreakerState:
    __slots__ = ("consecutive_failures", "opened_at")

    def __init__(self) -> None:
        self.consecutive_failures = 0
        self.opened_at: float = 0.0


_lock = threading.Lock()
_states: Dict[str, _BreakerState] = {}


def _state_for(provider: str) -> _BreakerState:
    state = _states.get(provider)
    if state is None:
        state = _BreakerState()
        _states[provider] = state
    return state


def is_open(provider: str) -> bool:
    """True — провайдер временно исключён из цепочки (недавние сбои).

    После истечения cooldown возвращает False (разрешаем пробный запрос),
    но счётчик неудач сохраняется: первая же новая ошибка снова размыкает
    цепь ещё на ``COOLDOWN_SEC``.
    """
    name = (provider or "").strip().lower()
    if not name:
        return False
    with _lock:
        state = _states.get(name)
        if state is None or state.consecutive_failures < FAILURE_THRESHOLD:
            return False
        if time.monotonic() - state.opened_at >= COOLDOWN_SEC:
            # half-open: пропускаем пробный запрос.
            return False
        return True


def record_success(provider: str) -> None:
    """Успешный вызов провайдера — сбрасываем серию неудач."""
    name = (provider or "").strip().lower()
    if not name:
        return
    with _lock:
        state = _state_for(name)
        if state.consecutive_failures:
            log.info("Circuit breaker %s: серия неудач сброшена (успешный вызов)", name)
        state.consecutive_failures = 0
        state.opened_at = 0.0


def record_failure(provider: str) -> None:
    """Неудачный вызов провайдера (исчерпаны попытки / нет соединения)."""
    name = (provider or "").strip().lower()
    if not name:
        return
    with _lock:
        state = _state_for(name)
        state.consecutive_failures += 1
        if state.consecutive_failures >= FAILURE_THRESHOLD:
            state.opened_at = time.monotonic()
            log.warning(
                "Circuit breaker %s: РАЗОМКНУТ на %d с (%d неудач подряд)",
                name, COOLDOWN_SEC, state.consecutive_failures,
            )


def status(provider: str) -> Dict[str, Any]:
    """Состояние breaker'а провайдера (диагностика/тесты)."""
    name = (provider or "").strip().lower()
    with _lock:
        state = _states.get(name)
        if state is None:
            return {"provider": name, "consecutive_failures": 0, "open": False}
        return {
            "provider": name,
            "consecutive_failures": state.consecutive_failures,
            "open": is_open(name),
        }


def reset() -> None:
    """Полный сброс всех breaker'ов (тесты / смена конфигурации)."""
    with _lock:
        _states.clear()
