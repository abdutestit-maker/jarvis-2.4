"""Deterministic local clock tool.  No model and no network are involved."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from core.actions.base import ActionResult, Tool, ToolContext
from core.actions.registry import DEFAULT_REGISTRY

__all__ = ["CurrentTimeTool", "current_time"]


def current_time() -> Dict[str, str]:
    now = datetime.now().astimezone()
    return {
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "timezone": now.tzname() or "local",
        "iso": now.isoformat(timespec="seconds"),
    }


class CurrentTimeTool(Tool):
    @property
    def name(self) -> str:
        return "current_time"

    @property
    def description(self) -> str:
        return "Показывает текущее локальное время, дату и часовой пояс без обращения к сети."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}, "additionalProperties": False}

    def run(self, args: Dict[str, Any], context: ToolContext) -> ActionResult:
        value = current_time()
        return ActionResult(tool=self.name, args=args, ok=True,
                            output=f"Сейчас {value['time']} ({value['timezone']}), {value['date']}.",
                            side_effects_contained=True)


DEFAULT_REGISTRY.register(CurrentTimeTool())

