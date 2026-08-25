from __future__ import annotations

import threading
import json
from datetime import datetime, timedelta, timezone

from core.executive import FactType, WorldFact
from core.actions.base import ToolContext
from core.actions.reminders import AddReminderTool
from core.task_runtime import (
    MissedTriggerPolicy,
    MissionStatus,
    MissionTrigger,
    TaskRuntime,
)
from core.verifier import verify_action_result


class Clock:
    def __init__(self) -> None:
        self.current = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += timedelta(seconds=seconds)


def verified_runner(calls: list[str]):
    def run(mission, cancel):
        calls.append(mission.task_id)
        mission.verification = {"verified": True, "method": "fixture"}
        return "verified"

    return run


def fire(runtime: TaskRuntime, task_id: str):
    runtime.run_scheduler_once()
    return runtime.wait(task_id, timeout=2)


def test_time_commitment_fires_at_injected_clock_time_without_real_sleep(tmp_path, monkeypatch):
    clock = Clock()
    calls: list[str] = []
    runtime = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=verified_runner(calls),
    )
    mission = runtime.schedule(
        "future fixture", MissionTrigger.at(clock() + timedelta(seconds=60))
    )
    monkeypatch.setattr("core.task_runtime.time.sleep", lambda *_: (_ for _ in ()).throw(AssertionError("sleep")))

    runtime.run_scheduler_once()
    assert calls == []
    clock.advance(60)
    completed = fire(runtime, mission.task_id)

    assert calls == [mission.task_id]
    assert completed.status is MissionStatus.COMPLETED


def test_waiting_commitment_survives_runtime_restart(tmp_path):
    clock = Clock()
    first = TaskRuntime(persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False)
    mission = first.schedule("restart fixture", MissionTrigger.at(clock() + timedelta(seconds=30)))
    first.stop_scheduler()

    calls: list[str] = []
    restored = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=verified_runner(calls),
    )
    clock.advance(30)
    completed = fire(restored, mission.task_id)

    assert completed.status is MissionStatus.COMPLETED
    assert calls == [mission.task_id]


def test_cancelled_commitment_never_executes_or_resurrects(tmp_path):
    clock = Clock()
    calls: list[str] = []
    runtime = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=verified_runner(calls),
    )
    mission = runtime.schedule("cancel fixture", MissionTrigger.at(clock() + timedelta(seconds=5)))
    assert runtime.cancel(mission.task_id)
    clock.advance(10)
    runtime.run_scheduler_once()
    assert calls == []

    restored = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=verified_runner(calls),
    )
    restored.run_scheduler_once()
    assert restored.get(mission.task_id).status is MissionStatus.CANCELLED
    assert calls == []


def test_paused_commitment_waits_and_resume_restores_execution(tmp_path):
    clock = Clock()
    calls: list[str] = []
    runtime = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=verified_runner(calls),
    )
    mission = runtime.schedule("pause fixture", MissionTrigger.at(clock() + timedelta(seconds=5)))
    assert runtime.pause(mission.task_id)
    clock.advance(10)
    runtime.run_scheduler_once()
    assert calls == []
    assert mission.status is MissionStatus.PAUSED

    assert runtime.resume(mission.task_id)
    completed = fire(runtime, mission.task_id)
    assert completed.status is MissionStatus.COMPLETED
    assert calls == [mission.task_id]


class FakeWorld:
    def __init__(self, fact: WorldFact) -> None:
        self.fact = fact
        self.calls = 0

    def observe_domain(self, domain: str, *, force: bool = False, **options):
        self.calls += 1
        return self.fact


def condition_fact(clock: Clock, *, fresh: bool, exists: bool = True) -> WorldFact:
    return WorldFact(
        key="world.filesystem.fixture", value={"exists": exists}, source="fixture_os",
        observed_at=clock().isoformat(),
        valid_until=(clock() + timedelta(seconds=5 if fresh else -1)).isoformat(),
        domain="filesystem", fact_type=FactType.OBSERVED.value,
        evidence=["fixture probe"], ephemeral=True,
    )


