"""Configurable, cooldown-aware system trigger engine (no OS dependency required)."""
from __future__ import annotations
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, Optional

@dataclass(frozen=True)
class TriggerDefinition:
    id: str
    enabled: bool = False
    condition: Dict[str, Any] = field(default_factory=dict)
    cooldown_hours: float = 2
    max_ignores: int = 3
    messages: tuple[str, ...] = ()

@dataclass
class TriggerContext:
    active_window: str = ""
    active_processes: set[str] = field(default_factory=set)
    idle_minutes: float = 0
    returned_from_afk: bool = False
    now: datetime = field(default_factory=datetime.now)
    durations: Dict[str, float] = field(default_factory=dict)

class SystemTriggerEngine:
    def __init__(self, triggers: Iterable[TriggerDefinition | Dict[str, Any]] = (), *, emit: Optional[Callable[[str, str], None]] = None, clock: Callable[[], float] = time.time) -> None:
        self.triggers = [self._coerce(t) for t in triggers]
        self.emit = emit or (lambda _event, _text: None)
        self.clock = clock
        self._last: Dict[str, float] = {}
        self._ignores: Dict[str, int] = {}

    @staticmethod
    def _coerce(value: TriggerDefinition | Dict[str, Any]) -> TriggerDefinition:
        if isinstance(value, TriggerDefinition): return value
        return TriggerDefinition(id=str(value["id"]), enabled=bool(value.get("enabled", False)), condition=dict(value.get("condition", {})), cooldown_hours=float(value.get("cooldown_hours", 2)), max_ignores=int(value.get("max_ignores", 3)), messages=tuple(value.get("messages", ())))

    def should_fire(self, trigger: TriggerDefinition, context: TriggerContext) -> bool:
        if not trigger.enabled or self._ignores.get(trigger.id, 0) >= trigger.max_ignores: return False
        last = self._last.get(trigger.id)
        if last is not None and self.clock() - last < trigger.cooldown_hours * 3600: return False
        c = trigger.condition
        if "active_window_contains" in c and c["active_window_contains"].lower() not in context.active_window.lower(): return False
        if "active_process" in c and not (set(c["active_process"]) & context.active_processes): return False
        if context.idle_minutes < float(c.get("afk_duration_minutes", 0)): return False
        if c.get("user_returned") and not context.returned_from_afk: return False
        if "time_after" in c and context.now.strftime("%H:%M") < str(c["time_after"]): return False
        for key, minutes in (("duration_minutes", c.get("duration_minutes")),):
            if minutes is not None and context.durations.get(trigger.id, 0) < float(minutes): return False
        return True

    def check(self, context: TriggerContext) -> list[str]:
        fired = []
        for trigger in self.triggers:
            if self.should_fire(trigger, context):
                text = random.choice(trigger.messages) if trigger.messages else ""
                self._last[trigger.id] = self.clock()
                fired.append(trigger.id)
                if text: self.emit("system_initiated", text)
        return fired

    def record_ignored(self, trigger_id: str) -> None: self._ignores[trigger_id] = self._ignores.get(trigger_id, 0) + 1
    def record_response(self, trigger_id: str) -> None: self._ignores[trigger_id] = 0
