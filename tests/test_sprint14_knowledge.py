from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from core.capability_engine import RiskConfidencePolicy
from core.metacognition import (
    BeliefStore,
    EpistemicStatus,
    EvidenceRef,
    Freshness,
    FreshnessPolicy,
    MetacognitionEngine,
    SourceType,
    VerificationStatus,
)


NOW = datetime(2026, 8, 17, 15, 0, tzinfo=timezone.utc)


def ref(ref_id, source, origin, *, verified=False, direct=False, reliability=0.7):
    return EvidenceRef(
        ref_id, source, origin, reliability,
        observed_at=NOW.isoformat(), verified=verified, direct=direct,
    )


def test_belief_store_is_bounded_private_and_restartable(tmp_path):
    store = BeliefStore(tmp_path, max_beliefs=3)
    engine = MetacognitionEngine(store)
    for index in range(5):
        engine.record(
            key=f"key.{index}", claim=f"value {index} password=secret-{index}", value=index,
            status=EpistemicStatus.INFERRED,
            evidence=[ref(f"m-{index}", SourceType.MEMORY, f"memory:{index}")],
            freshness=Freshness.stable(NOW), now=NOW + timedelta(seconds=index),
        )

    raw = store.path.read_text(encoding="utf-8")
    reopened = BeliefStore(tmp_path, max_beliefs=3)

    assert "secret-" not in raw
    assert len(reopened.all()) == 3
    assert {item.key for item in reopened.all()} == {"key.2", "key.3", "key.4"}


def test_fresh_direct_observation_supersedes_stale_memory(tmp_path):
    engine = MetacognitionEngine(BeliefStore(tmp_path))
    old = engine.record(
        key="app.version", claim="Installed version", value="1.0",
        status=EpistemicStatus.INFERRED,
        evidence=[ref("old", SourceType.MEMORY, "memory:old")],
        freshness=Freshness.volatile(NOW - timedelta(days=3), ttl_seconds=3600),
        now=NOW,
    )
    current = engine.record(
        key="app.version", claim="Installed version", value="2.0",
        status=EpistemicStatus.OBSERVED,
        evidence=[ref("disk", SourceType.LOCAL_SYSTEM, "system:app", verified=True, direct=True)],
        freshness=Freshness.volatile(NOW, ttl_seconds=3600),
        verification_status=VerificationStatus.VERIFIED, now=NOW,
    )

    assert old.value == "1.0"
    assert current.value == "2.0"
    assert current.status is EpistemicStatus.OBSERVED
    assert current.confidence >= 0.9
    assert any("1.0" in item for item in current.contradictions)
    assert "old" in current.supersedes


def test_equally_weak_conflicting_sources_remain_conflicted(tmp_path):
    engine = MetacognitionEngine(BeliefStore(tmp_path))
    engine.record(
        key="setting.mode", claim="Mode", value="A", status=EpistemicStatus.ASSUMED,
        evidence=[ref("user", SourceType.USER, "user:statement")],
        freshness=Freshness.stable(NOW), now=NOW,
    )
    belief = engine.record(
        key="setting.mode", claim="Mode", value="B", status=EpistemicStatus.INFERRED,
        evidence=[ref("provider", SourceType.PROVIDER, "provider:result")],
        freshness=Freshness.stable(NOW), now=NOW,
    )

    assert belief.status is EpistemicStatus.CONFLICTED
    assert belief.verification_status is VerificationStatus.NEEDS_VERIFICATION
    assert belief.confidence <= 0.45
    assert len(belief.contradictions) >= 2


def test_repetition_of_same_inference_never_becomes_known(tmp_path):
    engine = MetacognitionEngine(BeliefStore(tmp_path))
    first = None
    for index in range(10):
        belief = engine.record(
            key="claim.false", claim="Repeated claim", value="wrong",
            status=EpistemicStatus.INFERRED,
            evidence=[ref(f"copy-{index}", SourceType.RESEARCH, "same:upstream")],
            freshness=Freshness.stable(NOW), now=NOW,
        )
        first = first or belief.confidence

    assert belief.status is EpistemicStatus.INFERRED
    assert belief.confidence == first
    assert len(belief.evidence_refs) == 1


