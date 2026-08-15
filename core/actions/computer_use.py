"""Computer-use слой (P1 §6 + NEXT) — ТОЛЬКО FAKE / DRY-RUN.

В автономном ночном режиме реальная мышь / клавиатура / скриншот
КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНЫ: любой реальный ввод — необратимый эффект на
машине пользователя в 3 ночи. Поэтому слой реализован исключительно как
dry-run:

    * инструменты ЗАПИСЫВАЮТ намерение в ``DryRunInputController``;
    * возвращают подтверждение симуляции;
    * НЕ импортируют и НЕ вызывают pyautogui / ctypes / SendInput /
      pynput / win32api. Реальный ввод физически невозможен — кода
      для него нет.

Реальный backend (если когда-либо понадобится) должен жить в ОТДЕЛЬНОМ
модуле и быть СТРОГО за выключенным по умолчанию флагом. Здесь его нет
намеренно: нельзя ошибочно включить то, чего не существует.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.actions.base import ActionResult, Tool, ToolContext
from core.actions.registry import DEFAULT_REGISTRY
from core.utils.logger import get_logger

__all__ = [
    "DryRunInputController",
    "ComputerMouseTool",
    "ComputerKeyboardTool",
    "ComputerScreenshotTool",
]

log = get_logger(__name__)


@dataclass
class DryRunInputController:
    """Накопитель зарегистрированных (но НЕ выполненных) намерений ввода."""

    actions: List[Dict[str, Any]] = field(default_factory=list)

    def record(self, kind: str, args: Dict[str, Any]) -> Dict[str, Any]:
        entry = {
            "kind": kind,
            "args": dict(args or {}),
            "ts": time.time(),
            "mode": "dry_run",
        }
        self.actions.append(entry)
        log.info("[dry-run] computer-use %s: %s", kind, args)
        return entry

    def clear(self) -> None:
        self.actions.clear()


#: Единый контроллер сессии (в памяти).
_CONTROLLER = DryRunInputController()


class ComputerMouseTool(Tool):
    """Computer-use (DRY-RUN): намерение движения/клика мыши.

    НЕ двигает реальную мышь — только регистрирует намерение.
    """

    @property
    def name(self) -> str:
        return "computer_mouse"

    @property
    def description(self) -> str:
        return (
            "Управление указателем мыши (DRY-RUN, симуляция). Регистрирует "
            "намерение движения/клика, НЕ выполняя реальных действий. "
            "Аргументы: action (move|click|double_click|right_click), "
            "x, y (координаты), button (left|right|middle)."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["move", "click", "double_click", "right_click"],
                    "description": "Тип действия мыши.",
                },
                "x": {"type": "integer", "description": "Координата X (экран)."},
                "y": {"type": "integer", "description": "Координата Y (экран)."},
                "button": {
                    "type": "string",
                    "enum": ["left", "right", "middle"],
                    "default": "left",
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        }

    def run(self, args: Dict[str, Any], context: ToolContext) -> ActionResult:
        _CONTROLLER.record(self.name, args)
        return ActionResult(
            tool=self.name,
            args=args,
            ok=True,
            output=(
                f"[dry-run] computer_mouse: зарегистрировано намерение {args} "
                f"— реальный ввод мыши НЕ выполнен."
            ),
        )


class ComputerKeyboardTool(Tool):
    """Computer-use (DRY-RUN): намерение ввода с клавиатуры.

    НЕ нажимает реальные клавиши — только регистрирует намерение.
    """

    @property
    def name(self) -> str:
        return "computer_keyboard"

    @property
    def description(self) -> str:
        return (
            "Ввод с клавиатуры (DRY-RUN, симуляция). Регистрирует намерение "
            "печати/нажатия клавиши, НЕ выполняя реальных действий. "
            "Аргументы: action (type|press), text (для type), key (для press)."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["type", "press"],
                    "description": "type — ввести текст; press — нажать клавишу.",
                },
                "text": {"type": "string", "description": "Текст для ввода (action=type)."},
                "key": {"type": "string", "description": "Имя клавиши (action=press), напр. enter."},
            },
            "required": ["action"],
            "additionalProperties": False,
        }

    def run(self, args: Dict[str, Any], context: ToolContext) -> ActionResult:
        _CONTROLLER.record(self.name, args)
        return ActionResult(
            tool=self.name,
            args=args,
            ok=True,
            output=(
                f"[dry-run] computer_keyboard: зарегистрировано намерение {args} "
                f"— реальный ввод с клавиатуры НЕ выполнен."
            ),
        )


class ComputerScreenshotTool(Tool):
    """Computer-use (DRY-RUN): намерение скриншота.

    НЕ делает реальный скриншот — только регистрирует намерение.
    """

    @property
    def name(self) -> str:
        return "computer_screenshot"

    @property
    def description(self) -> str:
        return (
            "Скриншот экрана (DRY-RUN, симуляция). Регистрирует намерение "
            "снимка, НЕ делая реального захвата. Аргумент: path (куда бы "
            "сохранили, опционально)."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Путь сохранения скриншота (опционально, не используется в dry-run).",
                },
            },
            "additionalProperties": False,
        }

    def run(self, args: Dict[str, Any], context: ToolContext) -> ActionResult:
        _CONTROLLER.record(self.name, args)
        return ActionResult(
            tool=self.name,
            args=args,
            ok=True,
            output=(
                f"[dry-run] computer_screenshot: зарегистрировано намерение {args} "
                f"— реальный скриншот НЕ сделан."
            ),
        )


# Авто-регистрация (dry-run инструменты появляются в retrieval агента,
# но выполняются только как симуляция).
DEFAULT_REGISTRY.register(ComputerMouseTool())
DEFAULT_REGISTRY.register(ComputerKeyboardTool())
DEFAULT_REGISTRY.register(ComputerScreenshotTool())
