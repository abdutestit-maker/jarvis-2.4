"""Маскировка секретов в логах/аргументах (P0 §4, Q04).

DoD Q04: verifier/repair/agent печатают аргументы инструментов БЕЗ
секретов. Аргументы могут содержать ключи/токены/пароли (например, если
модель или пользователь передаёт ``api_key=...`` в аргументах вызова),
и они не должны попадать в лог в открытом виде.

Переиспользует регэксп ``_RE_SECRET`` из ``core.memory.secret_filter``
(там же живёт очистка контента ДЛЯ ПАМЯТИ, P1 §1.5) — избегаем дублирования
единого паттерна секретов. Здесь — только маскировка ПРИ ПЕЧАТИ, не очистка
для хранения.

``redact_secrets``:
    * идемпотентна (повторный вызов не умножает звёздочки);
    * безопасна к None/не-str данным (возвращает как есть);
    * не меняет семантику выполнения — только строковое представление для лога.
"""

from __future__ import annotations

from typing import Any

from core.memory.secret_filter import _RE_SECRET
from core.utils.logger import get_logger

__all__ = ["redact_secrets", "redact_args"]

log = get_logger(__name__)


def redact_secrets(value: Any) -> Any:
    """Маскирует секреты в строковом представлении ``value``.

    Если ``value`` — строка, секреты заменяются на ``<secret>``. Иначе
    (dict/list/число/None) возвращается как есть (маскировка args делается
    отдельно в ``redact_args``).
    """
    if not isinstance(value, str):
        return value
    if not value:
        return value
    # Заменяем весь совпавший секретный кусок единым маркером (идемпотентно).
    return _RE_SECRET.sub("<secret>", value)


def redact_args(args: Any) -> Any:
    """Рекурсивно маскирует секреты в аргументах инструмента перед печатью.

    Args:
        args: обычно ``Dict[str, Any]`` (аргументы инструмента).

    Returns:
        Копия структуры с замаскированными секретами в строках/значениях.
        Исходный ``args`` НЕ мутируется.
    """
    if isinstance(args, dict):
        return {k: redact_args(v) for k, v in args.items()}
    if isinstance(args, (list, tuple)):
        return type(args)(redact_args(v) for v in args)  # type: ignore[arg-type]
    if isinstance(args, str):
        return redact_secrets(args)
    return args
