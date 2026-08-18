"""Integrated living intelligence, persistent PREPARE work and proactive verification."""

from __future__ import annotations

from pathlib import Path

from core.living.models import AutonomyLevel, ComputerAssistanceLevel, ProactiveAction
from core.living.proactive import AttentionSnapshot, ProactiveCandidate
from core.living.resources import ResourceSnapshot
from core.living.service import LivingIntelligence
from core.task_runtime import MissionStatus, TaskRuntime


def _candidate(**overrides) -> ProactiveCandidate:
    data = {
        "id": "prepare_export",
        "topic": "export workflow",
        "opportunity": "prepare repeated export workflow",
        "confidence": 0.92,
        "expected_value": 0.9,
        "reversible": True,
        "risk": "low",
        "ambiguity": 0.05,
        "evidence": ["four semantic runs", "three successful outcomes"],
        "can_prepare": True,
    }
    data.update(overrides)
    return ProactiveCandidate(**data)


def test_prepare_mission_retries_temporary_provider_error_and_persists(tmp_path: Path) -> None:
    runtime = TaskRuntime(persistence_dir=tmp_path / "missions")
    intelligence = LivingIntelligence(tmp_path / "living", task_runtime=runtime)
    calls = []

    def prepare():
        calls.append(True)
        if len(calls) == 1:
            raise RuntimeError("temporary provider error")
        return {"verified": True, "capability": "workflow_export"}

    mission = intelligence.schedule_prepare(
        _candidate(), prepare,
        resources=ResourceSnapshot(cpu_percent=5, ram_percent=20),
    )
    completed = runtime.wait(mission.task_id, timeout=5) if mission else None

    assert completed is not None
    assert completed.status is MissionStatus.COMPLETED
    assert len(calls) == 2
    assert list((tmp_path / "missions").glob("*.json"))


def test_shadow_prepare_is_queued_when_background_budget_is_paused(tmp_path: Path) -> None:
    intelligence = LivingIntelligence(tmp_path / "living")

    mission = intelligence.schedule_prepare(
        _candidate(), lambda: {"verified": True},
        resources=ResourceSnapshot(cpu_percent=95, gaming=True, fullscreen=True),
    )
    pending = intelligence.shadow_backlog.next(cpu_percent=5, gpu_percent=0, gaming=False)

    assert mission is None
    assert pending is not None
    assert pending.id == "prepare_export"


def test_busy_proactive_cycle_prepares_without_foreground_message(tmp_path: Path) -> None:
    intelligence = LivingIntelligence(tmp_path / "living")
    prepared = []

    cycle = intelligence.proactive_cycle(
        _candidate(), AttentionSnapshot(fullscreen=True, media_active=True),
        resources=ResourceSnapshot(cpu_percent=5, ram_percent=20),
        prepare=lambda: prepared.append(True) or {"verified": True},
    )
    mission = cycle.mission
    if mission:
        intelligence.task_runtime.wait(mission.task_id, timeout=5)

    assert cycle.decision.action is ProactiveAction.PREPARE
    assert cycle.decision.user_message == ""
    assert prepared == [True]


def test_proactive_act_uses_checkpoint_observation_and_rollback(tmp_path: Path) -> None:
    intelligence = LivingIntelligence(tmp_path / "living")
    intelligence.profile_store.update(autonomy=AutonomyLevel.PARTNER)
    state = {"organized": False}
    rolled_back = []
    candidate = _candidate(can_prepare=False)

    failed = intelligence.execute_proactive(
        candidate, AttentionSnapshot(), desired_state={"organized": True},
        checkpoint=lambda: dict(state), executor=lambda: True,
        observer=lambda: dict(state),
        rollback=lambda checkpoint: rolled_back.append(checkpoint) or True,
    )
    state["organized"] = True
    passed = intelligence.execute_proactive(
        candidate, AttentionSnapshot(), desired_state={"organized": True},
        checkpoint=lambda: dict(state), executor=lambda: True,
        observer=lambda: dict(state),
        rollback=lambda checkpoint: rolled_back.append(checkpoint) or True,
    )

    assert failed.verified is False
    assert failed.rolled_back is True
    assert passed.verified is True
    assert rolled_back


def test_beginner_help_calls_existing_operator_capability(tmp_path: Path) -> None:
    intelligence = LivingIntelligence(tmp_path / "living")
    intelligence.profile_store.update(assistance=ComputerAssistanceLevel.BEGINNER)
    called = []

    result = intelligence.assist(
        "Я скачал программу, не понимаю, как её установить.",
        capability_available=True,
        operator=lambda request: called.append(request) or {"verified": True},
    )

    assert result.executed is True
    assert result.verified is True
    assert called
    assert len(result.message.split()) < 15