def test_world_condition_requires_fresh_observed_fact(tmp_path):
    clock = Clock()
    calls: list[str] = []
    world = FakeWorld(condition_fact(clock, fresh=True))
    runtime = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=verified_runner(calls), world_state=world,
    )
    mission = runtime.schedule(
        "world fixture",
        MissionTrigger.condition("filesystem", "exists", "equals", True, poll_interval_sec=10),
    )

    completed = fire(runtime, mission.task_id)

    assert completed.status is MissionStatus.COMPLETED
    assert calls == [mission.task_id]
    assert completed.latest_evidence["fact_type"] == "observed"


def test_stale_world_fact_cannot_trigger(tmp_path):
    clock = Clock()
    calls: list[str] = []
    world = FakeWorld(condition_fact(clock, fresh=False))
    runtime = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=verified_runner(calls), world_state=world,
    )
    mission = runtime.schedule(
        "stale fixture",
        MissionTrigger.condition("filesystem", "exists", "equals", True, poll_interval_sec=10),
    )

    runtime.run_scheduler_once()

    assert mission.status is MissionStatus.WAITING
    assert calls == []


def test_world_change_wakes_only_targeted_domain_and_supports_none_match(tmp_path):
    clock = Clock()
    calls: list[str] = []
    fact = WorldFact(
        key="world.processes", value={"processes": [{"name": "other.exe"}]},
        source="fixture_os", observed_at=clock().isoformat(),
        valid_until=(clock() + timedelta(seconds=5)).isoformat(),
        domain="processes", fact_type=FactType.OBSERVED.value,
        evidence=["fixture process list"], ephemeral=True,
    )
    runtime = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=verified_runner(calls), world_state=FakeWorld(fact),
    )
    mission = runtime.schedule(
        "wait for process close",
        MissionTrigger.condition(
            "processes", "processes", "none_match", {"name": "target.exe"},
            poll_interval_sec=60,
        ),
    )

    assert runtime.notify_world_changed("storage") == 0
    assert runtime.notify_world_changed("processes") == 1
    assert fire(runtime, mission.task_id).status is MissionStatus.COMPLETED
    assert calls == [mission.task_id]


def test_duplicate_trigger_executes_exactly_once(tmp_path):
    clock = Clock()
    calls: list[str] = []
    runtime = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=verified_runner(calls),
    )
    mission = runtime.schedule("dedupe fixture", MissionTrigger.event("download_finished"))

    assert runtime.notify_event("download_finished", {}, event_id="event-1") == 1
    assert runtime.notify_event("download_finished", {}, event_id="event-1") == 0
    completed = runtime.wait(mission.task_id, timeout=2)

    assert completed.status is MissionStatus.COMPLETED
    assert calls == [mission.task_id]


def test_completed_commitment_does_not_resurrect_after_restart(tmp_path):
    clock = Clock()
    calls: list[str] = []
    first = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=verified_runner(calls),
    )
    mission = first.schedule("complete fixture", MissionTrigger.at(clock()))
    assert fire(first, mission.task_id).status is MissionStatus.COMPLETED

    second = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=verified_runner(calls),
    )
    second.run_scheduler_once()

    assert second.get(mission.task_id).status is MissionStatus.COMPLETED
    assert calls == [mission.task_id]


def test_verification_failure_prevents_completed_state(tmp_path):
    clock = Clock()

    def unverified(mission, cancel):
        mission.verification = {"verified": False, "method": "fixture"}
        return "handler returned"

    runtime = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=unverified,
    )
    mission = runtime.schedule("unverified fixture", MissionTrigger.at(clock()))

    finished = fire(runtime, mission.task_id)

    assert finished.status is MissionStatus.FAILED
    assert finished.status is not MissionStatus.COMPLETED


