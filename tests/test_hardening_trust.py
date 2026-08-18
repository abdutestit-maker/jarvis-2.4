from __future__ import annotations

from core.trust import ExecutionResult, ObservationResult, VerificationResult, verify_independently


def test_provider_self_certification_is_not_independent_verification() -> None:
    execution = ExecutionResult(ok=True, provider="provider-a", payload={"ok": True})
    observation = ObservationResult(ok=True, source="provider-a", state={"ok": True})
    result = verify_independently(execution, observation, expected={"ok": True})
    assert isinstance(result, VerificationResult)
    assert result.verified is False
    assert "independent" in result.reason.lower()


def test_independent_observer_can_verify_expected_state() -> None:
    execution = ExecutionResult(ok=True, provider="provider-a", payload={"ok": True})
    observation = ObservationResult(ok=True, source="disk-observer", state={"ok": True})
    result = verify_independently(execution, observation, expected={"ok": True})
    assert result.verified is True

