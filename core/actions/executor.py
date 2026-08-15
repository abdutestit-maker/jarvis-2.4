"""Исполнитель инструментов (execute_tool).

Валидация аргументов по JSON Schema, retry на временные сбои,
всегда возвращает ActionResult (никогда не бросает исключение наружу).
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import jsonschema
from jsonschema import ValidationError

from core.actions.base import ActionResult, Tool, ToolContext
from core.actions.registry import ToolRegistry
from core.utils.logger import get_logger

__all__ = ["execute_tool", "validate_args"]

log = get_logger(__name__)


def validate_args(schema: Dict[str, Any], args: Dict[str, Any]) -> Optional[str]:
    """Валидирует аргументы по JSON Schema.

    Args:
        schema: JSON Schema (draft-07).
        args: словарь аргументов.

    Returns:
        None — валидация прошла.
        Строка — текст ошибки валидации.
    """
    try:
        jsonschema.validate(instance=args, schema=schema)
    except ValidationError as exc:
        # Формируем читаемое сообщение
        path = " -> ".join(str(p) for p in exc.path) if exc.path else "корень"
        return f"Валидация аргументов не прошла ({path}): {exc.message}"
    except Exception as exc:  # jsonschema может бросить другие ошибки
        return f"Ошибка валидатора: {exc}"
    return None


def execute_tool(
    registry: ToolRegistry,
    tool_name: str,
    args: Dict[str, Any],
    context: ToolContext,
    max_retries: int = 2,
    retry_delay: float = 0.5,
) -> ActionResult:
    """Выполняет инструмент с валидацией и retry.

    Args:
        registry: реестр инструментов.
        tool_name: имя инструмента.
        args: аргументы вызова.
        context: контекст выполнения.
        max_retries: число повторных попыток при временных ошибках (default 2).
        retry_delay: задержка между попытками в секундах (default 0.5).

    Returns:
        ActionResult — всегда возвращается, ok=False при любой ошибке.
    """
    tool = registry.get(tool_name)
    if tool is None:
        return ActionResult(
            tool=tool_name,
            args=args,
            ok=False,
            error=f"Инструмент '{tool_name}' не найден в реестре",
        )

    # Валидация аргументов
    validation_error = validate_args(tool.input_schema, args)
    if validation_error is not None:
        log.warning("Валидация аргументов '%s' не прошла: %s", tool_name, validation_error)
        return ActionResult(
            tool=tool_name,
            args=args,
            ok=False,
            error=validation_error,
        )

    # Выполнение с retry
    last_error: Optional[str] = None
    for attempt in range(max_retries + 1):
        start = time.perf_counter()
        try:
            result = tool.run(args, context)
            if not isinstance(result, ActionResult):
                # На случай, если инструмент вернул не ActionResult
                result = ActionResult(
                    tool=tool_name,
                    args=args,
                    ok=False,
                    error=f"Инструмент вернул не ActionResult: {type(result)}",
                )
            result.duration_sec = time.perf_counter() - start
            if not result.ok and attempt < max_retries:
                # Временная ошибка — пробуем ещё раз
                last_error = result.error
                log.debug(
                    "Инструмент '%s' вернул ошибку (попытка %d/%d): %s — retry",
                    tool_name,
                    attempt + 1,
                    max_retries + 1,
                    last_error,
                )
                time.sleep(retry_delay)
                continue
            return result
        except Exception as exc:  # Никакие исключения не должны выходить наружу
            duration = time.perf_counter() - start
            last_error = f"{type(exc).__name__}: {exc}"
            log.error("Исключение в инструменте '%s' (попытка %d/%d): %s",
                      tool_name, attempt + 1, max_retries + 1, exc)
            if attempt < max_retries:
                time.sleep(retry_delay)
                continue
            return ActionResult(
                tool=tool_name,
                args=args,
                ok=False,
                error=last_error,
                duration_sec=duration,
            )

    # Все попытки исчерпаны
    return ActionResult(
        tool=tool_name,
        args=args,
        ok=False,
        error=last_error or "Неизвестная ошибка после всех попыток",
    )