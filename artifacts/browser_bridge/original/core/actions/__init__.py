"""Движок действий Джарвиса — публичный контракт.

Все инструменты регистрируются в ``DEFAULT_REGISTRY`` при импорте этого пакета.

Использование::

    from core.actions import (
        Tool, ToolContext, ActionResult,
        ToolRegistry, DEFAULT_REGISTRY, execute_tool,
        # Конкретные инструменты доступны через реестр:
        # DEFAULT_REGISTRY.get("open_app"), DEFAULT_REGISTRY.get("web_search") и т.д.
    )
"""

from __future__ import annotations

# Базовые классы
from core.actions.base import Tool, ToolContext, ActionResult

# Реестр и исполнитель
from core.actions.registry import ToolRegistry, DEFAULT_REGISTRY
from core.actions.executor import execute_tool, validate_args

# Импорт всех инструментов для авто-регистрации
from core.actions import (  # noqa: F401
    app_control,
    system,
    web_search,
    web_fetch,
    filesystem,
    reminders,
    weather,
    screen_capture,
)

__all__ = [
    "Tool",
    "ToolContext",
    "ActionResult",
    "ToolRegistry",
    "DEFAULT_REGISTRY",
    "execute_tool",
    "validate_args",
]

# Удобная функция для получения схемы всех инструментов (для LLM function calling)
def get_tools_schema() -> list[dict]:
    """Возвращает JSON Schema всех зарегистрированных инструментов для function calling."""
    return DEFAULT_REGISTRY.generate_schema()


def list_available_tools() -> list[str]:
    """Список имён всех доступных инструментов."""
    return list(DEFAULT_REGISTRY._tools.keys())


# Логгируем загруженные инструменты
from core.utils.logger import get_logger
log = get_logger(__name__)
log.info("Движок действий инициализирован. Инструменты: %s", list_available_tools())
