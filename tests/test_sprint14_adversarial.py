from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from core.metacognition import (
    Belief,
    BeliefStore,
    ConfidenceCalibrator,
    EpistemicStatus,
    EvidenceRef,
    Expectation,
    FailureEpisode,
    FailureEpisodeStore,
    Freshness,
    MetacognitionEngine,
    SelfCorrectionEngine,
    SourceType,
    Strategy,
    VerificationStatus,
    fingerprint_environment,
)


NOW = datetime(2026, 8, 17, 18, 0, tzinfo=timezone.utc)


def test_adversarial_same_false_claim_repeated_cannot_become_fact(tmp_path):
    engine = MetacognitionEngine(BeliefStore(tmp_path))
    scores = []
    for index in range(25):
        belief = engine.record(
            key="false.claim", claim="Repeated external claim", value="wrong",
            status=EpistemicStatus.INFERRED,
            evidence=[EvidenceRef(
                f"copy-{index}", SourceType.RESEARCH, "single:underlying-source",
                reliability=0.7, observed_at=NOW.isoformat(),
            )], freshness=Freshness.stable(NOW), now=NOW,
        )
        scores.append(belief.confidence)

    assert len(set(scores)) == 1
    assert belief.status is EpistemicStatus.INFERRED
    assert belief.verification_status is VerificationStatus.UNVERIFIED


def test_adversarial_two_providers_copying_one_source_count_once():
    calibrator = ConfidenceCalibrator()
    belief = Belief(
        key="claim", claim="Provider claim", value=True,
        status=EpistemicStatus.INFERRED,
        evidence_refs=[
            EvidenceRef("provider-a", SourceType.PROVIDER, "upstream:same", 0.8),
            EvidenceRef("provider-b", SourceType.PROVIDER, "upstream:same", 0.8),
        ], freshness=Freshness.stable(NOW),
    )

    result = calibrator.calibrate(belief, now=NOW)

    assert result.inputs["independent_sources"] == 1
    assert result.confidence < 0.8


def test_adversarial_stale_memory_loses_to_disk_observation(tmp_path):
    engine = MetacognitionEngine(BeliefStore(tmp_path))
    engine.record(
        key="file.state", claim="File state", value="old",
        status=EpistemicStatus.INFERRED,
        evidence=[EvidenceRef("memory", SourceType.MEMORY, "memory:file", 0.8)],
        freshness=Freshness.volatile(NOW - timedelta(hours=1), ttl_seconds=30), now=NOW,
    )

    decision = engine.resolve(
        key="file.state", claim="File state",
        observer=lambda: {"value": "current", "source_id": "disk:file"}, now=NOW,
    )

    assert decision.belief.value == "current"
    assert decision.belief.status is EpistemicStatus.OBSERVED
    assert decision.belief.contradictions


def test_adversarial_provider_ok_with_unchanged_state_never_reports_success(tmp_path):
    correction = SelfCorrectionEngine(FailureEpisodeStore(tmp_path), max_attempts=1)

    report = correction.run(
        goal="change setting", task_class="config",
        strategies=[Strategy("provider", lambda: SimpleNamespace(ok=True))],
        expectation=Expectation("x", "change", "", {"setting": "new"}, "read", []),
        observer=lambda: {"setting": "old"}, environment={"app": "fixture"},
    )

    assert report.attempts[0].reported_success is True
    assert report.verified is False
    assert report.state == "research_required"


def test_adversarial_contextual_failure_overrides_prior_success_label(tmp_path):
    store = FailureEpisodeStore(tmp_path)
    environment = {"app": "fixture", "version": "1"}
    store.record(FailureEpisode(
        goal="change", task_class="config", strategy="provider_marked_successful",
        failure_category="expectation_mismatch", observed_mismatch={"state": "old"},
        environment_fingerprint=fingerprint_environment(environment), confidence=0.95,
        successful_repair="direct_write",
    ))
    calls = []
    state = {"value": "old"}
    report = SelfCorrectionEngine(FailureEpisodeStore(tmp_path)).run(
        goal="change again", task_class="config",
        strategies=[
            Strategy("provider_marked_successful", lambda: calls.append("bad")),
            Strategy("direct_write", lambda: calls.append("good") or state.update(value="new")),
        ], expectation=Expectation("x", "change", "", {"value": "new"}, "read", []),
        observer=lambda: dict(state), environment=environment,
    )

    assert calls == ["good"]
    assert report.verified is True


def test_adversarial_leading_question_does_not_seed_claim(tmp_path):
    engine = MetacognitionEngine(BeliefStore(tmp_path))

    result = engine.resolve(
        key="software.version", claim="Версия ведь точно 99.9?", now=NOW,
    )

    assert result.belief.value is None
    assert result.belief.claim == "software.version"
    assert result.response == "Пока не знаю. Могу проверить."


def test_confidence_decays_with_freshness_and_provider_uncertainty():
    evidence = EvidenceRef(
        "provider", SourceType.PROVIDER, "provider:unique", 0.9,
        observed_at=NOW.isoformat(), provider_uncertainty=0.0,
    )
    fresh = Belief(
        key="site", claim="Site state", value=True, status=EpistemicStatus.INFERRED,
        evidence_refs=[evidence], freshness=Freshness.volatile(NOW, ttl_seconds=60),
    )
    uncertain = Belief.from_dict(fresh.to_dict())
    uncertain.evidence_refs[0].provider_uncertainty = 0.8

    calibrator = ConfidenceCalibrator()
    fresh_score = calibrator.calibrate(fresh, now=NOW).confidence
    stale_score = calibrator.calibrate(fresh, now=NOW + timedelta(minutes=2)).confidence
    uncertain_score = calibrator.calibrate(uncertain, now=NOW).confidence

    assert stale_score < fresh_score
    assert uncertain_score < fresh_score


def test_resolution_order_uses_capability_before_research_and_user(tmp_path):
    order = []
    engine = MetacognitionEngine(BeliefStore(tmp_path))

    decision = engine.resolve(
        key="state", claim="State",
        observer=lambda: order.append("observer") or None,
        capability=lambda: order.append("capability") or {
            "value": "found", "source_id": "capability:inspect", "verified": True,
        },
        researcher=lambda: order.append("research") or {"value": "web"},
        now=NOW,
    )

    assert order == ["observer", "capability"]
    assert decision.action == "act"
    assert decision.belief.value == "found"
