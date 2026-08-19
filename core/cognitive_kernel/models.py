"""Serializable contracts used by the canonical JARVIS mission loop."""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _safe(value: Any, limit: int = 800) -> str:
    text = " ".join(str(value or "").split())[:limit]
    # Keep credentials and bearer material out of the local mission ledger.
    text = re.sub(r"(?i)(bearer\s+|api[_-]?key\s*[:=]\s*|token\s*[:=]\s*|password\s*[:=]\s*)[^\s,;]+", r"\1[REDACTED]", text)
    return text


def _safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not value:
        return {}
    result: dict[str, Any] = {}
    for key, item in value.items():
        name = _safe(key, 80)
        sensitive = bool(re.search(r"(?i)(?:api[_-]?key|token|password|secret|credential)", name))
        if isinstance(item, Mapping):
            result[name] = "[REDACTED]" if sensitive else _safe_mapping(item)
        elif isinstance(item, (list, tuple)):
            result[name] = "[REDACTED]" if sensitive else [_safe(v, 300) if not isinstance(v, Mapping) else _safe_mapping(v) for v in item[:50]]
        elif isinstance(item, (str, int, float, bool)) or item is None:
            result[name] = "[REDACTED]" if sensitive else (_safe(item, 500) if isinstance(item, str) else item)
        else:
            result[name] = "[REDACTED]" if sensitive else _safe(item, 500)
    return result


@dataclass
class TaskContractV2:
    intent_family: str = "conversation"
    subject: str = ""
    desired_outcome: str = ""
    inputs: list[dict[str, Any]] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    risk: str = "low"
    mode: str = "conversation"
    confidence: float = 0.0
    evidence: list[dict[str, Any]] = field(default_factory=list)
    id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex}")
    created_at: str = field(default_factory=utcnow)

    @property
    def contract_id(self) -> str:
        """Compatibility alias used by the pre-kernel intake contract."""
        return self.id

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["subject"] = _safe(self.subject)
        value["desired_outcome"] = _safe(self.desired_outcome, 2000)
        value["constraints"] = [_safe(item, 300) for item in self.constraints[:50]]
        value["inputs"] = [_safe_mapping(item) for item in self.inputs[:50]]
        value["evidence"] = [_safe_mapping(item) for item in self.evidence[:50]]
        value["confidence"] = round(max(0.0, min(1.0, float(self.confidence))), 4)
        return value


@dataclass
class EvidenceRecordV2:
    claim: str
    source: str
    observed_at: str = field(default_factory=utcnow)
    confidence: float = 0.0
    expected_state: dict[str, Any] = field(default_factory=dict)
    observed_state: dict[str, Any] = field(default_factory=dict)
    freshness: str = "fresh"
    latency_ms: float = 0.0
    path: str = "fast"
    state_hash: str = ""
    id: str = field(default_factory=lambda: f"evidence-{uuid.uuid4().hex}")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["claim"] = _safe(self.claim, 1200)
        value["source"] = _safe(self.source, 300)
        value["expected_state"] = _safe_mapping(self.expected_state)
        value["observed_state"] = _safe_mapping(self.observed_state)
        value["confidence"] = round(max(0.0, min(1.0, float(self.confidence))), 4)
        value["latency_ms"] = round(max(0.0, float(self.latency_ms)), 3)
        return value


@dataclass
class MissionRecord:
    id: str
    task_id: str
    # The intake contract is persisted with the mission so a restart can
    # resume the exact intent instead of classifying the text a second time.
    contract: dict[str, Any] = field(default_factory=dict)
    status: str = "queued"
    desired_state: dict[str, Any] = field(default_factory=dict)
    observed_state: dict[str, Any] = field(default_factory=dict)
    checkpoints: list[dict[str, Any]] = field(default_factory=list)
    next_action: str = ""
    rollback_plan: dict[str, Any] = field(default_factory=dict)
    evidence_ids: list[str] = field(default_factory=list)
    attempts: int = 0
    error: str = ""
    created_at: str = field(default_factory=utcnow)
    updated_at: str = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["desired_state"] = _safe_mapping(self.desired_state)
        value["observed_state"] = _safe_mapping(self.observed_state)
        value["contract"] = _safe_mapping(self.contract)
        value["checkpoints"] = [_safe_mapping(item) for item in self.checkpoints[-100:]]
        value["rollback_plan"] = _safe_mapping(self.rollback_plan)
        value["next_action"] = _safe(self.next_action, 500)
        value["error"] = _safe(self.error, 1000)
        return value


@dataclass(frozen=True)
class MissionHandle:
    id: str
    task_id: str
    intent_family: str
    status: str = "queued"


@dataclass
class VerificationOutcome:
    success: bool
    verified_fields: dict[str, Any] = field(default_factory=dict)
    mismatches: dict[str, Any] = field(default_factory=dict)
    repair_attempts: int = 0
    rollback_available: bool = False
    evidence_ids: list[str] = field(default_factory=list)
    action_taken: bool = False
    blocked_reason: str | None = None
    mission_id: str = ""

    @property
    def verified(self) -> bool:
        return bool(self.success)

    @property
    def ok(self) -> bool:
        """Additive compatibility alias; success still means verified state."""
        return bool(self.success)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["verified_fields"] = _safe_mapping(self.verified_fields)
        value["mismatches"] = _safe_mapping(self.mismatches)
        return value


@dataclass(frozen=True)
class CancellationResult:
    mission_id: str
    cancelled: bool
    stopped_before_mutation: bool = True
    reason: str = ""


@dataclass(frozen=True)
class DecisionTrace:
    mission_id: str
    selected_capability: str = ""
    path: str = "fast"
    confidence: float = 0.0
    reasons: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()


@dataclass
class RuntimeProfile:
    backend: str = "unknown"
    model_family: str = "local"
    n_gpu_layers: int = 0
    n_ctx: int = 4096
    n_batch: int = 256
    warmup_ms: float = 0.0
    ready_before_first_request: bool = False
    rss_mb: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


__all__ = [
    "CancellationResult", "DecisionTrace", "EvidenceRecordV2", "MissionHandle",
    "MissionRecord", "RuntimeProfile", "TaskContractV2", "VerificationOutcome",
]