def test_shadow_quality_feedback_enters_ranked_backlog(tmp_path: Path) -> None:
    intelligence = LivingIntelligence(tmp_path / "living")

    quality = intelligence.record_capability_outcome(
        "workflow_export", verified=False, duration=20,
        expected_duration=3, repairs=2, fallbacks=1,
    )

    assert quality.optimization_needed is True
    assert intelligence.shadow_backlog.next(cpu_percent=5, gpu_percent=0,
                                             gaming=False) is not None


def test_shadow_engine_keeps_explicit_empty_registry(tmp_path: Path) -> None:
    from core.actions.registry import ToolRegistry
    from core.shadow import ShadowEngine

    registry = ToolRegistry()
    engine = ShadowEngine(data_dir=tmp_path, registry=registry, enabled=True)

    assert engine.registry is registry

def test_clipboard_metadata_requires_permission_and_drops_values(tmp_path: Path) -> None:
    service = LivingIntelligence(tmp_path)

    denied = service.observe_clipboard_metadata({"type": "text", "value": "TOKEN"}, permission=False)
    accepted = service.observe_clipboard_metadata(
        {"type": "text", "format": "unicode", "size": 5, "value": "TOKEN"},
        permission=True,
    )

    assert denied is False
    assert accepted is True
    stored = service.context.observations[-1]
    assert stored.clipboard_metadata == {"type": "text", "format": "unicode", "size": 5}
    assert "TOKEN" not in str(stored)


def test_service_answers_all_declared_context_questions_without_invention(tmp_path: Path) -> None:
    service = LivingIntelligence(tmp_path)
    service.observe_action(
        action="prepare_capability", outcome="success", source="shadow_engine",
        metadata={"workflow": "organize reports", "goal_hint": "organize reports"},
    )

    assert service.answer_context("чему ты научился?")["known"] is True
    assert service.answer_context("что ты делал пока меня не было?")["known"] is True
    assert service.answer_context("обычный вопрос") is None

def test_service_derives_proactive_candidate_from_verified_workflow(tmp_path: Path) -> None:
    from core.living.workflow import SemanticAction, WorkflowRun

    service = LivingIntelligence(tmp_path)
    for index in range(4):
        service.observe_workflow(WorkflowRun(
            f"run-{index}",
            [SemanticAction("move", "file", "incoming report", "filesystem.move", {
                "source": f"in-{index}", "destination": f"out-{index}",
            })],
            duration_seconds=30, estimated_automated_seconds=2,
            success=True, desired_state={"organized": True},
            observed_state={"organized": True},
        ))

    candidates = service.opportunity_candidates()

    assert candidates
    assert candidates[0].evidence
    assert candidates[0].can_prepare is True
    assert candidates[0].risk == "low"

def test_proactive_execution_rolls_back_when_executor_raises(tmp_path: Path) -> None:
    service = LivingIntelligence(tmp_path)
    service.profile_store.update(autonomy=AutonomyLevel.PARTNER)
    candidate = _candidate(id="exceptional-act", confidence=0.96, expected_value=0.9)
    restored = []

    def broken():
        raise RuntimeError("provider crashed")

    result = service.execute_proactive(
        candidate, AttentionSnapshot(), desired_state={"done": True},
        checkpoint=lambda: "checkpoint", executor=broken,
        observer=lambda: {"done": False}, rollback=lambda saved: restored.append(saved) or True,
    )

    assert result.executed is True
    assert result.verified is False
    assert result.rolled_back is True
    assert restored == ["checkpoint"]
    assert any("provider crashed" in item for item in result.evidence)

def test_mission_event_feeds_structured_goal_and_active_state(tmp_path: Path) -> None:
    from core.task_runtime import TaskEvent

    service = LivingIntelligence(tmp_path)
    service.observe_mission_event(TaskEvent(
        task_id="JARVIS-2026-9", event_type="task_started",
        phase="executing", payload={"goal": "prepare catalog"},
    ))

    stored = service.context.observations[-1]
    assert stored.source == "mission_runtime"
    assert stored.active_mission is True
    assert stored.metadata["mission_goal"] == "prepare catalog"


def test_throttled_prepare_records_cooperative_resource_budget(tmp_path: Path) -> None:
    service = LivingIntelligence(tmp_path)
    mission = service.schedule_prepare(
        _candidate(topic="throttle"), lambda: {"verified": True},
        resources=ResourceSnapshot(cpu_percent=50, ram_percent=60, active_tts=True),
    )

    assert mission is not None
    assert mission.metadata["background_mode"] == "THROTTLE"
    assert mission.metadata["cpu_quota"] > 0
    service.task_runtime.wait(mission.task_id, timeout=5)
