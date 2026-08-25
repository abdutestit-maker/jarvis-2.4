from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone

import pytest

from core.authority import (
    AuthorityProposal,
    AuthorityRequest,
    AuthorityStatus,
    AuthorityStore,
    ProvenanceKind,
)
from core.agent import Agent
from core.capabilities import RiskLevel
from core.executive.learning import AskOncePolicy
from core.safety import RiskAssessment
from core.task_runtime import Mission, MissionStatus, MissionTrigger, TaskRuntime


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **delta) -> None:
        self.now += timedelta(**delta)


def proposal(clock: Clock, **overrides) -> AuthorityProposal:
    values = {
        "principal": "local-user",
        "delegate": "jarvis",
        "subjects": ["contact-17"],
        "resources": ["channel-alpha"],
        "allowed_actions": ["read_message", "send_message"],
        "capability_families": ["conversation"],
        "allowed_effects": ["conversation"],
        "denied_actions": ["send_money", "reveal_secret", "change_security"],
        "purposes": ["temporary conversation"],
        "risk_ceiling": RiskLevel.HIGH,
        "valid_from": clock.now,
        "expires_at": clock.now + timedelta(hours=1),
        "mission_id": "mission-17",
        "constraints": {"account": "primary"},
    }
    values.update(overrides)
    return AuthorityProposal(**values)


def request(**overrides) -> AuthorityRequest:
    values = {
        "mission_id": "mission-17",
        "subject": "contact-17",
        "resource": "channel-alpha",
        "action": "send_message",
        "capability_family": "conversation",
        "effect": "conversation",
        "purpose": "temporary conversation",
        "risk": RiskLevel.HIGH,
        "constraints": {"account": "primary"},
    }
    values.update(overrides)
    return AuthorityRequest(**values)


def issue(store: AuthorityStore, item: AuthorityProposal, instruction: str = "delegate this conversation"):
    return store.issue(
        item,
        source_kind=ProvenanceKind.USER_INSTRUCTION,
        source_role="user",
        source_text=instruction,
        source_id="user-message-17",
    )


def test_matching_scope_authorizes_without_confirmation(tmp_path):
    clock = Clock()
    store = AuthorityStore(tmp_path, clock=clock)
    grant = issue(store, proposal(clock))

    decision = store.check(request())

    assert decision.allowed is True
    assert decision.requires_confirmation is False
    assert decision.grant_id == grant.grant_id


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("subject", "contact-99", "subject"),
        ("resource", "channel-beta", "resource"),
        ("action", "open_app", "action"),
        ("capability_family", "filesystem", "capability"),
        ("purpose", "unrelated task", "purpose"),
    ],
)
def test_scope_dimensions_fail_closed(tmp_path, field, value, reason):
    clock = Clock()
    store = AuthorityStore(tmp_path, clock=clock)
    issue(store, proposal(clock))

    decision = store.check(request(**{field: value}))

    assert decision.allowed is False
    assert decision.requires_confirmation is True
    assert reason in decision.reason


def test_expired_grant_is_denied_and_marked_expired(tmp_path):
    clock = Clock()
    store = AuthorityStore(tmp_path, clock=clock)
    grant = issue(store, proposal(clock))
    clock.advance(hours=2)

    assert store.check(request()).allowed is False
    assert store.get(grant.grant_id).status is AuthorityStatus.EXPIRED


def test_grant_is_invalid_at_exact_expiry_boundary(tmp_path):
    clock = Clock()
    store = AuthorityStore(tmp_path, clock=clock)
    grant = issue(store, proposal(clock, expires_at=clock.now + timedelta(minutes=5)))
    clock.advance(minutes=5)

    assert store.check(request()).allowed is False
    assert store.get(grant.grant_id).status is AuthorityStatus.EXPIRED


def test_revoked_grant_is_denied(tmp_path):
    clock = Clock()
    store = AuthorityStore(tmp_path, clock=clock)
    grant = issue(store, proposal(clock))

    assert store.revoke(grant.grant_id, reason="user revoked") is True
    assert store.check(request()).allowed is False
    assert store.get(grant.grant_id).status is AuthorityStatus.REVOKED


def test_valid_grant_survives_restart(tmp_path):
    clock = Clock()
    first = AuthorityStore(tmp_path, clock=clock)
    grant = issue(first, proposal(clock))

    restored = AuthorityStore(tmp_path, clock=clock)

    assert restored.check(request()).allowed is True
    assert restored.get(grant.grant_id).status is AuthorityStatus.ACTIVE