def test_one_scheduler_thread_handles_one_hundred_waiting_tasks(tmp_path):
    clock = Clock()
    runtime = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=verified_runner([]),
    )
    baseline = threading.active_count()
    for index in range(100):
        runtime.schedule(f"future {index}", MissionTrigger.at(clock() + timedelta(hours=1, seconds=index)))

    runtime.start_scheduler()
    try:
        assert threading.active_count() <= baseline + 1
        assert not any(name.startswith("mission-") for name in runtime.runtime_thread_names())
    finally:
        runtime.stop_scheduler()


def test_scheduler_idle_waits_instead_of_busy_loop(tmp_path):
    clock = Clock()
    runtime = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=verified_runner([]), scheduler_poll_sec=60,
    )
    runtime.schedule("far future", MissionTrigger.at(clock() + timedelta(hours=1)))
    runtime.start_scheduler()
    threading.Event().wait(0.05)
    runtime.stop_scheduler()

    assert runtime.scheduler_stats()["wakeups"] <= 2
    assert runtime.scheduler_stats()["executions"] == 0


def test_condition_polling_stops_after_completion_and_cancel(tmp_path):
    clock = Clock()
    calls: list[str] = []
    world = FakeWorld(condition_fact(clock, fresh=True))
    runtime = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=verified_runner(calls), world_state=world,
    )
    completed = runtime.schedule(
        "condition complete",
        MissionTrigger.condition("filesystem", "exists", "equals", True, poll_interval_sec=1),
    )
    assert fire(runtime, completed.task_id).status is MissionStatus.COMPLETED
    observed = world.calls
    clock.advance(10)
    runtime.run_scheduler_once()
    assert world.calls == observed

    cancelled = runtime.schedule(
        "condition cancel",
        MissionTrigger.condition("filesystem", "exists", "equals", True, poll_interval_sec=1),
    )
    runtime.cancel(cancelled.task_id)
    clock.advance(10)
    runtime.run_scheduler_once()
    assert world.calls == observed


def test_manual_trigger_and_schedule_update_are_structured_primitives(tmp_path):
    clock = Clock()
    calls: list[str] = []
    runtime = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=verified_runner(calls),
    )
    mission = runtime.schedule("manual fixture", MissionTrigger.manual())
    runtime.run_scheduler_once()
    assert calls == []
    assert runtime.reschedule(mission.task_id, MissionTrigger.at(clock()))
    assert fire(runtime, mission.task_id).status is MissionStatus.COMPLETED


def test_manual_resume_trigger_executes_paused_mission(tmp_path):
    clock = Clock()
    calls: list[str] = []
    runtime = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=verified_runner(calls),
    )
    mission = runtime.schedule("manual resume", MissionTrigger.manual())
    assert runtime.pause(mission.task_id)

    assert runtime.resume(mission.task_id)
    finished = runtime.wait(mission.task_id, timeout=2)

    assert finished.status is MissionStatus.COMPLETED
    assert calls == [mission.task_id]


def test_missed_mutation_policy_expires_old_trigger(tmp_path):
    clock = Clock()
    calls: list[str] = []
    runtime = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=verified_runner(calls),
    )
    mission = runtime.schedule(
        "old mutation",
        MissionTrigger.at(
            clock() - timedelta(minutes=10),
            missed_policy=MissedTriggerPolicy.EXECUTE_IF_FRESH,
            max_lateness_sec=30,
        ),
    )

    runtime.run_scheduler_once()

    assert mission.status is MissionStatus.EXPIRED
    assert calls == []


def test_late_notification_policy_executes_after_offline_window(tmp_path):
    clock = Clock()
    calls: list[str] = []
    runtime = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=verified_runner(calls),
    )
    mission = runtime.schedule(
        "late reminder",
        MissionTrigger.at(
            clock() - timedelta(hours=1),
            missed_policy=MissedTriggerPolicy.NOTIFY_LATE,
            max_lateness_sec=0,
        ),
    )

    assert fire(runtime, mission.task_id).status is MissionStatus.COMPLETED
    assert calls == [mission.task_id]


