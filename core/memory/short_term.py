"""Кратковременная память диалога (только в оперативной памяти).

Простой кольцевой буфер последних сообщений. Никакой персистентности:
при перезапуске приложения память пуста. Долгосрочное хранение —
ответственность :class:`core.memory.long_term.LongTermMemory`.

Используется оркестратором (Часть 5) для передачи истории в LLM и
синхронизации с ``JarvisState["short_memory"]``.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Optional

from core.state import JarvisState, Message, Role
from core.utils.logger import get_logger

__all__ = ["SessionManager"]

log = get_logger(__name__)


class SessionManager:
    """Кольцевой буфер сообщений диалога в ОЗУ."""

    def __init__(self, max_size: int = 20) -> None:
        """
        Args:
            max_size: максимальное число хранимых сообщений. При превышении
                самые старые вытесняются. Значение <= 0 трактуется как безлимит.
        """
        if max_size < 0:
            max_size = 0
        self._max_size = max_size
        self._buffer: deque[Message] = deque(maxlen=max_size if max_size > 0 else None)

    # ------------------------------------------------------------------ #
    #  Запись
    # ------------------------------------------------------------------ #

    def push(self, role: str, content: str) -> None:
        """Добавляет сообщение в краткую память.

        Args:
            role: одна из ролей ``system``/``user``/``assistant``/``tool``.
            content: текст сообщения.
        """
        if not content:
            log.debug("Пропуск пустого сообщения роли '%s'", role)
            return
        message: Message = {
            "role": role if role in ("system", "user", "assistant", "tool") else "user",
            "content": content,
        }
        self._buffer.append(message)

    # ------------------------------------------------------------------ #
    #  Чтение
    # ------------------------------------------------------------------ #

    def get_recent(self, n: Optional[int] = None) -> List[Message]:
        """Возвращает последние ``n`` сообщений (или все, если ``n=None``).

        Возвращается копия, чтобы внешний код не мутировал внутренний буфер.
        """
        items = list(self._buffer)
        if n is None or n <= 0:
            return items
        return items[-n:]

    # ------------------------------------------------------------------ #
    #  Управление
    # ------------------------------------------------------------------ #

    def clear(self) -> None:
        """Полностью очищает краткую память."""
        self._buffer.clear()

    @property
    def size(self) -> int:
        """Текущее число сообщений в буфере."""
        return len(self._buffer)

    def to_state(self, state: JarvisState) -> None:
        """Записывает копию краткой памяти в поле состояния ``short_memory``.

        Args:
            state: состояние витка (мутируется на месте).
        """
        state["short_memory"] = self.get_recent()

    def __repr__(self) -> str:
        return f"<SessionManager size={self.size} max={self._max_size}>"
