from __future__ import annotations

from types import SimpleNamespace

from core.actions import DEFAULT_REGISTRY
from core.capabilities import CAPABILITIES
from core.capability_engine import (
    CapabilityCatalog,
    CapabilityPlanner,
    DesiredStateResult,
    ExecutionPlan,
    ExecutionStep,
    RiskConfidencePolicy,
)
from core.cognitive import (
    CapabilitySelfModel,
    CognitiveOrchestrator,
    CurrentMindState,
)
from core.memory.relationship import MemoryHierarchy, RelationshipMemoryStore
from core.voice.tts_sanitizer import sanitize_for_tts


def test_capability_self_model_is_generated_from_real_registries():
    model = CapabilitySelfModel(
        DEFAULT_REGISTRY, capability_registry=CAPABILITIES,
        providers={"installer": SimpleNamespace(available=True)},
        risk_policy=RiskConfidencePolicy(),
    )

    snapshot = model.snapshot()
    answer = model.answer("Ты умеешь устанавливать программы?", CurrentMindState())

    assert set(snapshot.tool_names) == {tool.name for tool in DEFAULT_REGISTRY.list_tools()}
    assert answer.known and "установ" in answer.text.casefold()
    assert "installer" in answer.evidence


def test_self_model_does_not_invent_unavailable_installer():
    model = CapabilitySelfModel(DEFAULT_REGISTRY, providers={})

    answer = model.answer("Ты умеешь устанавливать программы?", CurrentMindState())

    assert answer.known
    assert "не зарегистрирован" in answer.text.casefold()


def test_self_knowledge_current_task_comes_from_mind_state():
    model = CapabilitySelfModel(DEFAULT_REGISTRY)
    state = CurrentMindState(current_goal="настроить редактор", active_task="проверить тему")

    answer = model.answer("Что ты сейчас делаешь?", state)

    assert "настроить редактор" in answer.text
    assert "проверить тему" in answer.text


def test_contextual_followup_uses_last_verified_result():
    model = CapabilitySelfModel(DEFAULT_REGISTRY)
    state = CurrentMindState(
        current_goal="организовать файлы",
        last_verified_result="desired state verified: organized_by_extension",
        mission_state="completed",
    )

    answer = model.answer("Чем всё закончилось?", state)

    assert answer.known
    assert "организовать файлы" in answer.text
    assert "проверен" in answer.text.casefold()


def test_risk_explanation_is_derived_from_policy():
    model = CapabilitySelfModel(DEFAULT_REGISTRY, risk_policy=RiskConfidencePolicy())

    answer = model.answer("Почему ты спрашиваешь подтверждение?", CurrentMindState())

    assert answer.known
    assert "измен" in answer.text.casefold()
    assert "подтвержден" in answer.text.casefold()
    assert "high risk requires confirmation" in answer.evidence


def test_unknown_task_enters_research_pipeline_without_fake_success(tmp_path):
    catalog = CapabilityCatalog(tmp_path / "capabilities")
    coordinator = CognitiveOrchestrator(
        tmp_path / "cognitive", registry=DEFAULT_REGISTRY,
        capability_planner=CapabilityPlanner(catalog, DEFAULT_REGISTRY),
    )

    turn = coordinator.begin_interaction(
        "Атлас, сделай локальную неизвестную штуку", channel="voice",
    )

    assert turn.addressed
    assert turn.action == "research"
    assert turn.response == "Сейчас разберусь."
    assert turn.plan is not None and turn.plan.acquisition == "research"
    assert "Готово" not in turn.response


def test_retrieves_only_relevant_bounded_relationship_memory(tmp_path):
    relationship = RelationshipMemoryStore(tmp_path / "relationship")
    relevant = relationship.remember(
        "Пользователь предпочитает краткие отчёты", source="user_explicit",
        confidence=0.95, importance=0.9, key="communication_style",
    )
    relationship.remember(
        "Пользователь обычно делегирует работу с музыкой", source="outcome",
        confidence=0.8, importance=0.7, key="music",
    )
    hierarchy = MemoryHierarchy(relationship)
    coordinator = CognitiveOrchestrator(
        tmp_path / "cognitive", registry=DEFAULT_REGISTRY,
        memory_hierarchy=hierarchy,
    )

    turn = coordinator.begin_interaction("Подготовь краткий отчёт", implicit_address=True)

    assert turn.memory_refs == (f"relationship:{relevant.id}",)
    assert coordinator.state.recalled_memory_refs == [f"relationship:{relevant.id}"]
    assert len(turn.memory_refs) <= 4


def test_verification_is_required_before_success_wording(tmp_path):
    coordinator = CognitiveOrchestrator(tmp_path, registry=DEFAULT_REGISTRY)
    turn = coordinator.begin_interaction("Организуй файлы", implicit_address=True)
    unverified = SimpleNamespace(
        completed=False, state="verification_failed",
        verification=DesiredStateResult(False, {"organized": True}, {"organized": False}),
        results=[SimpleNamespace(ok=True)], needs_confirmation=False, episode=None,
    )

    response = coordinator.complete_execution(turn, unverified)

    assert "Готово" not in response
    assert coordinator.state.last_verified_result == ""
    assert coordinator.state.pending_verification

    verified = SimpleNamespace(
        completed=True, state="completed",
        verification=DesiredStateResult(True, {}, {"organized": True}),
        results=[SimpleNamespace(ok=True)], needs_confirmation=False,
        episode=SimpleNamespace(episode_id="episode-1"),
    )
    response = coordinator.complete_execution(turn, verified)

    assert response == "Готово. Проверил — работает."
    assert coordinator.state.last_verified_result
    assert coordinator.state.pending_verification == []


def test_interruption_and_resume_restore_the_suspended_goal(tmp_path):
    coordinator = CognitiveOrchestrator(tmp_path, registry=DEFAULT_REGISTRY)
    coordinator.state.current_goal = "настроить локальный проект"
    coordinator.state.active_task = "применить конфигурацию"
    coordinator.state.mission_state = "executing"

    coordinator.suspend_current()
    unrelated = coordinator.begin_interaction("Как настроение?", implicit_address=True)
    resumed = coordinator.begin_interaction("ладно, продолжай", implicit_address=True)

    assert unrelated.action == "conversation"
    assert resumed.action == "continue"
    assert resumed.goal == "настроить локальный проект"
    assert coordinator.state.active_task == "применить конфигурацию"


def test_speech_boundary_hides_raw_internal_details(tmp_path):
    coordinator = CognitiveOrchestrator(tmp_path, registry=DEFAULT_REGISTRY)
    raw = "Provider Qwen вернул HTTP 503 model_error traceback"

    spoken = coordinator.speech_text(raw)

    assert spoken == sanitize_for_tts(raw, fallback="")
    assert "503" not in spoken and "Qwen" not in spoken and "traceback" not in spoken.casefold()


def test_medium_risk_plan_waits_for_confirmation(tmp_path):
    class Planner:
        def plan(self, goal, desired_state=None):
            return ExecutionPlan(goal, "composed", desired_state or {"changed": True},
                                 steps=[ExecutionStep("change", "write_file")],
                                 confidence=0.99, risk_class="medium")

    coordinator = CognitiveOrchestrator(
        tmp_path, registry=DEFAULT_REGISTRY, capability_planner=Planner(),
    )

    turn = coordinator.begin_interaction("Измени системную настройку", implicit_address=True)

    assert turn.action == "confirm"
    assert turn.response == "Мне потребуется ваше подтверждение."
