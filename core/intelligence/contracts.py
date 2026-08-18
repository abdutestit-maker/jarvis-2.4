"""Typed contracts shared by intake, operator, tutor and verification paths."""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from statistics import median
from typing import Any, Iterable, Mapping


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _clean(value: Any, limit: int = 400) -> str:
    return " ".join(str(value or "").split())[:limit]


@dataclass
class TaskContract:
    """A normalized user goal.  It is safe to serialize into mission state."""

    intent_family: str = "conversation"
    subject: str = ""
    desired_outcome: str = ""
    inputs: list[dict[str, Any]] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    ambiguities: list[str] = field(default_factory=list)
    risk: str = "low"
    mode: str = "conversation"
    confidence: float = 0.0
    contract_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TaskContract":
        allowed = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{key: value[key] for key in allowed if key in value})


@dataclass
class EvidenceRecord:
    """Evidence for a claim or action, never a claim of success by itself."""

    claim: str
    source: str
    observed_at: str = field(default_factory=_now)
    confidence: float = 0.0
    expected_state: dict[str, Any] = field(default_factory=dict)
    observed_state: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    freshness: str = "fresh"
    path: str = "fast"
    evidence_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["confidence"] = round(float(self.confidence), 4)
        value["latency_ms"] = round(float(self.latency_ms), 3)
        return value


@dataclass(frozen=True)
class LatencyBudget:
    """Numerical gate for a user-visible execution path."""

    path: str
    p50_ms: float
    p95_ms: float
    hard_max_ms: float
    first_progress_p95_ms: float | None = None

    def check(self, values_ms: Iterable[float], *, first_progress_ms: Iterable[float] | None = None) -> dict[str, Any]:
        values = sorted(float(v) for v in values_ms)
        if not values:
            return {"path": self.path, "pass": False, "reason": "no_observations"}
        p50 = _percentile(values, 0.50)
        p95 = _percentile(values, 0.95)
        result = {
            "path": self.path,
            "count": len(values),
            "p50_ms": round(p50, 3),
            "p95_ms": round(p95, 3),
            "max_ms": round(max(values), 3),
            "budget_p50_ms": self.p50_ms,
            "budget_p95_ms": self.p95_ms,
            "budget_hard_max_ms": self.hard_max_ms,
            "pass": p50 <= self.p50_ms and p95 <= self.p95_ms and max(values) <= self.hard_max_ms,
        }
        if self.first_progress_p95_ms is not None and first_progress_ms is not None:
            progress = sorted(float(v) for v in first_progress_ms)
            result["first_progress_p95_ms"] = round(_percentile(progress, 0.95), 3) if progress else None
            result["budget_first_progress_p95_ms"] = self.first_progress_p95_ms
            result["pass"] = bool(result["pass"] and progress and _percentile(progress, 0.95) <= self.first_progress_p95_ms)
        return result


@dataclass
class LatencyObservation:
    path: str
    started_at: float = field(default_factory=time.perf_counter)
    first_progress_ms: float | None = None
    finished_ms: float | None = None
    cold_start: bool = False
    warmup_complete: bool = False

    def mark_progress(self) -> None:
        if self.first_progress_ms is None:
            self.first_progress_ms = (time.perf_counter() - self.started_at) * 1000

    def finish(self) -> float:
        if self.finished_ms is None:
            self.finished_ms = (time.perf_counter() - self.started_at) * 1000
        return self.finished_ms

    def to_evidence(self, claim: str, source: str) -> EvidenceRecord:
        return EvidenceRecord(
            claim=claim,
            source=source,
            latency_ms=self.finished_ms or self.finish(),
            path=self.path,
        )


@dataclass
class ResearchPending:
    """Serializable, resumable result when online research cannot finish."""

    query: str
    source_errors: list[str] = field(default_factory=list)
    cached_results: list[dict[str, Any]] = field(default_factory=list)
    local_fallback: list[dict[str, Any]] = field(default_factory=list)
    resume_task_id: str = field(default_factory=lambda: f"research-{uuid.uuid4().hex[:12]}")
    status: str = "research_pending"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    index = (len(values) - 1) * quantile
    lower = int(index)
    upper = min(len(values) - 1, lower + 1)
    weight = index - lower
    return values[lower] + (values[upper] - values[lower]) * weight


def latency_summary(values_ms: Iterable[float], *, path: str = "fast") -> dict[str, Any]:
    values = [float(v) for v in values_ms]
    if not values:
        return {"path": path, "count": 0, "pass": False}
    ordered = sorted(values)
    return {
        "path": path,
        "count": len(ordered),
        "p50_ms": round(_percentile(ordered, 0.50), 3),
        "p95_ms": round(_percentile(ordered, 0.95), 3),
        "max_ms": round(max(ordered), 3),
        "mean_ms": round(sum(ordered) / len(ordered), 3),
    }


def stable_fingerprint(value: Mapping[str, Any]) -> str:
    """Stable hash for reports and resumable task identity."""
    canonical = json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
