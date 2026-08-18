from __future__ import annotations

import json
from types import SimpleNamespace

from core.capability_engine import RiskConfidencePolicy
from core.metacognition import (
    AuditTrail,
    Expectation,
    ExpectationComparator,
    FailureEpisode,
    FailureEpisodeStore,
    SelfCorrectionEngine,
    Strategy,
    fingerprint_environment,
)


def test_expectation_mismatch_creates_structured_surprise():
    expectation = Expectation(
        action_id="change-1", goal="enable feature", strategy="provider_write",
        expected_effect={"feature": {"enabled": True}},
        verification_method="read config independently",
        failure_indicators=["enabled remains false"],
    )

    comparison = ExpectationComparator().compare(
        expectation, {"feature": {"enabled": False}},
        evidence_refs=["disk:config"],
    )

    assert comparison.verified is False
    assert comparison.surprise is not None
    assert comparison.surprise.mismatch["feature"]["enabled"] == {
        "expected": True, "actual": False,
    }
    assert comparison.surprise.evidence_refs == ["disk:config"]


def test_reported_success_without_effect_triggers_different_strategy(tmp_path):
    actual = {"enabled": False}
    calls = []

    def fake_success():
        calls.append("cached_write")
        return SimpleNamespace(ok=True)

    def real_change():
        calls.append("atomic_write")
        actual["enabled"] = True
        return SimpleNamespace(ok=True)

    engine = SelfCorrectionEngine(
        FailureEpisodeStore(tmp_path / "failures"), max_attempts=3,
    )
    report = engine.run(
        goal="enable feature", task_class="config_change",
        strategies=[Strategy("cached_write", fake_success), Strategy("atomic_write", real_change)],
        expectation=Expectation(
            "change", "enable feature", "", {"enabled": True},
            "read config independently", ["enabled=false"],
        ), observer=lambda: {"enabled": actual["enabled"]},
        evidence_provider=lambda: ["disk:config"],
        environment={"app": "fixture", "version": "2"},
    )

    assert calls == ["cached_write", "atomic_write"]
    assert report.verified is True
    assert report.selected_strategy == "atomic_write"
    assert len(report.surprises) == 1
    assert report.attempts[0].reported_success is True
    assert report.attempts[0].verified is False
    assert report.failure_episodes[0].successful_repair == "atomic_write"


def test_repeated_identical_failed_strategy_is_not_retried(tmp_path):
    calls = []
    engine = SelfCorrectionEngine(FailureEpisodeStore(tmp_path), max_attempts=5)

    report = engine.run(
        goal="change", task_class="config",
        strategies=[
            Strategy("same", lambda: calls.append("same") or True),
            Strategy("same", lambda: calls.append("same") or True),
        ],
        expectation=Expectation("x", "change", "", {"value": 2}, "inspect", []),
        observer=lambda: {"value": 1}, environment={"app": "fixture"},
    )

    assert calls == ["same"]
    assert report.verified is False
    assert report.state == "research_required"
    assert report.skipped_strategies == ["same"]
    assert report.strategy_confidence["same"] < 1.0


def test_failure_episode_is_contextual_not_global_blacklist(tmp_path):
    store = FailureEpisodeStore(tmp_path)
    env_a = fingerprint_environment({"app": "fixture", "version": "1"})
    env_b = fingerprint_environment({"app": "fixture", "version": "2"})
    store.record(FailureEpisode(
        goal="enable", task_class="config", strategy="cached_write",
        failure_category="expectation_mismatch",
        observed_mismatch={"enabled": {"expected": True, "actual": False}},
        environment_fingerprint=env_a, confidence=0.9,
    ))

    assert store.avoid_strategies("config", env_a) == {"cached_write"}
    assert store.avoid_strategies("config", env_b) == set()


def test_restart_avoids_previously_failed_strategy_in_matching_context(tmp_path):
    store = FailureEpisodeStore(tmp_path)
    env = {"app": "fixture", "version": "2"}
    fingerprint = fingerprint_environment(env)
    store.record(FailureEpisode(
        goal="enable", task_class="config", strategy="cached_write",
        failure_category="expectation_mismatch", observed_mismatch={"enabled": False},
        environment_fingerprint=fingerprint, confidence=0.95,
        successful_repair="atomic_write",
    ))
    calls = []
    actual = {"enabled": False}

    reopened = SelfCorrectionEngine(FailureEpisodeStore(tmp_path), max_attempts=3)
    report = reopened.run(
        goal="enable again", task_class="config",
        strategies=[
            Strategy("cached_write", lambda: calls.append("cached") or True),
            Strategy("atomic_write", lambda: calls.append("atomic") or actual.update(enabled=True)),
        ],
        expectation=Expectation("x", "enable", "", {"enabled": True}, "inspect", []),
        observer=lambda: dict(actual), environment=env,
    )

    assert calls == ["atomic"]
    assert report.verified is True
    assert report.skipped_strategies == ["cached_write"]


def test_self_correction_respects_risk_gate(tmp_path):
    calls = []
    engine = SelfCorrectionEngine(
        FailureEpisodeStore(tmp_path), risk_policy=RiskConfidencePolicy(),
    )

    report = engine.run(
        goal="system change", task_class="system",
        strategies=[Strategy("change", lambda: calls.append(True))],
        expectation=Expectation("x", "system", "", {"changed": True}, "inspect", []),
        observer=lambda: {"changed": False}, environment={}, risk="high",
    )

    assert report.state == "waiting_for_user"
    assert report.needs_confirmation is True
    assert calls == []


def test_failure_store_filters_secrets_and_raw_traceback(tmp_path):
    store = FailureEpisodeStore(tmp_path)
    store.record(FailureEpisode(
        goal="use password=super-secret", task_class="config",
        strategy="provider", failure_category="Traceback Error 500",
        observed_mismatch={"token": "raw-secret", "state": "unchanged"},
        environment_fingerprint="env", confidence=0.8,
    ))

    raw = store.path.read_text(encoding="utf-8")

    assert "super-secret" not in raw
    assert "raw-secret" not in raw
    assert "Traceback" not in raw


def test_audit_bundle_is_machine_readable_and_contains_no_private_reasoning(tmp_path):
    audit = AuditTrail(tmp_path / "audit")
    audit.record("expectation", {
        "expected_effect": {"enabled": True},
        "reasoning": "private scratch text",
        "evidence_refs": ["disk:config"],
    })
    audit.record("observation", {"observed": {"enabled": False}})

    bundle = audit.export_bundle(
        tmp_path / "sprint14_audit.json", beliefs=[], failures=[],
    )
    raw = bundle.read_text(encoding="utf-8")
    payload = json.loads(raw)

    assert payload["schema"] == "atlas.metacognition.audit.v1"
    assert {event["type"] for event in payload["events"]} == {"expectation", "observation"}
    assert "private scratch text" not in raw
    assert "reasoning" not in raw
