"""Expectation-to-observation comparison and structured surprise."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from core.metacognition.models import utcnow


@dataclass
class Expectation:
    action_id: str
    goal: str
    strategy: str
    expected_effect: dict[str, Any]
    verification_method: str
    failure_indicators: list[str]
    created_at: str = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Surprise:
    action_id: str
    expected: dict[str, Any]
    observed: dict[str, Any]
    mismatch: dict[str, Any]
    failure_indicators: list[str]
    evidence_refs: list[str]
    created_at: str = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ComparisonResult:
    verified: bool
    observed: dict[str, Any]
    surprise: Surprise | None = None


class ExpectationComparator:
    def compare(self, expectation: Expectation, observed: dict[str, Any], *,
                evidence_refs: list[str] | None = None) -> ComparisonResult:
        mismatch = self._diff(expectation.expected_effect, observed)
        if not mismatch:
            return ComparisonResult(True, dict(observed))
        surprise = Surprise(
            expectation.action_id, dict(expectation.expected_effect), dict(observed),
            mismatch, list(expectation.failure_indicators), list(evidence_refs or ()),
        )
        return ComparisonResult(False, dict(observed), surprise)

    def _diff(self, expected: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
        mismatch: dict[str, Any] = {}
        for key, wanted in expected.items():
            actual = observed.get(key)
            if isinstance(wanted, dict) and isinstance(actual, dict):
                nested = self._diff(wanted, actual)
                if nested:
                    mismatch[key] = nested
            elif actual != wanted:
                mismatch[key] = {"expected": wanted, "actual": actual}
        return mismatch


__all__ = ["ComparisonResult", "Expectation", "ExpectationComparator", "Surprise"]