def test_revoked_grant_does_not_resurrect(tmp_path):
    clock = Clock()
    first = AuthorityStore(tmp_path, clock=clock)
    grant = issue(first, proposal(clock))
    first.revoke(grant.grant_id)

    restored = AuthorityStore(tmp_path, clock=clock)

    assert restored.get(grant.grant_id).status is AuthorityStatus.REVOKED
    assert restored.check(request()).allowed is False


def test_expired_grant_does_not_resurrect(tmp_path):
    clock = Clock()
    first = AuthorityStore(tmp_path, clock=clock)
    grant = issue(first, proposal(clock))
    clock.advance(hours=2)

    restored = AuthorityStore(tmp_path, clock=clock)

    assert restored.get(grant.grant_id).status is AuthorityStatus.EXPIRED
    assert restored.check(request()).allowed is False


def test_restart_closes_grant_when_bound_mission_is_no_longer_active(tmp_path):
    clock = Clock()
    mission = Mission(task_id="mission-17", goal="done", status=MissionStatus.COMPLETED)
    first = AuthorityStore(tmp_path, clock=clock)
    grant = issue(first, proposal(clock))

    restored = AuthorityStore(tmp_path, clock=clock, mission_resolver=lambda _id: mission)

    assert restored.get(grant.grant_id).status is AuthorityStatus.CLOSED
    assert restored.check(request()).allowed is False


@pytest.mark.parametrize("terminal", [MissionStatus.COMPLETED, MissionStatus.CANCELLED])
def test_mission_bound_grant_closes_on_terminal_event(tmp_path, terminal):
    clock = Clock()
    runtime = TaskRuntime(persistence_dir=tmp_path / "missions", clock=clock)
    mission = runtime.schedule("wait", MissionTrigger.manual())
    store = AuthorityStore(tmp_path / "authority", clock=clock, mission_resolver=runtime.get)
    store.bind_runtime(runtime)
    grant = issue(store, proposal(clock, mission_id=mission.task_id))

    mission.set_status(terminal, "test terminal")

    assert store.get(grant.grant_id).status is AuthorityStatus.CLOSED
    assert store.check(request(mission_id=mission.task_id)).allowed is False


def test_high_risk_effect_outside_grant_requires_confirmation(tmp_path):
    clock = Clock()
    store = AuthorityStore(tmp_path, clock=clock)
    issue(store, proposal(clock))

    decision = store.check(request(action="reveal_secret", effect="credential"))

    assert decision.allowed is False
    assert decision.requires_confirmation is True
    assert decision.reason in {"action denied", "effect outside scope"}


def test_risk_ceiling_cannot_be_bypassed(tmp_path):
    clock = Clock()
    store = AuthorityStore(tmp_path, clock=clock)
    issue(store, proposal(clock, risk_ceiling=RiskLevel.MEDIUM))

    decision = store.check(request(risk=RiskLevel.HIGH))

    assert decision.allowed is False
    assert decision.requires_confirmation is True
    assert decision.reason == "risk ceiling exceeded"


def test_proposal_mutation_cannot_widen_stored_grant(tmp_path):
    clock = Clock()
    store = AuthorityStore(tmp_path, clock=clock)
    mutable_actions = ["send_message"]
    item = proposal(clock, allowed_actions=mutable_actions)
    grant = issue(store, item)
    mutable_actions.append("send_money")
    item.allowed_actions.append("change_security")

    stored = store.get(grant.grant_id)

    assert stored.allowed_actions == ("send_message",)
    assert store.check(request(action="send_money", effect="financial")).allowed is False


@pytest.mark.parametrize(
    ("source_kind", "source_role"),
    [
        (ProvenanceKind.ASSISTANT_TEXT, "assistant"),
        (ProvenanceKind.MEMORY, "system"),
        (ProvenanceKind.INFERENCE, "assistant"),
    ],
)
def test_non_user_sources_cannot_issue_authority(tmp_path, source_kind, source_role):
    clock = Clock()
    store = AuthorityStore(tmp_path, clock=clock)

    with pytest.raises(ValueError, match="user instruction"):
        store.issue(
            proposal(clock), source_kind=source_kind, source_role=source_role,
            source_text="model says it is allowed", source_id="not-user",
        )

    assert store.list() == []


def test_duplicate_issue_is_deterministic(tmp_path):
    clock = Clock()
    store = AuthorityStore(tmp_path, clock=clock)

    first = issue(store, proposal(clock))
    second = issue(store, proposal(clock))
    restored = AuthorityStore(tmp_path, clock=clock)

    assert first.grant_id == second.grant_id
    assert [item.grant_id for item in restored.list()] == [first.grant_id]