def test_interrupted_execution_recovers_paused_without_duplicate_dispatch(tmp_path):
    clock = Clock()
    calls: list[str] = []
    first = TaskRuntime(persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False)
    mission = first.schedule("interrupted", MissionTrigger.at(clock()))
    mission.status = MissionStatus.EXECUTING
    mission.execution_id = "execution-before-restart"
    first.restore_mission(mission)

    restored = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=verified_runner(calls),
    )
    restored.run_scheduler_once()

    assert restored.get(mission.task_id).status is MissionStatus.PAUSED
    assert calls == []


def test_reminder_tool_uses_durable_record_and_independent_verification(tmp_path):
    runtime = TaskRuntime(persistence_dir=tmp_path, auto_start_scheduler=False)
    result = AddReminderTool().run(
        {"text": "fixture reminder", "minutes": 1},
        ToolContext(extra={"task_runtime": runtime}),
    )

    verification = verify_action_result(result)

    assert result.ok is True
    assert result.output["durable"] is True
    assert verification.verified is True
    assert verification.method == "durable_reminder_record"


def test_persistence_contains_data_only_and_redacts_secret_fields(tmp_path):
    clock = Clock()
    runtime = TaskRuntime(persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False)
    mission = runtime.schedule(
        "data-only fixture", MissionTrigger.manual(),
        context={"api_key": "secret-value", "callback": lambda: None},
    )

    stored = json.loads(runtime.persistence_path(mission.task_id).read_text(encoding="utf-8"))

    assert stored["context"]["api_key"] == "[redacted]"
    assert "callback" not in stored["context"]


def test_concurrent_duplicate_event_claims_one_execution(tmp_path):
    clock = Clock()
    calls: list[str] = []
    runtime = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=verified_runner(calls),
    )
    mission = runtime.schedule("event race", MissionTrigger.event("fixture_event"))
    gate = threading.Barrier(8)

    def notify():
        gate.wait()
        runtime.notify_event("fixture_event", {}, event_id="same-event")

    threads = [threading.Thread(target=notify) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2)
    finished = runtime.wait(mission.task_id, timeout=2)

    assert finished.status is MissionStatus.COMPLETED
    assert calls == [mission.task_id]


def test_cancel_race_cannot_turn_cancelled_execution_into_completed(tmp_path):
    clock = Clock()
    started = threading.Event()
    release = threading.Event()

    def cooperative(mission, cancel):
        started.set()
        release.wait(timeout=2)
        mission.verification = {"verified": True, "method": "fixture"}
        return "runner returned after cancellation"

    runtime = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=cooperative,
    )
    mission = runtime.schedule("cancel race", MissionTrigger.at(clock()))
    runtime.run_scheduler_once()
    assert started.wait(timeout=1)
    assert runtime.cancel(mission.task_id)
    release.set()
    finished = runtime.wait(mission.task_id, timeout=2)

    assert finished.status is MissionStatus.CANCELLED


def test_unpersisted_trigger_claim_never_executes_side_effect(tmp_path, monkeypatch):
    clock = Clock()
    calls: list[str] = []
    runtime = TaskRuntime(
        persistence_dir=tmp_path, clock=clock, auto_start_scheduler=False,
        durable_runner=verified_runner(calls), scheduler_poll_sec=10,
    )
    mission = runtime.schedule("persistence failure", MissionTrigger.at(clock()))
    real_persist = runtime._persist

    def fail_claim(current):
        if current.status is MissionStatus.TRIGGERED:
            raise OSError("fixture persistence failure")
        return real_persist(current)

    monkeypatch.setattr(runtime, "_persist", fail_claim)
    runtime.run_scheduler_once()

    assert calls == []
    assert mission.status is MissionStatus.WAITING
    assert mission.execution_id is None
    assert mission.executed_trigger_ids == []
