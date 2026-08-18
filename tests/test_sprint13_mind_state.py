from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from core.cognitive import (
    ContinuityResolver,
    CurrentMindState,
    GoalFrame,
    GoalStack,
    MindStateStore,
)
from core.task_runtime import Mission, MissionStatus, TaskRuntime


BASE = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)


def test_current_mind_state_is_structured_and_contains_no_reasoning_fields():
    state = CurrentMindState(
        current_goal="настроить проект", active_task="configuration",
        subgoals=["inspect", "apply", "verify"],
        relevant_context_refs=["context:episode-1"],
        recalled_memory_refs=["relationship:style"],
        current_app="Editor", mission_state="executing",
        attention_state="available", uncertainties=["target version"],
        pending_verification=["config.enabled=true"],
        interaction_mode="work", confidence=0.82,
    )

    payload = state.to_safe_dict()

    assert payload["current_goal"] == "настроить проект"
    assert payload["pending_verification"] == ["config.enabled=true"]
    assert not ({"reasoning", "chain_of_thought", "thoughts", "scratchpad"} & set(payload))


def test_mind_state_persists_only_continuity_fields(tmp_path):
    store = MindStateStore(tmp_path)
    state = CurrentMindState(
        current_goal="подготовить отчёт", active_task="report",
        current_app="Private Window", attention_state="busy",
        relevant_context_refs=["context:42"], confidence=0.9,
    )

    store.save(state)
    raw = json.loads(store.path.read_text(encoding="utf-8"))
    restored = store.load()

    assert "current_app" not in raw
    assert "attention_state" not in raw
    assert restored.current_goal == "подготовить отчёт"
    assert restored.current_app == ""


def test_mind_state_privacy_filter_removes_secret_values(tmp_path):
    store = MindStateStore(tmp_path)
    store.save(CurrentMindState(
        current_goal="проверить password=super-secret",
        last_verified_result="token=raw-secret",
        pending_user_question="api_key=private-value",
    ))

    raw = store.path.read_text(encoding="utf-8")

    assert "super-secret" not in raw
    assert "raw-secret" not in raw
    assert "private-value" not in raw


def test_public_mind_state_view_redacts_secret_values():
    payload = CurrentMindState(
        current_goal="проверить password=super-secret",
        last_verified_result="token=raw-secret",
    ).to_safe_dict()

    serialized = json.dumps(payload, ensure_ascii=False)
    assert "super-secret" not in serialized
    assert "raw-secret" not in serialized


def test_goal_stack_is_bounded_and_prunes_stale_goals(tmp_path):
    stack = GoalStack(tmp_path, max_depth=3, ttl_days=2)
    for index in range(5):
        stack.suspend(GoalFrame(
            goal_id=f"g-{index}", goal=f"task {index}",
            updated_at=(BASE + timedelta(hours=index)).isoformat(),
        ), now=BASE + timedelta(hours=index))
    stack.suspend(GoalFrame(
        goal_id="stale", goal="old task",
        updated_at=(BASE - timedelta(days=5)).isoformat(),
    ), now=BASE)

    frames = stack.frames(now=BASE + timedelta(hours=5))

    assert len(frames) == 3
    assert {frame.goal for frame in frames} == {"task 2", "task 3", "task 4"}


def test_unique_continuation_resumes_suspended_goal(tmp_path):
    stack = GoalStack(tmp_path)
    stack.suspend(GoalFrame(goal_id="install", goal="установить тестовую программу"), now=BASE)
    resolver = ContinuityResolver(stack)

    result = resolver.resolve("ладно, продолжай", CurrentMindState(), now=BASE)

    assert result.action == "continue"
    assert result.goal == "установить тестовую программу"
    assert result.confidence >= 0.8


def test_ambiguous_continuation_asks_one_concise_question(tmp_path):
    stack = GoalStack(tmp_path)
    stack.suspend(GoalFrame(goal_id="a", goal="настроить редактор"), now=BASE)
    stack.suspend(GoalFrame(goal_id="b", goal="подготовить отчёт"), now=BASE)

    result = ContinuityResolver(stack).resolve("продолжай", CurrentMindState(), now=BASE)

    assert result.action == "clarify"
    assert result.goal == ""
    assert result.question.count("?") == 1
    assert "редактор" in result.question and "отчёт" in result.question


def test_specific_continuation_selects_matching_goal(tmp_path):
    stack = GoalStack(tmp_path)
    stack.suspend(GoalFrame(goal_id="install", goal="установка редактора"), now=BASE)
    stack.suspend(GoalFrame(goal_id="report", goal="подготовка отчёта"), now=BASE)

    result = ContinuityResolver(stack).resolve(
        "что там с установкой?", CurrentMindState(), now=BASE,
    )

    assert result.action == "status"
    assert result.goal == "установка редактора"


def test_restart_reconstructs_useful_state_from_mission_and_living_context(tmp_path):
    mission_dir = tmp_path / "missions"
    runtime = TaskRuntime(persistence_dir=mission_dir)
    runtime.restore_mission(Mission(
        task_id="JARVIS-2026-001", goal="настроить редактор",
        status=MissionStatus.PAUSED, current_step="apply theme",
        verification={"verified": False},
    ))
    reloaded_runtime = TaskRuntime(persistence_dir=mission_dir)
    living = SimpleNamespace(current=SimpleNamespace(
        active_application="Editor", user_busy=True,
    ))

    state = MindStateStore(tmp_path / "mind").reconstruct(
        task_runtime=reloaded_runtime, living_context=living,
    )

    assert state.current_goal == "настроить редактор"
    assert state.active_task == "apply theme"
    assert state.mission_state == "paused"
    assert state.current_app == "Editor"
    assert state.attention_state == "busy"


def test_restart_uses_high_confidence_living_goal_when_no_mission(tmp_path):
    living = SimpleNamespace(current=SimpleNamespace(
        active_application="Editor", user_busy=False,
        goal="подготовить релиз", goal_confidence=0.88,
        evidence=["repeated semantic actions"],
    ))

    state = MindStateStore(tmp_path).reconstruct(living_context=living)

    assert state.current_goal == "подготовить релиз"
    assert state.confidence == 0.88
    assert state.relevant_context_refs == ["living:goal"]


def test_only_verified_result_becomes_last_verified_result(tmp_path):
    store = MindStateStore(tmp_path)
    state = CurrentMindState(current_goal="apply setting")

    store.observe_result(state, result="ActionResult.ok", verified=False,
                         pending=["setting.enabled=true"])
    assert state.last_verified_result == ""
    assert state.pending_verification == ["setting.enabled=true"]

    store.observe_result(state, result="setting.enabled=true", verified=True)
    assert state.last_verified_result == "setting.enabled=true"
    assert state.pending_verification == []
    assert store.recent_verified(limit=1)[0].result == "setting.enabled=true"
