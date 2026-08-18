"""Command OS: canonical primitives instead of a second command catalogue."""

from __future__ import annotations

import re
from typing import Any, Iterable, Optional

from .models import ActionMode, CommandPlan, CommandPrimitive, CommandStep


class CommandOS:
    PRIMITIVES = tuple(CommandPrimitive)
    _ALIASES = {
        "наблюдай": CommandPrimitive.OBSERVE, "найди": CommandPrimitive.FIND,
        "сравни": CommandPrimitive.COMPARE, "спланируй": CommandPrimitive.PLAN,
        "подготовь": CommandPrimitive.PREPARE, "сделай": CommandPrimitive.EXECUTE,
        "проверь": CommandPrimitive.VERIFY, "исправь": CommandPrimitive.REPAIR,
        "отмени": CommandPrimitive.ROLLBACK, "продолжи": CommandPrimitive.RESUME,
        "кратко": CommandPrimitive.BRIEF,
    }

    @classmethod
    def mode_for(cls, goal: str, *, complexity: Optional[float] = None,
                 risk: str = "low") -> ActionMode:
        text = (goal or "").casefold()
        if any(word in text for word in ("отмени", "верни", "откат", "undo")):
            return ActionMode.ROLLBACK
        if any(word in text for word in ("подготовь", "черновик", "заранее", "не отправляй")):
            return ActionMode.PREPARE
        if any(word in text for word in ("наблюдай", "следи", "монитор")):
            return ActionMode.MONITOR
        if risk.casefold() in {"high", "critical"} or (complexity or 0) >= 0.6:
            return ActionMode.DELIBERATE
        return ActionMode.REFLEX

    @classmethod
    def compile(cls, goal: str, *, intent: str = "none", tool: Optional[str] = None,
                args: Optional[dict[str, Any]] = None, desired_state: Optional[dict[str, Any]] = None,
                constraints: Optional[Iterable[str]] = None, risk: str = "low",
                complexity: Optional[float] = None) -> CommandPlan:
        goal = " ".join((goal or "").split())
        mode = cls.mode_for(goal, complexity=complexity, risk=risk)
        expected = dict(desired_state or {})
        steps = [CommandStep(CommandPrimitive.OBSERVE, "получить текущее состояние")]
        if tool:
            steps.extend([
                CommandStep(CommandPrimitive.FIND, f"разрешить capability {tool}", tool=tool, args=dict(args or {})),
                CommandStep(CommandPrimitive.PLAN, "проверить preconditions"),
                CommandStep(CommandPrimitive.PREPARE, "сформировать безопасный вызов"),
                CommandStep(CommandPrimitive.EXECUTE, f"вызвать {tool}", tool=tool, args=dict(args or {}),
                            expected_state=expected, reversible=mode != ActionMode.ROLLBACK),
                CommandStep(CommandPrimitive.OBSERVE, "снять фактическое состояние после действия"),
                CommandStep(CommandPrimitive.VERIFY, "сопоставить desired state с observed state",
                            expected_state=expected),
            ])
        else:
            steps.append(CommandStep(CommandPrimitive.BRIEF, "сформировать ответ без побочного действия"))
        if mode == ActionMode.ROLLBACK:
            steps.insert(1, CommandStep(CommandPrimitive.ROLLBACK, "подготовить semantic undo"))
        return CommandPlan(goal=goal, steps=steps, mode=mode, desired_state=expected,
                           constraints=list(constraints or []))

    @classmethod
    def explain(cls, plan: CommandPlan) -> str:
        return " → ".join(step.primitive.value for step in plan.steps)

    @classmethod
    def normalize_primitive(cls, value: str) -> CommandPrimitive:
        raw = " ".join((value or "").split()).casefold()
        if raw in cls._ALIASES:
            return cls._ALIASES[raw]
        return CommandPrimitive(raw.upper())

