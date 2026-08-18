"""Contradiction-aware belief updates and verify-before-ask decisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from core.metacognition.calibration import ConfidenceCalibrator
from core.metacognition.freshness import FreshnessPolicy
from core.metacognition.models import (
    Belief, EpistemicState, EpistemicStatus, EvidenceRef, Freshness, FreshnessState,
    SourceType, VerificationStatus, utcnow,
)
from core.metacognition.store import BeliefStore


@dataclass(frozen=True)
class KnowledgeDecision:
    action: str
    belief: Belief
    response: str
    evidence: tuple[str, ...] = ()


_SOURCE_AUTHORITY = {
    SourceType.DIRECT_OBSERVATION: 0.90,
    SourceType.LOCAL_SYSTEM: 0.88,
    SourceType.VERIFIED_EPISODE: 0.80,
    SourceType.CAPABILITY: 0.68,
    SourceType.RESEARCH: 0.58,
    SourceType.PROVIDER: 0.55,
    SourceType.USER: 0.52,
    SourceType.MEMORY: 0.38,
    SourceType.INFERENCE: 0.25,
}


class MetacognitionEngine:
    def __init__(self, store: BeliefStore, *, calibrator: ConfidenceCalibrator | None = None,
                 freshness_policy: FreshnessPolicy | None = None,
                 risk_policy: Any = None, audit: Any = None) -> None:
        self.store = store
        self.calibrator = calibrator or ConfidenceCalibrator()
        self.freshness_policy = freshness_policy or FreshnessPolicy()
        self.risk_policy = risk_policy
        self.audit = audit

    def record(self, *, key: str, claim: str, value: Any,
               status: EpistemicStatus, evidence: list[EvidenceRef],
               freshness: Freshness, verification_status: VerificationStatus = VerificationStatus.UNVERIFIED,
               now: datetime | None = None) -> Belief:
        moment = self._now(now)
        incoming = Belief(
            key=key, claim=claim, value=value, status=status,
            evidence_refs=self._deduplicate(evidence),
            source_types=list(dict.fromkeys(item.source_type for item in evidence)),
            freshness=freshness, verification_status=verification_status,
            created_at=moment.isoformat(), updated_at=moment.isoformat(),
        )
        current = self.store.get(key)
        transition = "created"
        if current is not None and current.value == incoming.value:
            incoming.created_at = current.created_at
            incoming.evidence_refs = self._deduplicate(current.evidence_refs + incoming.evidence_refs)
            incoming.source_types = list(dict.fromkeys(
                current.source_types + incoming.source_types
            ))
            incoming.contradictions = list(current.contradictions)
            incoming.supersedes = list(current.supersedes)
            incoming.status = self._stronger_status(current.status, incoming.status)
            incoming.verification_status = self._stronger_verification(
                current.verification_status, incoming.verification_status,
            )
            if self._authority(current, moment) > self._authority(incoming, moment):
                incoming.freshness = current.freshness
            transition = "reinforced"
        elif current is not None:
            incoming, transition = self._resolve_conflict(current, incoming, moment)
        calibration = self.calibrator.calibrate(incoming, now=moment)
        incoming.confidence = calibration.confidence
        saved = self.store.upsert(incoming)
        self._audit("belief_transition", {
            "key": saved.key, "transition": transition, "status": saved.status.value,
            "confidence": saved.confidence, "evidence_refs": list(calibration.independent_evidence_refs),
            "confidence_inputs": calibration.inputs,
            "contradictions": list(saved.contradictions),
        })
        return saved

    def resolve(self, *, key: str, claim: str,
                observer: Callable[[], Any] | None = None,
                capability: Callable[[], Any] | None = None,
                researcher: Callable[[], Any] | None = None,
                observer_risk: str = "low", now: datetime | None = None) -> KnowledgeDecision:
        moment = self._now(now)
        existing = self.store.get(key)
        if existing is not None and self._answerable(existing, moment):
            return KnowledgeDecision("answer", existing, self._answer_text(existing),
                                     tuple(item.ref_id for item in existing.evidence_refs))

        if observer is not None:
            if self.risk_policy is not None:
                decision = self.risk_policy.decide(confidence=0.95, risk=observer_risk)
                if getattr(decision, "action", "") == "confirm":
                    belief = existing or self._unknown(key, moment)
                    return KnowledgeDecision(
                        "wait", belief, "Для этой проверки потребуется ваше подтверждение.",
                        (str(getattr(decision, "reason", "risk gate")),),
                    )
            observed = self._try_source(observer)
            if observed is not None:
                belief = self._record_observation(key, claim, observed, SourceType.LOCAL_SYSTEM, moment)
                return KnowledgeDecision("observe", belief, self._observation_text(belief),
                                         tuple(item.ref_id for item in belief.evidence_refs))

        for action, source, callback in (
            ("act", SourceType.CAPABILITY, capability),
            ("research", SourceType.RESEARCH, researcher),
        ):
            if callback is None:
                continue
            result = self._try_source(callback)
            if result is not None:
                belief = self._record_observation(key, claim, result, source, moment)
                return KnowledgeDecision(action, belief, self._observation_text(belief),
                                         tuple(item.ref_id for item in belief.evidence_refs))

        belief = existing or self._unknown(key, moment)
        if existing is None:
            belief = self.store.upsert(belief)
        return KnowledgeDecision("ask", belief, "Пока не знаю. Могу проверить.")

    def certainty_response(self, key: str, *, now: datetime | None = None) -> str:
        belief = self.store.get(key)
        if belief is None or belief.status is EpistemicStatus.UNKNOWN:
            return "Пока не знаю. Могу проверить."
        if belief.freshness.state(self._now(now)) is FreshnessState.STALE:
            return "Пока нет. Данные устарели — сначала проверю."
        if self._answerable(belief, self._now(now)):
            return "Да. " + self.provenance_response(key)
        return "Пока нет. У меня есть только косвенные данные."

    def provenance_response(self, key: str) -> str:
        belief = self.store.get(key)
        if belief is None or not belief.evidence_refs:
            return "Источник пока не подтверждён."
        sources = {item.source_type for item in belief.evidence_refs}
        self._audit("provenance", {
            "key": key,
            "source_types": sorted(item.value for item in sources),
            "evidence_refs": [item.ref_id for item in belief.evidence_refs],
        })
        if SourceType.LOCAL_SYSTEM in sources or SourceType.DIRECT_OBSERVATION in sources:
            return "Я проверил это в локальной системе."
        if SourceType.VERIFIED_EPISODE in sources:
            return "Это сохранено из нашей предыдущей подтверждённой задачи."
        if SourceType.MEMORY in sources:
            return "Это взято из сохранённой памяти и ещё требует проверки."
        if SourceType.RESEARCH in sources:
            return "Это получено из проверенного источника исследования."
        if SourceType.USER in sources:
            return "Вы сообщили это ранее."
        return "Это следует из зарегистрированного результата, который ещё нужно проверить."

    def summary(self, *, now: datetime | None = None) -> dict[str, list[str]]:
        moment = self._now(now)
        result = {"known": [], "unknown": [], "uncertain": [],
                  "conflicted": [], "needs_verification": []}
        for belief in self.store.all():
            if belief.status in {EpistemicStatus.KNOWN, EpistemicStatus.OBSERVED} and self._answerable(belief, moment):
                result["known"].append(belief.key)
            elif belief.status is EpistemicStatus.UNKNOWN:
                result["unknown"].append(belief.key)
            elif belief.status is EpistemicStatus.CONFLICTED:
                result["conflicted"].append(belief.key)
            else:
                result["uncertain"].append(belief.key)
            if (belief.verification_status is not VerificationStatus.VERIFIED
                    or belief.freshness.state(moment) is FreshnessState.STALE):
                result["needs_verification"].append(belief.key)
        return result

    def epistemic_state(self, *, active_key: str = "") -> EpistemicState:
        return EpistemicState(self.store.all(), active_key=active_key)

    def _record_observation(self, key: str, claim: str, result: dict[str, Any],
                            source: SourceType, moment: datetime) -> Belief:
        verified = bool(result.get("verified", source is SourceType.LOCAL_SYSTEM))
        direct = bool(result.get("direct", source is SourceType.LOCAL_SYSTEM))
        evidence = EvidenceRef(
            ref_id=str(result.get("source_id") or f"{source.value}:{key}"),
            source_type=source,
            origin_id=str(result.get("origin_id") or result.get("source_id") or f"{source.value}:{key}"),
            reliability=float(result.get("reliability", 0.95 if direct else 0.7)),
            observed_at=moment.isoformat(), verified=verified, direct=direct,
            provider_uncertainty=float(result.get("provider_uncertainty", 0.0)),
        )
        status = EpistemicStatus.OBSERVED if direct else EpistemicStatus.INFERRED
        verification = VerificationStatus.VERIFIED if verified else VerificationStatus.NEEDS_VERIFICATION
        return self.record(
            key=key, claim=claim, value=result.get("value"), status=status,
            evidence=[evidence], freshness=self.freshness_policy.for_key(key, moment),
            verification_status=verification, now=moment,
        )

    def _resolve_conflict(self, current: Belief, incoming: Belief,
                          moment: datetime) -> tuple[Belief, str]:
        old_score, new_score = self._authority(current, moment), self._authority(incoming, moment)
        old_note = f"previous:{current.value!r} ({','.join(item.value for item in current.source_types)})"
        new_note = f"incoming:{incoming.value!r} ({','.join(item.value for item in incoming.source_types)})"
        if new_score - old_score >= 0.15:
            incoming.created_at = current.created_at
            incoming.contradictions = list(dict.fromkeys(current.contradictions + [old_note]))
            incoming.supersedes = list(dict.fromkeys(
                current.supersedes + [item.ref_id for item in current.evidence_refs]
            ))
            return incoming, "superseded_by_stronger_evidence"
        if old_score - new_score >= 0.15:
            retained = Belief.from_dict(current.to_dict())
            retained.updated_at = moment.isoformat()
            retained.contradictions = list(dict.fromkeys(retained.contradictions + [new_note]))
            retained.supersedes.extend(item.ref_id for item in incoming.evidence_refs)
            return retained, "conflict_retained_stronger_evidence"
        conflicted = Belief.from_dict(incoming.to_dict())
        conflicted.status = EpistemicStatus.CONFLICTED
        conflicted.verification_status = VerificationStatus.NEEDS_VERIFICATION
        conflicted.created_at = current.created_at
        conflicted.evidence_refs = self._deduplicate(current.evidence_refs + incoming.evidence_refs)
        conflicted.source_types = list(dict.fromkeys(current.source_types + incoming.source_types))
        conflicted.contradictions = list(dict.fromkeys(
            current.contradictions + [old_note, new_note]
        ))
        return conflicted, "conflicted"

    def _authority(self, belief: Belief, moment: datetime) -> float:
        sources = belief.source_types or [item.source_type for item in belief.evidence_refs]
        source = max((_SOURCE_AUTHORITY.get(item, 0.2) for item in sources), default=0.2)
        direct = 0.2 if any(item.direct for item in belief.evidence_refs) else 0.0
        verified = 0.2 if belief.verification_status is VerificationStatus.VERIFIED else 0.0
        return source + direct + verified + 0.1 * belief.freshness.score(moment)

    @staticmethod
    def _deduplicate(items: list[EvidenceRef]) -> list[EvidenceRef]:
        selected: dict[str, EvidenceRef] = {}
        for item in items:
            origin = item.origin_id or item.ref_id
            previous = selected.get(origin)
            score = item.reliability + 0.2 * item.verified + 0.2 * item.direct
            old_score = previous.reliability + 0.2 * previous.verified + 0.2 * previous.direct if previous else -1
            if score > old_score:
                selected[origin] = item
        return list(selected.values())

    @staticmethod
    def _stronger_status(left: EpistemicStatus, right: EpistemicStatus) -> EpistemicStatus:
        rank = {EpistemicStatus.UNKNOWN: 0, EpistemicStatus.ASSUMED: 1,
                EpistemicStatus.INFERRED: 2, EpistemicStatus.CONFLICTED: 3,
                EpistemicStatus.OBSERVED: 4, EpistemicStatus.KNOWN: 5}
        return left if rank[left] >= rank[right] else right

    @staticmethod
    def _stronger_verification(left: VerificationStatus,
                               right: VerificationStatus) -> VerificationStatus:
        rank = {VerificationStatus.FAILED: 0, VerificationStatus.UNVERIFIED: 1,
                VerificationStatus.NEEDS_VERIFICATION: 2, VerificationStatus.VERIFIED: 3}
        return left if rank[left] >= rank[right] else right

    @staticmethod
    def _try_source(callback: Callable[[], Any]) -> dict[str, Any] | None:
        try:
            value = callback()
        except Exception:
            return None
        if isinstance(value, dict) and "value" in value:
            return dict(value)
        if value is not None:
            return {"value": value}
        return None

    @staticmethod
    def _answerable(belief: Belief, moment: datetime) -> bool:
        return (
            belief.status in {EpistemicStatus.KNOWN, EpistemicStatus.OBSERVED}
            and belief.verification_status is VerificationStatus.VERIFIED
            and belief.freshness.state(moment) is not FreshnessState.STALE
            and belief.confidence >= 0.75
        )

    def _answer_text(self, belief: Belief) -> str:
        return f"Проверил: {belief.value}."

    @staticmethod
    def _observation_text(belief: Belief) -> str:
        if belief.contradictions:
            return f"Раньше было сохранено другое значение. Сейчас система показывает {belief.value}."
        if belief.verification_status is not VerificationStatus.VERIFIED:
            return "Есть только косвенные данные. Сначала проверю."
        return f"Проверил: {belief.value}."

    @staticmethod
    def _unknown(key: str, moment: datetime) -> Belief:
        return Belief(
            key=key, claim=key, value=None, status=EpistemicStatus.UNKNOWN,
            freshness=Freshness.volatile(moment, ttl_seconds=1),
            verification_status=VerificationStatus.NEEDS_VERIFICATION,
            created_at=moment.isoformat(), updated_at=moment.isoformat(), confidence=0.0,
        )

    @staticmethod
    def _now(value: datetime | None) -> datetime:
        moment = value or datetime.now(timezone.utc)
        return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)

    def _audit(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.audit is not None:
            self.audit.record(event_type, payload)


__all__ = ["KnowledgeDecision", "MetacognitionEngine"]
