from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace

from core.actions import DEFAULT_REGISTRY
from core.capability_engine import DesiredStateResult
from core.cognitive import CognitiveOrchestrator, CurrentMindState
from core.metacognition import EpistemicStatus
from core.metacognition import Expectation, Strategy


NOW = datetime(2026, 8, 17, 16, 0, tzinfo=timezone.utc)


def test_current_mind_state_exposes_only_safe_epistemic_summaries():
    state = CurrentMindState(
        known=["app.version"], unknown=["network.state"],
        uncertain=["website.state"], conflicted=["setting.mode"],
        needs_verification=["file.exists"], active_epistemic_key="app.version",
    )

    payload = state.to_safe_dict()

    assert payload["known"] == ["app.version"]
    assert payload["conflicted"] == ["setting.mode"]
    assert payload["needs_verification"] == ["file.exists"]
    assert not ({"reasoning", "thoughts", "scratchpad"} & set(payload))


def test_cognitive_runtime_owns_metacognition_without_replacing_existing_registry(tmp_path):
    coordinator = CognitiveOrchestrator(tmp_path, registry=DEFAULT_REGISTRY)

    assert coordinator.registry is DEFAULT_REGISTRY
    assert coordinator.metacognition.store.path.is_file() is False
    assert coordinator.correction.failures is coordinator.failure_store
    assert coordinator.audit.directory.is_dir()


def test_safe_observation_updates_current_mind_summary(tmp_path):
    coordinator = CognitiveOrchestrator(tmp_path, registry=DEFAULT_REGISTRY)

    decision = coordinator.resolve_knowledge(
        key="software.version", claim="Installed version",
        observer=lambda: {"value": "3.1", "source_id": "registry:fixture"},
        now=NOW,
    )

    assert decision.action == "observe"
    assert coordinator.state.known == ["software.version"]
    assert coordinator.state.unknown == []
    assert coordinator.state.active_epistemic_key == "software.version"


def test_natural_certainty_and_provenance_questions_use_active_belief(tmp_path):
    coordinator = CognitiveOrchestrator(tmp_path, registry=DEFAULT_REGISTRY)
    coordinator.resolve_knowledge(
        key="software.version", claim="Installed version",
        observer=lambda: {"value": "3.1", "source_id": "registry:fixture"},
        now=NOW,
    )

    certainty = coordinator.begin_interaction("Ты уверен?", implicit_address=True)
    provenance = coordinator.begin_interaction("Откуда ты это знаешь?", implicit_address=True)

    assert certainty.action == "metacognition"
    assert certainty.response == "Да. Я проверил это в локальной системе."
    assert provenance.action == "metacognition"
    assert provenance.response == "Я проверил это в локальной системе."


def test_unknown_certainty_is_truthful(tmp_path):
    coordinator = CognitiveOrchestrator(tmp_path, registry=DEFAULT_REGISTRY)

    answer = coordinator.begin_interaction("Ты уверен?", implicit_address=True)

    assert answer.response == "Пока не знаю. Могу проверить."
    assert "0." not in answer.response


def test_unverified_execution_updates_needs_verification_not_success(tmp_path):
    coordinator = CognitiveOrchestrator(tmp_path, registry=DEFAULT_REGISTRY)
    turn = coordinator.begin_interaction("Организуй файлы", implicit_address=True)
    report = SimpleNamespace(
        completed=False, state="verification_failed", needs_confirmation=False,
        verification=DesiredStateResult(False, {"organized": True}, {"organized": False}),
        results=[SimpleNamespace(ok=True)], episode=None,
    )

    response = coordinator.complete_execution(turn, report)

    assert "Готово" not in response
    assert coordinator.state.last_verified_result == ""
    assert coordinator.state.needs_verification
    belief = coordinator.metacognition.store.get(coordinator.state.active_epistemic_key)
    assert belief.verification_status.value == "failed"


def test_verified_execution_supersedes_failed_expectation_and_becomes_known(tmp_path):
    coordinator = CognitiveOrchestrator(tmp_path, registry=DEFAULT_REGISTRY)
    turn = coordinator.begin_interaction("Организуй файлы", implicit_address=True)
    failed = SimpleNamespace(
        completed=False, state="verification_failed", needs_confirmation=False,
        verification=DesiredStateResult(False, {"organized": True}, {"organized": False}),
        results=[SimpleNamespace(ok=True)], episode=None,
    )
    coordinator.complete_execution(turn, failed)
    success = SimpleNamespace(
        completed=True, state="completed", needs_confirmation=False,
        verification=DesiredStateResult(True, {}, {"organized": True}),
        results=[SimpleNamespace(ok=True)], episode=SimpleNamespace(episode_id="verified-1"),
    )

    response = coordinator.complete_execution(turn, success)
    belief = coordinator.metacognition.store.get(coordinator.state.active_epistemic_key)

    assert response == "Готово. Проверил — работает."
    assert belief.value is True
    assert belief.status in {EpistemicStatus.KNOWN, EpistemicStatus.OBSERVED}
    assert belief.confidence >= 0.9
    assert coordinator.state.active_epistemic_key in coordinator.state.known


def test_epistemic_summary_persists_across_cognitive_restart(tmp_path):
    first = CognitiveOrchestrator(tmp_path, registry=DEFAULT_REGISTRY)
    first.resolve_knowledge(
        key="software.version", claim="Installed version",
        observer=lambda: {"value": "3.1", "source_id": "registry:fixture"},
        now=NOW,
    )

    reopened = CognitiveOrchestrator(tmp_path, registry=DEFAULT_REGISTRY)

    assert reopened.metacognition.store.get("software.version").value == "3.1"
    assert reopened.state.active_epistemic_key == "software.version"
    assert reopened.state.known == ["software.version"]
    raw = json.loads(reopened.store.path.read_text(encoding="utf-8"))
    assert "known" in raw and "needs_verification" in raw


def test_cognitive_orchestrator_runs_bounded_correction_and_updates_mind(tmp_path):
    coordinator = CognitiveOrchestrator(tmp_path, registry=DEFAULT_REGISTRY)
    actual = {"enabled": False}

    response, report = coordinator.execute_with_correction(
        goal="enable fixture", task_class="fixture_config",
        strategies=[
            Strategy("no_effect", lambda: SimpleNamespace(ok=True)),
            Strategy("repair", lambda: actual.update(enabled=True)),
        ],
        expectation=Expectation("x", "enable fixture", "", {"enabled": True}, "inspect", []),
        observer=lambda: dict(actual), environment={"app": "fixture"},
    )

    assert report.verified is True
    assert response == "Готово. Проверил — работает."
    assert coordinator.state.last_verified_result
    assert coordinator.state.active_epistemic_key in coordinator.state.known


def test_cognitive_orchestrator_never_naturalizes_failed_correction_as_success(tmp_path):
    coordinator = CognitiveOrchestrator(tmp_path, registry=DEFAULT_REGISTRY)

    response, report = coordinator.execute_with_correction(
        goal="change fixture", task_class="fixture_config",
        strategies=[Strategy("no_effect", lambda: SimpleNamespace(ok=True))],
        expectation=Expectation("x", "change fixture", "", {"value": "new"}, "inspect", []),
        observer=lambda: {"value": "old"}, environment={"app": "fixture"},
    )

    assert report.verified is False
    assert "Готово" not in response
    assert coordinator.state.needs_verification
