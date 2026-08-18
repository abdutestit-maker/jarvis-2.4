"""Structured, privacy-minimal models for Sprint 11 living intelligence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ContextObservation:
    observed_at: datetime = field(default_factory=utcnow)
    source: str = "local"
    application: str = ""
    process: str = ""
    window_title: str = ""
    domain: str = ""
    page_title: str = ""
    action: str = ""
    target: str = ""
    outcome: str = "unknown"
    error_signature: str = ""
    user_language: str = ""
    idle_seconds: float = 0.0
    fullscreen: bool = False
    media_active: bool = False
    meeting_active: bool = False
    typing_active: bool = False
    do_not_disturb: bool = False
    active_mission: bool = False
    clipboard_metadata: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["observed_at"] = self.observed_at.isoformat()
        return value


@dataclass
class CurrentContext:
    active_application: str = ""
    active_process: str = ""
    window_title: str = ""
    browser_domain: str = ""
    page_title: str = ""
    session_duration: float = 0.0
    current_project: str = ""
    probable_activity: str = ""
    goal: str = ""
    goal_confidence: float = 0.0
    recent_actions: list[str] = field(default_factory=list)
    repetition_score: float = 0.0
    friction_score: float = 0.0
    user_busy: bool = False
    jarvis_should_interrupt: bool = False
    evidence: list[str] = field(default_factory=list)
    updated_at: str = ""


@dataclass
class ActivityEpisode:
    episode_id: str
    start: datetime
    end: datetime | None = None
    applications: list[str] = field(default_factory=list)
    high_level_actions: list[str] = field(default_factory=list)
    goal_hypothesis: str = ""
    goal_confidence: float = 0.0
    problems: list[str] = field(default_factory=list)
    jarvis_interventions: list[str] = field(default_factory=list)
    outcome: str = "active"
    project: str = ""
    evidence_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["start"] = self.start.isoformat()
        value["end"] = self.end.isoformat() if self.end else None
        return value


@dataclass(frozen=True)
class GoalHypothesis:
    goal: str
    confidence: float
    evidence: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()


@dataclass(frozen=True)
class FrictionSignal:
    type: str
    confidence: float
    context: str
    possible_help: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReturnContext:
    message: str
    confidence: float
    evidence: tuple[str, ...]
    episode_id: str


class AutonomyLevel(str, Enum):
    OBSERVER = "observer"
    ASSISTANT = "assistant"
    PARTNER = "partner"
    AUTONOMOUS = "autonomous"


class ComputerAssistanceLevel(str, Enum):
    BEGINNER = "beginner"
    NORMAL = "normal"
    ADVANCED = "advanced"
    DEVELOPER = "developer"


class ProactiveAction(str, Enum):
    SILENT = "SILENT"
    PREPARE = "PREPARE"
    SUGGEST = "SUGGEST"
    ACT = "ACT"
    ASK = "ASK"
    WARN = "WARN"


class InterruptionLevel(str, Enum):
    NONE = "NONE"
    PASSIVE = "PASSIVE"
    NORMAL = "NORMAL"
    IMPORTANT = "IMPORTANT"
    URGENT = "URGENT"


__all__ = [
    "ActivityEpisode", "AutonomyLevel", "ComputerAssistanceLevel",
    "ContextObservation", "CurrentContext", "FrictionSignal", "GoalHypothesis",
    "InterruptionLevel", "ProactiveAction", "ReturnContext", "utcnow",
]
