"""Менеджер напоминаний (reminders) на threading.Timer.

Инструмент:
- ``AddReminderTool`` — добавляет напоминание через N минут.
- ``TaskManager`` — управляет таймерами, вызывает callback при срабатывании.

При срабатывании таймера вызывается callback-функция
(оркестратор Части 5 подключит сюда notifications.py).
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from config.settings import Settings
from core.actions.base import ActionResult, Tool, ToolContext
from core.actions.registry import DEFAULT_REGISTRY
from core.utils.logger import get_logger

__all__ = ["TaskManager", "AddReminderTool", "ListRemindersTool", "CancelReminderTool"]

log = get_logger(__name__)


@dataclass(slots=True)
class Reminder:
    """Напоминание с таймером."""

    id: str
    text: str
    due_at: float  # unix timestamp
    timer: threading.Timer
    created_at: float = field(default_factory=time.time)


class TaskManager:
    """Менеджер напоминаний на основе threading.Timer.

    Не персистентен — при перезапуске приложения напоминания теряются.
    Для персистентности нужно хранить в БД (будущая доработка).

    Args:
        callback: функция, вызываемая при срабатывании напоминания.
            Сигнатура: callback(reminder_id: str, text: str) -> None.
    """

    def __init__(self, callback: Optional[Callable[[str, str], None]] = None) -> None:
        self._reminders: Dict[str, Reminder] = {}
        self._lock = threading.RLock()
        self._callback = callback

    def add_reminder_in_minutes(self, text: str, minutes: int) -> str:
        """Добавляет напоминание.

        Args:
            text: текст напоминания.
            minutes: через сколько минут сработать (>= 1).

        Returns:
            ID напоминания (uuid).
        """
        if not text or not text.strip():
            raise ValueError("Текст напоминания не может быть пустым")
        if minutes < 1:
            raise ValueError("Минимум 1 минута")

        reminder_id = uuid.uuid4().hex[:8]
        due_at = time.time() + minutes * 60

        def _fire() -> None:
            with self._lock:
                rem = self._reminders.pop(reminder_id, None)
            if rem and self._callback:
                try:
                    self._callback(rem.id, rem.text)
                except Exception as exc:
                    log.error("Ошибка в callback напоминания %s: %s", reminder_id, exc)

        timer = threading.Timer(minutes * 60, _fire)
        timer.daemon = True
        timer.start()

        reminder = Reminder(id=reminder_id, text=text.strip(), due_at=due_at, timer=timer)
        with self._lock:
            self._reminders[reminder_id] = reminder

        log.info("Добавлено напоминание #%s через %d мин: %s", reminder_id, minutes, text[:50])
        return reminder_id

    def list_reminders(self) -> List[Dict[str, Any]]:
        """Возвращает список активных напоминаний."""
        with self._lock:
            now = time.time()
            result = []
            for rem in self._reminders.values():
                remaining = max(0, int(rem.due_at - now))
                result.append(
                    {
                        "id": rem.id,
                        "text": rem.text,
                        "due_at": rem.due_at,
                        "remaining_sec": remaining,
                        "created_at": rem.created_at,
                    }
                )
            return sorted(result, key=lambda x: x["due_at"])

    def cancel_reminder(self, reminder_id: str) -> bool:
        """Отменяет напоминание по ID.

        Returns:
            True — было отменено, False — не найдено.
        """
        with self._lock:
            rem = self._reminders.pop(reminder_id, None)
        if rem:
            rem.timer.cancel()
            log.info("Отменено напоминание #%s", reminder_id)
            return True
        return False

    def clear_all(self) -> int:
        """Отменяет все напоминания. Возвращает число отменённых."""
        with self._lock:
            count = len(self._reminders)
            for rem in self._reminders.values():
                rem.timer.cancel()
            self._reminders.clear()
        return count

    def shutdown(self) -> None:
        """Корректно останавливает все таймеры (при выходе приложения)."""
        self.clear_all()


# Глобальный экземпляр для удобства (оркестратор может использовать свой)
_DEFAULT_MANAGER: Optional[TaskManager] = None


def get_default_manager() -> TaskManager:
    """Возвращает глобальный TaskManager (лениво создаёт)."""
    global _DEFAULT_MANAGER
    if _DEFAULT_MANAGER is None:
        _DEFAULT_MANAGER = TaskManager()
    return _DEFAULT_MANAGER


# --------------------------------------------------------------------------- #
# Tool-обёртки
# --------------------------------------------------------------------------- #


class AddReminderTool(Tool):
    """Инструмент: добавить напоминание."""

    @property
    def name(self) -> str:
        return "add_reminder"

    @property
    def description(self) -> str:
        return (
            "Создаёт напоминание, которое сработает через указанное число минут. "
            "При срабатывании вызывает callback (подключается оркестратором). "
            "Не персистентно — при перезапуске теряется."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Текст напоминания (что напомнить).",
                },
                "minutes": {
                    "type": "integer",
                    "description": "Через сколько минут сработать (минимум 1).",
                    "minimum": 1,
                    "maximum": 10080,  # неделя
                },
            },
            "required": ["text", "minutes"],
            "additionalProperties": False,
        }

    def run(self, args: Dict[str, Any], context: ToolContext) -> ActionResult:
        text = args["text"]
        minutes = args["minutes"]

        manager = get_default_manager()
        # Если у контекста есть callback — используем его (оркестратор прокидывает)
        callback = context.extra.get("reminder_callback") if context.extra else None
        if callback and manager._callback is None:
            manager._callback = callback

        try:
            reminder_id = manager.add_reminder_in_minutes(text, minutes)
            return ActionResult(
                tool=self.name,
                args=args,
                ok=True,
                output=f"Напоминание создано (ID: {reminder_id}): через {minutes} мин — «{text}»",
            )
        except Exception as exc:
            return ActionResult(
                tool=self.name,
                args=args,
                ok=False,
                error=str(exc),
            )


class ListRemindersTool(Tool):
    """Инструмент: список активных напоминаний."""

    @property
    def name(self) -> str:
        return "list_reminders"

    @property
    def description(self) -> str:
        return "Возвращает список всех активных напоминаний с оставшимся временем."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}, "additionalProperties": False}

    def run(self, args: Dict[str, Any], context: ToolContext) -> ActionResult:
        manager = get_default_manager()
        reminders = manager.list_reminders()

        if not reminders:
            return ActionResult(
                tool=self.name,
                args=args,
                ok=True,
                output="Активных напоминаний нет.",
            )

        lines = ["Активные напоминания:"]
        for r in reminders:
            mins = r["remaining_sec"] // 60
            secs = r["remaining_sec"] % 60
            lines.append(f"  #{r['id']} — {r['text']} (через {mins} мин {secs} сек)")
        return ActionResult(
            tool=self.name,
            args=args,
            ok=True,
            output="\n".join(lines),
        )


class CancelReminderTool(Tool):
    """Инструмент: отменить напоминание по ID."""

    @property
    def name(self) -> str:
        return "cancel_reminder"

    @property
    def description(self) -> str:
        return "Отменяет активное напоминание по его ID."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "reminder_id": {
                    "type": "string",
                    "description": "ID напоминания (возвращается при создании).",
                },
            },
            "required": ["reminder_id"],
            "additionalProperties": False,
        }

    def run(self, args: Dict[str, Any], context: ToolContext) -> ActionResult:
        reminder_id = args["reminder_id"]
        manager = get_default_manager()

        if manager.cancel_reminder(reminder_id):
            return ActionResult(
                tool=self.name,
                args=args,
                ok=True,
                output=f"Напоминание #{reminder_id} отменено.",
            )
        else:
            return ActionResult(
                tool=self.name,
                args=args,
                ok=False,
                error=f"Напоминание #{reminder_id} не найдено.",
            )


# Авто-регистрация
DEFAULT_REGISTRY.register(AddReminderTool())
DEFAULT_REGISTRY.register(ListRemindersTool())
DEFAULT_REGISTRY.register(CancelReminderTool())