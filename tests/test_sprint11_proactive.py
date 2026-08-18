"""Evidence-based proactive policy, attention, memory and assistance profiles."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.living.models import AutonomyLevel, ComputerAssistanceLevel, ProactiveAction
from core.living.proactive import (
    AssistancePolicy,
    AttentionManager,
    AttentionSnapshot,
    ProactiveCandidate,
    ProactiveDecisionEngine,
    ProactiveMemoryStore,
    UserProfileStore,
)


NOW = datetime(2026, 8, 17, 10, tzinfo=timezone.utc)


def _candidate(**overrides) -> ProactiveCandidate:
    data = {
        "id": "organize_reports",
        "topic": "organize reports",
        "opportunity": "automate repeated report organization",
        "confidence": 0.91,
        "expected_value": 0.85,
        "reversible": True,
        "risk": "low",
        "ambiguity": 0.05,
        "evidence": ["workflow repeated", "verified semantic actions"],
        "can_prepare": True,
    }
    data.update(overrides)
    return ProactiveCandidate(**data)


def test_proactive_without_structured_evidence_is_silent(tmp_path: Path) -> None:
    engine = ProactiveDecisionEngine(ProactiveMemoryStore(tmp_path / "memory"))

    decision = engine.decide(_candidate(evidence=[]), AttentionSnapshot(), now=NOW)

    assert decision.action is ProactiveAction.SILENT
    assert decision.user_message == ""


def test_busy_user_causes_silent_prepare_not_interruption(tmp_path: Path) -> None:
    engine = ProactiveDecisionEngine(ProactiveMemoryStore(tmp_path / "memory"))

    decision = engine.decide(
        _candidate(), AttentionSnapshot(fullscreen=True, media_active=True), now=NOW,
    )

    assert decision.action is ProactiveAction.PREPARE
    assert decision.user_message == ""
    assert decision.background_allowed is True


def test_default_assistant_suggests_but_does_not_act(tmp_path: Path) -> None:
    profile = UserProfileStore(tmp_path / "profile").load()
    engine = ProactiveDecisionEngine(ProactiveMemoryStore(tmp_path / "memory"))

    decision = engine.decide(_candidate(), AttentionSnapshot(), profile=profile, now=NOW)

    assert profile.autonomy is AutonomyLevel.ASSISTANT
    assert decision.action is ProactiveAction.SUGGEST
    assert decision.user_message.count("?") == 1
    assert decision.evidence


def test_partner_can_act_only_for_low_risk_reversible_clear_action(tmp_path: Path) -> None:
    store = UserProfileStore(tmp_path / "profile")
    profile = store.update(autonomy=AutonomyLevel.PARTNER)
    engine = ProactiveDecisionEngine(ProactiveMemoryStore(tmp_path / "memory"))

    allowed = engine.decide(_candidate(), AttentionSnapshot(), profile=profile, now=NOW)
    blocked = engine.decide(
        _candidate(id="danger", topic="danger", opportunity="delete system data",
                   risk="high", danger=False),
        AttentionSnapshot(), profile=profile, now=NOW,
    )

    assert allowed.action is ProactiveAction.ACT
    assert blocked.action is not ProactiveAction.ACT


def test_missing_information_produces_one_specific_question(tmp_path: Path) -> None:
    engine = ProactiveDecisionEngine(ProactiveMemoryStore(tmp_path / "memory"))

    decision = engine.decide(
        _candidate(ambiguity=0.8, missing_information="which project folder"),
        AttentionSnapshot(), now=NOW,
    )

    assert decision.action is ProactiveAction.ASK
    assert decision.user_message.count("?") == 1
    assert "project folder" in decision.user_message


def test_warn_requires_real_danger_evidence(tmp_path: Path) -> None:
    engine = ProactiveDecisionEngine(ProactiveMemoryStore(tmp_path / "memory"))

    warning = engine.decide(
        _candidate(id="phishing", topic="suspicious download", risk="high", danger=True,
                   opportunity="suspicious executable detected", urgency=0.95),
        AttentionSnapshot(), now=NOW,
    )
    no_warning = engine.decide(
        _candidate(id="vague", topic="vague", risk="high", danger=True,
                   evidence=[], urgency=0.95),
        AttentionSnapshot(), now=NOW,
    )

    assert warning.action is ProactiveAction.WARN
    assert no_warning.action is ProactiveAction.SILENT


def test_attention_manager_suppresses_fullscreen_then_releases_after_exit() -> None:
    manager = AttentionManager()

    busy = manager.assess(AttentionSnapshot(fullscreen=True, media_active=True), urgency=0.4)
    available = manager.assess(AttentionSnapshot(), urgency=0.4)

    assert busy.can_interrupt is False
    assert busy.level.value == "NONE"
    assert available.can_interrupt is True
    assert available.level.value in {"PASSIVE", "NORMAL"}


def test_ignore_and_rejection_learning_create_adaptive_cooldown(tmp_path: Path) -> None:
    memory = ProactiveMemoryStore(tmp_path)
    memory.record("organize reports", outcome="ignored", useful=None, now=NOW)

    assert memory.allows("organize reports", now=NOW + timedelta(days=1)) is False
    memory.record("organize reports", outcome="rejected", useful=False,
                  now=NOW + timedelta(days=8))
    assert memory.allows("organize reports", now=NOW + timedelta(days=15)) is False
    assert memory.affinity("organize reports") < 0


def test_computer_assistance_profile_is_not_user_intelligence(tmp_path: Path) -> None:
    store = UserProfileStore(tmp_path)
    profile = store.update(assistance=ComputerAssistanceLevel.BEGINNER)
    loaded = store.load()

    assert loaded.assistance is ComputerAssistanceLevel.BEGINNER
    assert "intelligence" not in store.path.read_text(encoding="utf-8").lower()


def test_beginner_assistance_delegates_safe_parts_and_keeps_message_short() -> None:
    response = AssistancePolicy().plan(
        "I downloaded an app and do not understand installation",
        assistance=ComputerAssistanceLevel.BEGINNER,
        capability_available=True,
    )
    required = AssistancePolicy().plan(
        "continue installation", assistance=ComputerAssistanceLevel.BEGINNER,
        capability_available=True, requires_user_input="Windows password",
    )

    assert response.execute_safe_parts is True
    assert len(response.message.split()) < 15
    assert required.message.count(".") <= 2
    assert "Windows password" in required.message


def test_developer_profile_receives_provider_trace() -> None:
    response = AssistancePolicy().plan(
        "configure application", assistance=ComputerAssistanceLevel.DEVELOPER,
        capability_available=True, provider_trace="config → UIA → verify",
    )

    assert response.show_trace is True
    assert "config" in response.message


def test_credentials_ask_one_question_but_never_prepare_when_risk_is_high(tmp_path: Path) -> None:
    engine = ProactiveDecisionEngine(ProactiveMemoryStore(tmp_path))
    candidate = _candidate(
        opportunity="delete protected account using password",
        risk="high", requires_credentials=True, missing_information="пароль",
        can_prepare=True,
    )

    available = engine.decide(candidate, AttentionSnapshot())
    busy = engine.decide(candidate, AttentionSnapshot(media_active=True))

    assert available.action is ProactiveAction.ASK
    assert "пароль" in available.user_message
    assert busy.action is ProactiveAction.SILENT
    assert busy.user_message == ""

def test_typing_or_active_mission_defers_suggestion_to_background_prepare(tmp_path: Path) -> None:
    engine = ProactiveDecisionEngine(ProactiveMemoryStore(tmp_path))

    typing = engine.decide(_candidate(topic="typing"), AttentionSnapshot(typing_active=True))
    mission = engine.decide(_candidate(topic="mission"), AttentionSnapshot(active_mission=True))

    assert typing.action is ProactiveAction.PREPARE
    assert typing.user_message == ""
    assert mission.action is ProactiveAction.PREPARE
    assert mission.user_message == ""
