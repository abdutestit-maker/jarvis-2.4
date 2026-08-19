from __future__ import annotations

from pathlib import Path

from core.cognitive_kernel import (
    CapabilityGraph,
    CapabilityManifest,
    CognitiveKernel,
    EvidenceRecordV2,
)
from core.research_gateway import ResearchGateway, ResearchResult


def test_unknown_capability_becomes_resumable_research_task(tmp_path: Path):
    kernel = CognitiveKernel(tmp_path)
    handle = kernel.submit("сделай новую локальную задачу")

    outcome = kernel.run(handle.id, capability="not_registered")

    assert outcome.success is False
    assert outcome.action_taken is False
    assert outcome.blocked_reason == "CAPABILITY_RESEARCH_REQUIRED"
    mission = kernel.ledger.load(handle.id)
    assert mission is not None
    assert mission.status == "research_pending"
    assert kernel.explain_decision(handle.id).selected_capability == "capability research"
    kernel.close()


def test_executor_requires_verified_outcome_and_records_evidence(tmp_path: Path):
    graph = CapabilityGraph([CapabilityManifest(name="fixture", intent_families=("operate",))])
    kernel = CognitiveKernel(tmp_path, capability_graph=graph)

    def executor(*, mission, cancel):
        return {
            "success": True,
            "action_taken": True,
            "verified_fields": {"fixture": "ready"},
        }

    kernel.register_executor("fixture", executor)
    handle = kernel.submit("запусти тестовую операцию")
    outcome = kernel.run(handle.id, capability="fixture")

    assert outcome.success is True
    assert outcome.ok is True
    assert outcome.mission_id == handle.id
    assert kernel.ledger.load(handle.id).status == "verified"
    kernel.close()


def test_submit_reuses_idempotency_key_and_task_contract(tmp_path: Path):
    kernel = CognitiveKernel(tmp_path)
    first = kernel.submit("подготовь отчёт", context={"idempotency_key": "ws-42"})
    second = kernel.submit("подготовь отчёт", context={"idempotency_key": "ws-42"})
    assert second.id == first.id
    assert second.task_id == first.task_id
    assert len(kernel.ledger.events(first.id)) == 2
    kernel.close()


def test_semantic_undo_requires_and_runs_explicit_rollback_executor(tmp_path: Path):
    kernel = CognitiveKernel(tmp_path)
    handle = kernel.submit("изменить настройку")
    mission = kernel.ledger.load(handle.id)
    assert mission is not None
    mission.rollback_plan = {"capability": "restore_fixture", "expected_state": {"theme": "Light"}}
    kernel.ledger.save(mission, event_type="mission.rollback_declared")
    kernel.register_rollback_executor("restore_fixture", lambda **_: {
        "success": True, "action_taken": True, "verified_fields": {"theme": "Light"}
    })
    outcome = kernel.undo(handle.id)
    assert outcome.success is True
    assert outcome.action_taken is True
    assert kernel.ledger.load(handle.id).status == "rolled_back"
    kernel.close()


def test_ledger_redacts_secrets_from_evidence(tmp_path: Path):
    kernel = CognitiveKernel(tmp_path)
    handle = kernel.submit("проверь token: SUPER_SECRET")
    evidence = EvidenceRecordV2(
        claim="token: SUPER_SECRET was observed",
        source="fixture",
        expected_state={"password": "password: SECRET"},
        observed_state={"api_key": "api_key=SECRET"},
    )
    kernel.record_evidence(handle.id, evidence)

    payload = kernel.ledger.events(handle.id)[-1]["payload"]
    raw = str(payload)
    assert "SUPER_SECRET" not in raw
    assert "SECRET" not in raw
    assert "[REDACTED]" in raw
    kernel.close()


def test_cancel_stops_before_mutation(tmp_path: Path):
    kernel = CognitiveKernel(tmp_path)
    handle = kernel.submit("создай файл")
    result = kernel.cancel(handle.id, reason="user_cancelled")
    assert result.cancelled is True
    assert result.stopped_before_mutation is True
    assert kernel.ledger.load(handle.id).status == "cancelled"
    kernel.close()


def test_research_gateway_preserves_offline_pending_shape(tmp_path: Path):
    class Engine:
        def run(self, query):
            from core.research import ResearchReport
            return ResearchReport(query=query, status="research_pending", resume_task_id="research-fixture")

    from config.settings import Settings
    gateway = ResearchGateway(Settings(data_dir=tmp_path), engine=Engine())
    result = gateway.search("найди официальный источник")
    assert result.to_dict()["status"] == "research_pending"
    assert result.to_dict()["query"] == "найди официальный источник"
    assert result.resume_task_id == "research-fixture"
    assert gateway.resume("research-fixture").status == "research_pending"


def test_research_gateway_persists_resume_handle_across_instances(tmp_path: Path):
    class Engine:
        def run(self, query):
            from core.research import ResearchReport
            return ResearchReport(query=query, status="research_pending", resume_task_id="research-persisted")

    from config.settings import Settings
    first = ResearchGateway(Settings(data_dir=tmp_path), engine=Engine())
    first.search("offline fixture")
    second = ResearchGateway(Settings(data_dir=tmp_path), engine=Engine())
    resumed = second.resume("research-persisted")
    assert resumed.status == "research_pending"
    assert resumed.query == "offline fixture"
