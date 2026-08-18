"""Explicit execution/observation/verification trust boundary."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExecutionResult:
    ok: bool
    provider: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ObservationResult:
    ok: bool
    source: str
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VerificationResult:
    verified: bool
    reason: str
    missing: dict[str, Any] = field(default_factory=dict)
    evidence: tuple[str, ...] = ()


def verify_independently(execution: ExecutionResult, observation: ObservationResult,
                         *, expected: dict[str, Any]) -> VerificationResult:
    if not execution.ok:
        return VerificationResult(False, "execution provider reported failure")
    if not observation.ok:
        return VerificationResult(False, "independent observer reported failure")
    if execution.provider.casefold() == observation.source.casefold():
        return VerificationResult(False, "independent observer is the same provider")
    missing = {key: value for key, value in expected.items() if observation.state.get(key) != value}
    if missing:
        return VerificationResult(False, "observed state does not match expected state", missing, (observation.source,))
    return VerificationResult(True, "independently observed desired state", evidence=(observation.source,))


__all__ = ["ExecutionResult", "ObservationResult", "VerificationResult", "verify_independently"]

