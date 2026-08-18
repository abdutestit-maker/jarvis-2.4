"""Structured epistemic facts; deliberately excludes private reasoning."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc(value: datetime | str | None = None) -> datetime:
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            parsed = datetime.now(timezone.utc)
    else:
        parsed = value or datetime.now(timezone.utc)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class EpistemicStatus(str, Enum):
    KNOWN = "known"
    OBSERVED = "observed"
    INFERRED = "inferred"
    ASSUMED = "assumed"
    UNKNOWN = "unknown"
    CONFLICTED = "conflicted"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    NEEDS_VERIFICATION = "needs_verification"
    FAILED = "failed"


class SourceType(str, Enum):
    USER = "user"
    DIRECT_OBSERVATION = "direct_observation"
    MEMORY = "memory"
    VERIFIED_EPISODE = "verified_episode"
    CAPABILITY = "capability"
    LOCAL_SYSTEM = "local_system"
    RESEARCH = "research"
    INFERENCE = "inference"
    PROVIDER = "provider"


class FreshnessState(str, Enum):
    FRESH = "fresh"
    AGING = "aging"
    STALE = "stale"
    TIMELESS = "timeless"


@dataclass
class Freshness:
    observed_at: str = field(default_factory=utcnow)
    ttl_seconds: int | None = 3600
    is_volatile: bool = True

    @classmethod
    def volatile(cls, observed_at: datetime | str, *, ttl_seconds: int) -> "Freshness":
        return cls(_utc(observed_at).isoformat(), max(1, int(ttl_seconds)), True)

    @classmethod
    def stable(cls, observed_at: datetime | str, *, ttl_seconds: int = 15_552_000) -> "Freshness":
        return cls(_utc(observed_at).isoformat(), max(1, int(ttl_seconds)), False)

    @classmethod
    def timeless(cls, observed_at: datetime | str | None = None) -> "Freshness":
        return cls(_utc(observed_at).isoformat(), None, False)

    def state(self, now: datetime | None = None) -> FreshnessState:
        if self.ttl_seconds is None:
            return FreshnessState.TIMELESS
        age = max(0.0, (_utc(now) - _utc(self.observed_at)).total_seconds())
        if age >= self.ttl_seconds:
            return FreshnessState.STALE
        if age >= self.ttl_seconds * 0.5:
            return FreshnessState.AGING
        return FreshnessState.FRESH

    def score(self, now: datetime | None = None) -> float:
        return {
            FreshnessState.TIMELESS: 1.0,
            FreshnessState.FRESH: 1.0,
            FreshnessState.AGING: 0.5,
            FreshnessState.STALE: 0.0,
        }[self.state(now)]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Freshness":
        return cls(
            observed_at=str(payload.get("observed_at") or utcnow()),
            ttl_seconds=payload.get("ttl_seconds"),
            is_volatile=bool(payload.get("is_volatile", payload.get("volatile", True))),
        )


@dataclass
class EvidenceRef:
    ref_id: str
    source_type: SourceType
    origin_id: str
    reliability: float = 0.5
    observed_at: str = field(default_factory=utcnow)
    verified: bool = False
    direct: bool = False
    memory_confidence: float | None = None
    provider_uncertainty: float = 0.0

    def __post_init__(self) -> None:
        self.reliability = max(0.0, min(1.0, float(self.reliability)))
        self.provider_uncertainty = max(0.0, min(1.0, float(self.provider_uncertainty)))
        if self.memory_confidence is not None:
            self.memory_confidence = max(0.0, min(1.0, float(self.memory_confidence)))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_type"] = self.source_type.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvidenceRef":
        value = dict(payload)
        value["source_type"] = SourceType(value.get("source_type", SourceType.INFERENCE.value))
        return cls(**value)


@dataclass
class Belief:
    key: str
    claim: str
    status: EpistemicStatus
    value: Any = None
    confidence: float = 0.0
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    source_types: list[SourceType] = field(default_factory=list)
    freshness: Freshness = field(default_factory=Freshness)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    contradictions: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utcnow)
    updated_at: str = field(default_factory=utcnow)
    supersedes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key, "claim": self.claim, "value": self.value,
            "status": self.status.value, "confidence": self.confidence,
            "evidence_refs": [item.to_dict() for item in self.evidence_refs],
            "source_types": [item.value for item in self.source_types],
            "freshness": asdict(self.freshness),
            "verification_status": self.verification_status.value,
            "contradictions": list(self.contradictions),
            "created_at": self.created_at, "updated_at": self.updated_at,
            "supersedes": list(self.supersedes),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Belief":
        return cls(
            key=str(payload.get("key") or ""), claim=str(payload.get("claim") or ""),
            value=payload.get("value"),
            status=EpistemicStatus(payload.get("status", EpistemicStatus.UNKNOWN.value)),
            confidence=float(payload.get("confidence", 0.0)),
            evidence_refs=[EvidenceRef.from_dict(item) for item in payload.get("evidence_refs", ())],
            source_types=[SourceType(item) for item in payload.get("source_types", ())],
            freshness=Freshness.from_dict(payload.get("freshness") or {}),
            verification_status=VerificationStatus(
                payload.get("verification_status", VerificationStatus.UNVERIFIED.value)
            ),
            contradictions=[str(item) for item in payload.get("contradictions", ())],
            created_at=str(payload.get("created_at") or utcnow()),
            updated_at=str(payload.get("updated_at") or utcnow()),
            supersedes=[str(item) for item in payload.get("supersedes", ())],
        )


@dataclass
class EpistemicState:
    beliefs: list[Belief] = field(default_factory=list)
    active_key: str = ""
    updated_at: str = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "beliefs": [item.to_dict() for item in self.beliefs],
            "active_key": self.active_key,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EpistemicState":
        return cls(
            beliefs=[Belief.from_dict(item) for item in payload.get("beliefs", ())
                     if isinstance(item, dict)],
            active_key=str(payload.get("active_key") or ""),
            updated_at=str(payload.get("updated_at") or utcnow()),
        )


@dataclass(frozen=True)
class CalibrationResult:
    confidence: float
    inputs: dict[str, float | int]
    independent_evidence_refs: tuple[str, ...]


__all__ = [
    "Belief", "CalibrationResult", "EpistemicState", "EpistemicStatus", "EvidenceRef", "Freshness",
    "FreshnessState", "SourceType", "VerificationStatus", "utcnow",
]
