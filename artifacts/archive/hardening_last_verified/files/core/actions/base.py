"""Базовые классы для движка действий.

``Tool`` — абстрактный инструмент, который оркестратор может вызвать.
``ToolContext`` — контекст выполнения (доступ к settings, state, user_id).
Все конкретные инструменты наследуются от ``Tool``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import threading
from typing import Any, Dict, Optional

from config.settings import Settings
from core.state import JarvisState


@dataclass(slots=True)
class ToolContext:
    """Контекст, передаваемый инструменту при вызове.

    Attributes:
        user_id: идентификатор пользователя (пока всегда "default").
        settings: конфигурация проекта.
        state: текущее состояние витка (JarvisState) — для чтения
            retrieved_context, short_memory и т.п.
        extra: произвольные дополнительные данные (например, callback для TTS).
    """

    user_id: str = "default"
    settings: Optional[Settings] = None
    state: Optional[JarvisState] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)


@dataclass(slots=True)
class ActionResult:
    """Результат выполнения инструмента.

    Attributes:
        tool: имя инструмента.
        args: аргументы, с которыми был вызван.
        ok: True — успех, False — ошибка (ожидаемая, не исключение).
        output: полезная нагрузка (строка для пользователя / данные для LLM).
        error: текст ошибки, если ok=False.
        duration_sec: время выполнения в секундах.
        step_index: индекс шага в плане (если инструмент вызывается из плана).
    """

    tool: str
    args: Dict[str, Any]
    ok: bool
    output: Any = None
    error: Optional[str] = None
    duration_sec: float = 0.0
    step_index: Optional[int] = None
    terminated: bool = False
    side_effects_contained: bool = False
    execution_mode: str = "in_process"

    def __bool__(self) -> bool:
        return self.ok

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "args": self.args,
            "ok": self.ok,
            "output": self.output,
            "error": self.error,
            "duration_sec": self.duration_sec,
            "step_index": self.step_index,
            "terminated": self.terminated,
            "side_effects_contained": self.side_effects_contained,
            "execution_mode": self.execution_mode,
        }


class Tool(ABC):
    """Абстрактный базовый класс инструмента.

    Каждый инструмент должен реализовать:
    - ``name`` — уникальное имя (snake_case, например "open_app")
    - ``description`` — описание для LLM (function calling schema)
    - ``input_schema`` — JSON Schema аргументов
    - ``run`` — логика выполнения

    Пример:
        class MyTool(Tool):
            def name(self) -> str: return "my_tool"
            def description(self) -> str: return "Does something useful"
            def input_schema(self) -> dict: return {...}
            def run(self, args, context) -> ActionResult: ...
    """

    # Tools may opt into hard subprocess cancellation. Legacy in-process
    # tools remain API-compatible and receive cooperative cancellation only.
    supports_hard_cancellation: bool = False

    @property
    @abstractmethod
    def name(self) -> str:
        """Уникальное имя инструмента."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Описание для LLM (function calling)."""

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """JSON Schema аргументов (draft-07 compatible)."""

    @abstractmethod
    def run(self, args: Dict[str, Any], context: ToolContext) -> ActionResult:
        """Выполняет инструмент с заданными аргументами.

        Args:
            args: аргументы (уже валидированы по input_schema).
            context: контекст выполнения (settings, state, user_id).

        Returns:
            ActionResult — всегда возвращается, исключения не бросаются.
        """
