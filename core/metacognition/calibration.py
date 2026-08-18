"""Deterministic confidence calibration from inspectable evidence signals."""

from __future__ import annotations

from datetime import datetime

from core.metacognition.models import (
    Belief, CalibrationResult, EpistemicStatus, VerificationStatus,
)


class ConfidenceCalibrator:
    def calibrate(self, belief: Belief, *, now: datetime | None = None,
                  successful_prior_episodes: int = 0) -> CalibrationResult:
        independent = {}
        for item in belief.evidence_refs:
            origin = item.origin_id or item.ref_id
            previous = independent.get(origin)
            if previous is None or self._quality(item) > self._quality(previous):
                independent[origin] = item
        evidence = list(independent.values())
        reliability = sum(item.reliability for item in evidence) / len(evidence) if evidence else 0.0
        direct = 1.0 if any(item.direct for item in evidence) else 0.0
        verified = 1.0 if (
            belief.verification_status is VerificationStatus.VERIFIED
            or any(item.verified for item in evidence)
        ) else 0.0
        memory_scores = [item.memory_confidence for item in evidence
                         if item.memory_confidence is not None]
        memory = sum(memory_scores) / len(memory_scores) if memory_scores else 0.0
        uncertainty = max((item.provider_uncertainty for item in evidence), default=0.0)
        freshness = belief.freshness.score(now)
        contradiction_count = len(set(belief.contradictions))
        unresolved_conflict = 1 if belief.status is EpistemicStatus.CONFLICTED else 0
        count = len(evidence)
        independence = 0.0 if not count else 0.05 + 0.08 * min(2, count - 1)
        prior = min(0.05, max(0, int(successful_prior_episodes)) * 0.01)
        score = (
            0.10 + 0.25 * reliability + 0.25 * direct + 0.25 * verified
            + 0.10 * freshness + independence + 0.05 * memory + prior
            - 0.20 * uncertainty - 0.35 * unresolved_conflict
        )
        if freshness == 0.0:
            score -= 0.30
        caps = {
            EpistemicStatus.UNKNOWN: 0.15,
            EpistemicStatus.ASSUMED: 0.49,
            EpistemicStatus.INFERRED: 0.79,
            EpistemicStatus.CONFLICTED: 0.45,
        }
        score = min(score, caps.get(belief.status, 0.99))
        confidence = round(max(0.0, min(0.99, score)), 3)
        inputs: dict[str, float | int] = {
            "source_reliability": round(reliability, 3),
            "direct_observation": direct,
            "verified_evidence": verified,
            "freshness": freshness,
            "independent_sources": count,
            "memory_confidence": round(memory, 3),
            "contradictions": contradiction_count,
            "successful_prior_episodes": max(0, int(successful_prior_episodes)),
            "provider_uncertainty": round(uncertainty, 3),
        }
        return CalibrationResult(
            confidence, inputs,
            tuple(item.ref_id for item in evidence),
        )

    @staticmethod
    def _quality(evidence) -> float:
        return (
            evidence.reliability + 0.2 * bool(evidence.verified)
            + 0.2 * bool(evidence.direct) - 0.2 * evidence.provider_uncertainty
        )


__all__ = ["ConfidenceCalibrator"]