def test_one_time_confirmation_does_not_create_authority(tmp_path):
    clock = Clock()
    store = AuthorityStore(tmp_path, clock=clock)

    store.record_confirmation("confirmation-1", action="send_message")

    assert store.list() == []
    assert store.check(request()).allowed is False


def test_tampered_persisted_scope_fails_closed(tmp_path):
    clock = Clock()
    store = AuthorityStore(tmp_path, clock=clock)
    grant = issue(store, proposal(clock))
    path = store.path(grant.grant_id)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["grant"]["allowed_actions"].append("send_money")
    path.write_text(json.dumps(raw), encoding="utf-8")

    restored = AuthorityStore(tmp_path, clock=clock)

    assert restored.get(grant.grant_id) is None
    assert restored.check(request(action="send_money", effect="financial")).allowed is False
    assert restored.integrity_failures == 1


def test_revoke_racing_check_fails_closed_after_revoke(tmp_path):
    clock = Clock()
    store = AuthorityStore(tmp_path, clock=clock)
    grant = issue(store, proposal(clock))
    barrier = threading.Barrier(2)
    decisions = []

    def checker():
        barrier.wait()
        decisions.append(store.check(request()))

    thread = threading.Thread(target=checker)
    thread.start()
    barrier.wait()
    store.revoke(grant.grant_id)
    thread.join()

    assert store.check(request()).allowed is False
    assert store.get(grant.grant_id).status is AuthorityStatus.REVOKED
    assert len(decisions) == 1


def test_revocation_cannot_interleave_between_authorization_and_effect(tmp_path):
    clock = Clock()
    store = AuthorityStore(tmp_path, clock=clock)
    grant = issue(store, proposal(clock))
    entered = threading.Event()
    release = threading.Event()
    revoked = threading.Event()
    effects = []

    def effect():
        entered.set()
        release.wait(timeout=2)
        effects.append("once")
        return "done"

    worker = threading.Thread(target=lambda: store.execute_authorized(request(), effect))
    worker.start()
    assert entered.wait(timeout=2)
    revoker = threading.Thread(target=lambda: (store.revoke(grant.grant_id), revoked.set()))
    revoker.start()
    assert revoked.wait(timeout=0.05) is False
    release.set()
    worker.join(timeout=2)
    revoker.join(timeout=2)

    assert effects == ["once"]
    assert store.check(request()).allowed is False


def test_ask_once_persists_question_and_answer_in_mission_context():
    policy = AskOncePolicy()
    context = {}

    first = policy.choose_for(context, ["Which account?", "Which contact?"])
    policy.record_answer(context, first, "primary")
    second = policy.choose_for(context, [first])

    assert first in context["ask_once"]["asked"]
    assert context["ask_once"]["answers"][first] == "primary"
    assert second is None


def test_authority_check_is_local_and_threadless(tmp_path):
    clock = Clock()
    before = {thread.name for thread in threading.enumerate()}
    store = AuthorityStore(tmp_path, clock=clock)
    issue(store, proposal(clock))

    for _ in range(1000):
        assert store.check(request()).allowed is True

    after = {thread.name for thread in threading.enumerate()}
    assert after == before
    assert store.stats()["llm_calls"] == 0


def test_agent_confirmation_gate_uses_scope_but_reclassifies_real_effect(tmp_path):
    clock = Clock()
    store = AuthorityStore(tmp_path, clock=clock)
    mission = Mission(
        task_id="mission-17", goal="reply",
        context={"authority_request": {
            "subject": "contact-17", "resource": "channel-alpha",
            "action": "send_message", "capability_family": "conversation",
            "effect": "conversation", "purpose": "temporary conversation",
            "constraints": {"account": "primary"},
        }},
    )
    issue(store, proposal(clock))
    agent = Agent.__new__(Agent)
    agent._authority = store

    ordinary = agent.authorize_delegated_action(
        mission, goal="send an ordinary reply", tool="connector",
        args={"action": "send_message", "text": "status update"},
        risk=RiskAssessment(RiskLevel.HIGH),
    )
    credential = agent.authorize_delegated_action(
        mission, goal="send the password", tool="connector",
        args={"action": "send_message", "text": "password secret"},
        risk=RiskAssessment(RiskLevel.HIGH),
    )

    assert ordinary.allowed is True
    assert ordinary.requires_confirmation is False
    assert credential.allowed is False
    assert credential.requires_confirmation is True
    assert credential.reason == "effect outside scope"