def test_volatile_freshness_policy_marks_old_state_stale():
    policy = FreshnessPolicy()

    version = policy.for_key("software.version", NOW - timedelta(days=2))
    identity = policy.for_key("identity.name", NOW - timedelta(days=5000))

    assert version.state(NOW).value == "stale"
    assert identity.state(NOW).value == "timeless"


def test_verify_before_ask_uses_safe_local_observation(tmp_path):
    called = []
    engine = MetacognitionEngine(
        BeliefStore(tmp_path), risk_policy=RiskConfidencePolicy(),
    )

    decision = engine.resolve(
        key="app.version", claim="Installed version",
        observer=lambda: called.append("inspect") or {
            "value": "2.4", "source_id": "registry:app", "reliability": 0.98,
        }, observer_risk="low", now=NOW,
    )

    assert decision.action == "observe"
    assert called == ["inspect"]
    assert decision.belief.value == "2.4"
    assert decision.belief.verification_status is VerificationStatus.VERIFIED
    assert "Проверил" in decision.response


def test_stale_knowledge_is_reobserved_before_answer(tmp_path):
    engine = MetacognitionEngine(BeliefStore(tmp_path))
    engine.record(
        key="file.exists", claim="File exists", value=False,
        status=EpistemicStatus.INFERRED,
        evidence=[ref("memory", SourceType.MEMORY, "memory:file")],
        freshness=Freshness.volatile(NOW - timedelta(hours=2), ttl_seconds=60), now=NOW,
    )

    decision = engine.resolve(
        key="file.exists", claim="File exists",
        observer=lambda: {"value": True, "source_id": "disk:file"}, now=NOW,
    )

    assert decision.action == "observe"
    assert decision.belief.value is True
    assert any("False" in item for item in decision.belief.contradictions)


def test_risk_gate_remains_authoritative_before_observation(tmp_path):
    called = []
    engine = MetacognitionEngine(
        BeliefStore(tmp_path), risk_policy=RiskConfidencePolicy(),
    )

    decision = engine.resolve(
        key="system.setting", claim="System setting",
        observer=lambda: called.append(True) or {"value": "x"},
        observer_risk="medium", now=NOW,
    )

    assert decision.action == "wait"
    assert called == []
    assert "подтверждение" in decision.response


def test_certainty_and_provenance_are_natural_and_factual(tmp_path):
    engine = MetacognitionEngine(BeliefStore(tmp_path))
    engine.record(
        key="app.version", claim="Installed version", value="2.0",
        status=EpistemicStatus.OBSERVED,
        evidence=[ref("disk", SourceType.LOCAL_SYSTEM, "system:app", verified=True, direct=True)],
        freshness=Freshness.volatile(NOW, ttl_seconds=3600),
        verification_status=VerificationStatus.VERIFIED, now=NOW,
    )

    certainty = engine.certainty_response("app.version", now=NOW)
    provenance = engine.provenance_response("app.version")

    assert certainty == "Да. Я проверил это в локальной системе."
    assert provenance == "Я проверил это в локальной системе."
    assert "confidence" not in certainty.casefold()


def test_unknown_answer_is_truthful_and_does_not_record_leading_assumption(tmp_path):
    store = BeliefStore(tmp_path)
    engine = MetacognitionEngine(store)

    decision = engine.resolve(
        key="app.version", claim="Версия точно 9.9, верно?", now=NOW,
    )

    assert decision.action == "ask"
    assert decision.response == "Пока не знаю. Могу проверить."
    assert decision.belief.status is EpistemicStatus.UNKNOWN
    assert decision.belief.value is None
    assert "9.9" not in json.dumps(decision.belief.to_dict(), ensure_ascii=False)
