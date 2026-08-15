"""Реестр инструментов (ToolRegistry).

Хранит зарегистрированные инструменты, предоставляет поиск по имени,
генерацию JSON Schema для function calling и глобальный DEFAULT_REGISTRY.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.actions.base import Tool
from core.utils.logger import get_logger

__all__ = ["ToolRegistry", "DEFAULT_REGISTRY"]

log = get_logger(__name__)


class ToolRegistry:
    """Реестр доступных инструментов.

    Инструменты регистрируются при импорте модулей core.actions.*.
    Оркестратор использует ``DEFAULT_REGISTRY``.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Регистрирует инструмент.

        Args:
            tool: экземпляр Tool.

        Raises:
            ValueError: если инструмент с таким именем уже зарегистрирован.
        """
        if tool.name in self._tools:
            raise ValueError(f"Инструмент '{tool.name}' уже зарегистрирован")
        self._tools[tool.name] = tool
        log.debug("Зарегистрирован инструмент: %s", tool.name)

    def get(self, name: str) -> Optional[Tool]:
        """Возвращает инструмент по имени или None."""
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        """Список всех зарегистрированных инструментов."""
        return list(self._tools.values())

    def generate_schema(self) -> List[Dict[str, Any]]:
        """Генерирует список JSON Schema для function calling (OpenAI-compatible).

        Returns:
            Список словарей вида:
            {
                "type": "function",
                "function": {
                    "name": "...",
                    "description": "...",
                    "parameters": {...}
                }
            }
        """
        schemas = []
        for tool in self._tools.values():
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.input_schema,
                    },
                }
            )
        return schemas

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)

    def __repr__(self) -> str:
        return f"<ToolRegistry tools={list(self._tools.keys())}>"


# Глобальный реестр — заполняется при импорте core.actions
DEFAULT_REGISTRY = ToolRegistry()