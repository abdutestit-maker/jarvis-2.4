"""Semantic workflow discovery, generalization and Capability integration."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.actions.registry import DEFAULT_REGISTRY
from core.capability_engine import CapabilityCatalog, CapabilityEngine, CapabilityKind
from core.living.workflow import (
    SemanticAction,
    WorkflowCapabilityBridge,
    WorkflowExecutor,
    WorkflowLearner,
    WorkflowRun,
)


def _run(index: int, *, success: bool = True) -> WorkflowRun:
    return WorkflowRun(
        run_id=f"run-{index}",
        actions=[
            SemanticAction("discover", "folder", "inbox", "filesystem.list"),
            SemanticAction("move", "file", "newest report", "filesystem.move",
                           {"source": f"report-{index}.txt", "destination": "project/report.txt"}),
            SemanticAction("rename", "file", "project report", "filesystem.rename",
                           {"name": f"catalog-{index}.txt"}),
        ],
        duration_seconds=30 + index,
        estimated_automated_seconds=3,
        success=success,
        desired_state={"organized": True},
        observed_state={"organized": success},
    )


def test_workflow_discovery_generalizes_similar_semantic_sequences(tmp_path: Path) -> None:
    learner = WorkflowLearner(tmp_path)
    for index in range(4):
        learner.observe(_run(index))

    candidate = learner.discover()[0]

    assert candidate.frequency == 4
    assert candidate.similarity >= 0.9
    assert candidate.reliability == 1.0
    assert candidate.confidence >= 0.75
    assert candidate.actions[1].parameters["source"] == {"$slot": "source"}
    assert candidate.actions[2].parameters["name"] == {"$slot": "name"}
    assert "coordinate" not in str(candidate).lower()


def test_workflow_learning_rejects_coordinate_macros(tmp_path: Path) -> None:
    learner = WorkflowLearner(tmp_path)
    run = WorkflowRun(
        "coords", [SemanticAction("click", "button", "save", "uia", {"x": 10, "y": 20})],
    )

    with pytest.raises(ValueError, match="semantic"):
        learner.observe(run)


def test_unreliable_workflow_stays_below_learning_threshold(tmp_path: Path) -> None:
    learner = WorkflowLearner(tmp_path)
    learner.observe(_run(1, success=False))
    learner.observe(_run(2, success=False))
    learner.observe(_run(3, success=True))

    candidate = learner.discover()[0]

    assert candidate.reliability < 0.5
    assert candidate.ready is False


def test_workflow_becomes_capability_only_after_verified_rehearsal(tmp_path: Path) -> None:
    learner = WorkflowLearner(tmp_path / "workflows")
    for index in range(4):
        learner.observe(_run(index))
    candidate = learner.discover()[0]
    catalog = CapabilityCatalog(tmp_path / "capabilities")
    bridge = WorkflowCapabilityBridge(catalog)

    rejected = bridge.rehearse(candidate, lambda _candidate: {"verified": False})
    accepted = bridge.rehearse(candidate, lambda _candidate: {
        "verified": True, "observed": {"organized": True}, "duration": 2.5,
    })

    assert rejected is None
    assert accepted is not None
    assert accepted.kind is CapabilityKind.LEARNED
    assert catalog.get(accepted.id) is not None
    assert catalog.retrieve_episodes("organize inbox report")


def test_workflow_executor_observes_desired_state_instead_of_trusting_calls(tmp_path: Path) -> None:
    state = {"organized": False}
    calls = []
    providers = {
        "filesystem.list": lambda action, params: calls.append(action.verb) or True,
        "filesystem.move": lambda action, params: calls.append(action.verb) or True,
        "filesystem.rename": lambda action, params: calls.append(action.verb) or True,
    }
    learner = WorkflowLearner(tmp_path)
    for index in range(4):
        learner.observe(_run(index))
    candidate = learner.discover()[0]
    executor = WorkflowExecutor(providers, observer=lambda: dict(state))

    failed = executor.execute(candidate, slots={"source": "in.txt", "name": "out.txt"})
    state["organized"] = True
    passed = executor.execute(candidate, slots={"source": "in.txt", "name": "out.txt"})

    assert failed.verified is False
    assert passed.verified is True
    assert calls


def test_workflow_runs_reload_for_second_process_reuse(tmp_path: Path) -> None:
    first = WorkflowLearner(tmp_path)
    for index in range(4):
        first.observe(_run(index))

    second = WorkflowLearner(tmp_path)
    candidates = second.discover()

    assert candidates
    assert candidates[0].frequency == 4
    assert candidates[0].ready

def test_workflow_executor_requires_accepted_actions_even_if_state_already_matches(tmp_path: Path) -> None:
    learner = WorkflowLearner(tmp_path)
    for index in range(4):
        learner.observe(_run(index))
    candidate = learner.discover()[0]
    executor = WorkflowExecutor(
        {"filesystem.list": lambda *_args: {"ok": False}},
        observer=lambda: {"organized": True},
    )

    result = executor.execute(candidate)

    assert result.verified is False
    assert "workflow_actions" in result.missing
    assert any(not item["accepted"] for item in result.action_results)


def test_workflow_executor_contains_provider_exception_and_does_not_verify(tmp_path: Path) -> None:
    learner = WorkflowLearner(tmp_path)
    for index in range(4):
        learner.observe(_run(index))
    candidate = learner.discover()[0]

    def broken(*_args):
        raise RuntimeError("temporary provider failure")

    result = WorkflowExecutor(
        {"filesystem.list": broken, "filesystem.move": broken, "filesystem.rename": broken},
        observer=lambda: {"organized": True},
    ).execute(candidate)

    assert result.verified is False
    assert any("temporary provider failure" in item.get("error", "")
               for item in result.action_results)
