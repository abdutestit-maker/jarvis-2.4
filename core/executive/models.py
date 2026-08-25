"""Small serialisable records used by Executive Mind."""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return value


class _StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class FactType(_StrEnum):
    """Epistemic origin of a world fact; current state is never memory."""

    OBSERVED = "observed"
    REMEMBERED = "remembered"
    INFERRED = "inferred"
    USER_REPORTED = "user_reported"


class GoalStatus(_StrEnum):
    OPEN = "open"
    ACTIVE = "active"
    BLOCKED = "blocked"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CommitmentType(_StrEnum):
    IDEA = "idea"
    INTENTION = "intention"
    PROMISE = "promise"
    DEADLINE = "deadline"
    EXPECTATION = "expectation"


class CommitmentStatus(_StrEnum):
    OPEN = "open"
    COMPLETED = "completed"
    SUPERSEDED = "superseded"
    DISMISSED = "dismissed"


class ActionMode(_StrEnum):
    REFLEX = "reflex"
    DELIBERATE = "deliberate"
    PREPARE = "prepare"
    MONITOR = "monitor"
    ROLLBACK = "rollback"


class CommandPrimitive(_StrEnum):
    OBSERVE = "OBSERVE"
    FIND = "FIND"
    COMPARE = "COMPARE"
    PLAN = "PLAN"
    SIMULATE = "SIMULATE"
    PREPARE = "PREPARE"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    REPAIR = "REPAIR"
    ROLLBACK = "ROLLBACK"
    MONITOR = "MONITOR"
    RESUME = "RESUME"
    BRIEF = "BRIEF"


@dataclass
class GoalNode:
    title: str
    id: str = field(default_factory=lambda: _new_id("goal"))
    status: GoalStatus = GoalStatus.OPEN
    parent_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    desired_state: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    next_action: str = ""
    deadline: Optional[str] = None
    source: str = "user"
    confidence: float = 0.6
    priority: float = 0.5
    last_verified: Optional[str] = None
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable(asdict(self))

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "GoalNode":
        data = dict(raw)
        data["status"] = GoalStatus(data.get("status", GoalStatus.OPEN))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Commitment:
    text: str
    kind: CommitmentType = CommitmentType.INTENTION
    id: str = field(default_factory=lambda: _new_id("commit"))
    status: CommitmentStatus = CommitmentStatus.OPEN
    due_at: Optional[str] = None
    source: str = "user"
    confidence: float = 0.6
    importance: float = 0.5
    owner: str = "user"
    next_action: str = ""
    last_checked: Optional[str] = None
    created_at: str = field(default_factory=now_iso)
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable(asdict(self))

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Commitment":
        data = dict(raw)
        data["kind"] = CommitmentType(data.get("kind", CommitmentType.INTENTION))
        data["status"] = CommitmentStatus(data.get("status", CommitmentStatus.OPEN))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class WorldFact:
    key: str
    value: Any
    source: str
    observed_at: str = field(default_factory=now_iso)
    valid_until: Optional[str] = None
    confidence: float = 0.7
    volatility: str = "normal"
    supersedes: Optional[str] = None
    domain: str = "general"
    fact_type: str = FactType.INFERRED.value
    ttl_seconds: Optional[float] = None
    evidence: List[str] = field(default_factory=list)
    error: Optional[str] = None
    ephemeral: bool = False

    def to_dict(self) -> Dict[str, Any]:
        payload = _jsonable(asdict(self))
        payload["freshness"] = self.freshness()
        return payload

    def freshness(self, now: Optional[datetime] = None) -> str:
        if not self.valid_until:
            return "timeless"
        moment = now or datetime.now(timezone.utc)
        try:
            deadline = datetime.fromisoformat(self.valid_until)
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return "unknown"
        return "fresh" if deadline > moment else "stale"

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "WorldFact":
        return cls(**{k: v for k, v in dict(raw).items() if k in cls.__dataclass_fields__})


@dataclass
class IntentContract:
    raw: str
    intent: str = "none"
    goal: str = ""
    constraints: List[str] = field(default_factory=list)
    mode: ActionMode = ActionMode.REFLEX
    confidence: float = 0.5
    source: str = "user"
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class CommandStep:
    primitive: CommandPrimitive
    description: str = ""
    tool: Optional[str] = None
    args: Dict[str, Any] = field(default_factory=dict)
    expected_state: Dict[str, Any] = field(default_factory=dict)
    reversible: bool = True
    requires_confirmation: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class CommandPlan:
    goal: str
    steps: List[CommandStep] = field(default_factory=list)
    mode: ActionMode = ActionMode.REFLEX
    desired_state: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    plan_id: str = field(default_factory=lambda: _new_id("plan"))

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class CapabilitySpec:
    name: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    risk: str = "medium"
    cost: str = "free"
    reliability: float = 0.5
    latency_sec: Optional[float] = None
    tools: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class RehearsalReport:
    ready: bool
    plan_id: str = ""
    blockers: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    simulated_steps: List[str] = field(default_factory=list)
    rollback_ready: bool = True
    side_effects: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class UndoRecord:
    action_id: str
    before: Dict[str, Any]
    after: Dict[str, Any]
    inverse: Dict[str, Any] = field(default_factory=dict)
    verified: bool = False
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class DemoStep:
    action: str
    target: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    observed_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class LearnedWorkflow:
    name: str
    steps: List[DemoStep] = field(default_factory=list)
    parameters: List[str] = field(default_factory=list)
    confidence: float = 0.5
    scope: str = "local"
    id: str = field(default_factory=lambda: _new_id("workflow"))
    created_at: str = field(default_factory=now_iso)
    last_verified: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class EvalCase:
    name: str
    goal: str
    expected_state: Dict[str, Any] = field(default_factory=dict)
    last_result: str = ""
    verified: bool = False
    repair_count: int = 0
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable(asdict(self))


def normalize_tokens(text: str) -> set[str]:
    return set(re.findall(r"[\w-]{2,}", (text or "").casefold(), flags=re.UNICODE))
