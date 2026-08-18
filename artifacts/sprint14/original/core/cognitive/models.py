"""Typed, inspectable state for the ATLAS cognitive coordinator.

The structures in this module contain continuity facts and references only.
They deliberately have no field for hidden reasoning or model scratch space.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CurrentMindState:
    current_goal: str = ""
    active_task: str = ""
    subgoals: list[str] = field(default_factory=list)
    relevant_context_refs: list[str] = field(default_factory=list)
    recalled_memory_refs: list[str] = field(default_factory=list)
    current_app: str = ""
    mission_state: str = "idle"
    attention_state: str = "available"
    uncertainties: list[str] = field(default_factory=list)
    pending_verification: list[str] = field(default_factory=list)
    interaction_mode: str = "conversation"
    confidence: float = 0.0
    last_verified_result: str = ""
    pending_user_question: str = ""
    active_mission_id: str = ""
    updated_at: str = field(default_factory=utcnow)

    def to_safe_dict(self) -> dict[str, Any]:
        """Return the explicit public state contract (never private reasoning)."""
        from core.memory.secret_filter import sanitize_for_memory

        def clean(value: Any) -> Any:
            if isinstance(value, str):
                return sanitize_for_memory(value)
            if isinstance(value, list):
                return [clean(item) for item in value]
            if isinstance(value, dict):
                return {str(key): clean(item) for key, item in value.items()}
            return value

        return clean(asdict(self))


@dataclass
class GoalFrame:
    goal_id: str
    goal: str
    active_task: str = ""
    status: str = "suspended"
    context_refs: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=utcnow)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GoalFrame":
        allowed = {name for name in cls.__dataclass_fields__}
        return cls(**{key: value for key, value in payload.items() if key in allowed})


@dataclass(frozen=True)
class ContinuationResolution:
    action: str = "none"
    goal: str = ""
    goal_id: str = ""
    question: str = ""
    confidence: float = 0.0
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class CognitiveEpisode:
    goal: str
    result: str
    verified_at: str = field(default_factory=utcnow)
    evidence: tuple[str, ...] = ()


__all__ = [
    "CognitiveEpisode", "ContinuationResolution", "CurrentMindState",
    "GoalFrame", "utcnow",
]
