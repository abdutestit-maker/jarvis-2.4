from __future__ import annotations

from datetime import datetime, timedelta, timezone

from core.metacognition import (
    Belief,
    ConfidenceCalibrator,
    EpistemicState,
    EpistemicStatus,
    EvidenceRef,
    Freshness,
    FreshnessState,
    SourceType,
    VerificationStatus,
)


NOW = datetime(2026, 8, 17, 14, 0, tzinfo=timezone.utc)


def evidence(ref_id="obs-1", *, source=SourceType.DIRECT_OBSERVATION,
             origin="system:app", reliability=0.95, verified=True,
             direct=True, age=0, provider_uncertainty=0.0):
    return EvidenceRef(
        ref_id=ref_id, source_type=source, origin_id=origin,
        reliability=reliability, verified=verified, direct=direct,
        observed_at=(NOW - timedelta(seconds=age)).isoformat(),
        provider_uncertainty=provider_uncertainty,
    )


def test_epistemic_belief_has_only_safe_structured_fields():
    belief = Belief(
        key="app.version", claim="Installed version is 2.0", value="2.0",
        status=EpistemicStatus.OBSERVED,
        evidence_refs=[evidence()], source_types=[SourceType.DIRECT_OBSERVATION],
        freshness=Freshness.volatile(NOW, ttl_seconds=3600),
        verification_status=VerificationStatus.VERIFIED,
    )

    payload = belief.to_dict()

    assert payload["status"] == "observed"
    assert payload["verification_status"] == "verified"
    assert payload["evidence_refs"][0]["ref_id"] == "obs-1"
    assert not ({"reasoning", "thoughts", "chain_of_thought", "scratchpad"} & set(payload))

    aggregate = EpistemicState([belief], active_key="app.version").to_dict()
    assert aggregate["active_key"] == "app.version"
    assert aggregate["beliefs"][0]["claim"] == "Installed version is 2.0"


def test_direct_verified_observation_calibrates_as_high_confidence():
    belief = Belief(
        key="app.version", claim="Installed version is 2.0", value="2.0",
        status=EpistemicStatus.OBSERVED, evidence_refs=[evidence()],
        freshness=Freshness.volatile(NOW, ttl_seconds=3600),
        verification_status=VerificationStatus.VERIFIED,
    )

    result = ConfidenceCalibrator().calibrate(belief, now=NOW)

    assert result.confidence >= 0.9
    assert result.inputs["direct_observation"] == 1.0
    assert result.inputs["verified_evidence"] == 1.0


def test_inferred_memory_is_not_promoted_to_fact():
    belief = Belief(
        key="app.version", claim="Version may be 1.0", value="1.0",
        status=EpistemicStatus.INFERRED,
        evidence_refs=[evidence(
            source=SourceType.MEMORY, origin="memory:episode-1",
            reliability=0.65, verified=False, direct=False,
        )],
        freshness=Freshness.volatile(NOW, ttl_seconds=3600),
        verification_status=VerificationStatus.NEEDS_VERIFICATION,
    )

    result = ConfidenceCalibrator().calibrate(belief, now=NOW, successful_prior_episodes=20)

    assert result.confidence < 0.8
    assert belief.status is EpistemicStatus.INFERRED


def test_duplicate_evidence_from_same_origin_does_not_raise_confidence():
    single = Belief(
        key="setting", claim="Setting enabled", value=True,
        status=EpistemicStatus.INFERRED, evidence_refs=[evidence(
            ref_id="provider-a", source=SourceType.RESEARCH,
            origin="upstream:one", verified=False, direct=False,
        )], freshness=Freshness.stable(NOW, ttl_seconds=3600),
    )
    duplicate = Belief.from_dict(single.to_dict())
    duplicate.evidence_refs.append(evidence(
        ref_id="provider-b", source=SourceType.RESEARCH,
        origin="upstream:one", verified=False, direct=False,
    ))

    calibrator = ConfidenceCalibrator()
    first = calibrator.calibrate(single, now=NOW)
    repeated = calibrator.calibrate(duplicate, now=NOW)

    assert repeated.confidence == first.confidence
    assert repeated.inputs["independent_sources"] == 1


def test_independent_evidence_can_raise_but_not_force_certainty():
    belief = Belief(
        key="site.state", claim="Site is available", value=True,
        status=EpistemicStatus.INFERRED,
        evidence_refs=[
            evidence("a", source=SourceType.RESEARCH, origin="source:a",
                     verified=False, direct=False, reliability=0.75),
            evidence("b", source=SourceType.USER, origin="source:b",
                     verified=False, direct=False, reliability=0.7),
        ], freshness=Freshness.volatile(NOW, ttl_seconds=300),
    )

    result = ConfidenceCalibrator().calibrate(belief, now=NOW)

    assert result.inputs["independent_sources"] == 2
    assert 0.5 < result.confidence < 0.8


def test_contradiction_caps_confidence():
    belief = Belief(
        key="app.version", claim="Version is conflicted", value="2.0",
        status=EpistemicStatus.CONFLICTED, evidence_refs=[evidence()],
        freshness=Freshness.volatile(NOW, ttl_seconds=3600),
        contradictions=["memory:version=1.0"],
        verification_status=VerificationStatus.NEEDS_VERIFICATION,
    )

    result = ConfidenceCalibrator().calibrate(belief, now=NOW)

    assert result.inputs["contradictions"] == 1
    assert result.confidence <= 0.45


def test_stale_volatile_evidence_loses_confidence():
    freshness = Freshness.volatile(NOW - timedelta(hours=2), ttl_seconds=60)
    belief = Belief(
        key="active.window", claim="Editor is active", value="Editor",
        status=EpistemicStatus.OBSERVED, evidence_refs=[evidence(age=7200)],
        freshness=freshness, verification_status=VerificationStatus.VERIFIED,
    )

    result = ConfidenceCalibrator().calibrate(belief, now=NOW)

    assert freshness.state(NOW) is FreshnessState.STALE
    assert result.inputs["freshness"] == 0.0
    assert result.confidence < 0.75


def test_unknown_is_always_low_confidence():
    belief = Belief(
        key="missing", claim="Value is unavailable", status=EpistemicStatus.UNKNOWN,
        freshness=Freshness.volatile(NOW, ttl_seconds=1),
        verification_status=VerificationStatus.NEEDS_VERIFICATION,
    )

    assert ConfidenceCalibrator().calibrate(belief, now=NOW).confidence <= 0.15
