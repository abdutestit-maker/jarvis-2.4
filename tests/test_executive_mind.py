from __future__ import annotations

from datetime import datetime, timedelta, timezone

from core.executive import (
    AskOncePolicy,
    CommandOS,
    CommandPrimitive,
    CommitmentEngine,
    ExecutiveMind,
    GoalGraph,
    GoalStatus,
    PersonalEvalLab,
    ShadowRehearsal,
    TemporalMemory,
)
from core.executive.models import EvalCase
from core.executive.store import ExecutiveStore


def test_goal_graph_dependencies_and_resume(tmp_path):
    graph = GoalGraph(tmp_path / "executive")
    first = graph.add("подготовить отчёт", priority=0.9)
    second = graph.add("отправить отчёт", dependencies=[first.id], priority=1.0)
    assert graph.blockers(second) == [first.id]
    assert graph.resume().id == first.id
    graph.mark(first.id, GoalStatus.COMPLETED, verified=True)
    assert graph.resume().id == second.id


def test_command_os_compiles_verified_pipeline(tmp_path):
    plan = CommandOS.compile("открой блокнот", intent="app", tool="open_app",
                             args={"name": "блокнот"}, desired_state={"process": "notepad"})
    assert plan.steps[0].primitive is CommandPrimitive.OBSERVE
    assert CommandPrimitive.VERIFY in [step.primitive for step in plan.steps]
    assert ShadowRehearsal().rehearse(plan).ready


def test_commitment_and_temporal_memory_are_persistent(tmp_path):
    store = ExecutiveStore(tmp_path / "executive")
    commitments = CommitmentEngine(store)
    item = commitments.observe("Не забудь отправить отчёт завтра")[0]
    assert item.due_at and item.status.value == "open"
    assert CommitmentEngine(store).open()[0].text == item.text

    memory = TemporalMemory(store)
    memory.remember("предпочитает короткие ответы", source="user", confidence=0.9)
    assert memory.current("короткие")[0]["confidence"] == 0.9
    memory.remember("старое правило", source="test", valid_until=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat())
    assert memory.expire() == 1


def test_executive_mind_learning_and_eval(tmp_path):
    mind = ExecutiveMind(tmp_path / "executive")
    mind.demonstrations.start("утренний отчёт")
    mind.demonstrations.observe("find", target="email", parameters={"folder": "inbox"})
    workflow = mind.demonstrations.finish(verify=True)
    assert workflow.confidence >= 0.8
    result = mind.complete_turn("утренний отчёт", verified=True, tool="current_time", result="ok")
    assert result["verified"] is True
    assert mind.evals.summary()["verified"] == 1


def test_ask_once_and_relevance(tmp_path):
    ask = AskOncePolicy()
    question = ask.choose(["какой каталог использовать", "какой каталог использовать"], observations={})
    assert question
    assert ask.choose([question]) is None

