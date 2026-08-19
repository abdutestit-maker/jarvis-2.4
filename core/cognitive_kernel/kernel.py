"""Canonical intake, mission lifecycle and verified outcome authority."""

from __future__ import annotations

import threading
import uuid
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .capabilities import CapabilityGraph
from .ledger import MissionLedger
from .models import (
    CancellationResult,
    DecisionTrace,
    EvidenceRecordV2,
    MissionHandle,
    MissionRecord,
    TaskContractV2,
    VerificationOutcome,
    utcnow,
)


class CognitiveKernel:
    """Idempotent mission facade that can wrap existing executors."""

    def __init__(
        self,
        root: Path | str,
        *,
        capability_graph: CapabilityGraph | None = None,
        intake: Any | None = None,
    ) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.ledger = MissionLedger(self.root / "missions.db")
        self.capabilities = capability_graph or CapabilityGraph()
        self._intake = intake
        self._executors: dict[str, Callable[..., Any]] = {}
        self._rollback_executors: dict[str, Callable[..., Any]] = {}
        self._cancel: dict[str, threading.Event] = {}
        self._lock = threading.RLock()

    def register_executor(self, name: str, executor: Callable[..., Any]) -> None:
        if not callable(executor):
            raise TypeError("executor must be callable")
        self._executors[str(name)] = executor

    def register_rollback_executor(self, name: str, executor: Callable[..., Any]) -> None:
        """Register the explicit inverse of a capability for semantic undo."""
        if not callable(executor):
            raise TypeError("rollback executor must be callable")
        self._rollback_executors[str(name)] = executor

    def submit(self, text: str, context: Mapping[str, Any] | None = None) -> MissionHandle:
        raw = " ".join(str(text or "").split())
        context_data = dict(context or {})
        requested_mission = str(context_data.get("mission_id", "")).strip()
        if requested_mission:
            existing = self.ledger.load(requested_mission)
            if existing is not None:
                contract = dict(existing.contract)
                return MissionHandle(existing.id, existing.task_id,
                                     str(contract.get("intent_family", "conversation")), existing.status)
        idempotency_key = str(
            context_data.get("idempotency_key") or context_data.get("request_id") or ""
        ).strip()
        if idempotency_key:
            existing = self.ledger.load_by_idempotency(idempotency_key)
            if existing is not None:
                contract = dict(existing.contract)
                return MissionHandle(existing.id, existing.task_id,
                                     str(contract.get("intent_family", "conversation")), existing.status)
        intake = self._intake
        if intake is None:
            from core.intelligence import UniversalIntake
            intake = UniversalIntake()
        legacy = intake.classify(raw, attachments=context_data.get("attachments"))
        contract = TaskContractV2(
            intent_family=legacy.intent_family,
            subject=legacy.subject,
            desired_outcome=legacy.desired_outcome,
            inputs=list(legacy.inputs),
            constraints=list(legacy.constraints),
            risk=legacy.risk,
            mode=legacy.mode,
            confidence=legacy.confidence,
            evidence=list(legacy.evidence),
        )
        mission_id = f"mission-{uuid.uuid4().hex}"
        contract_payload = contract.to_dict()
        if idempotency_key:
            contract_payload["idempotency_key"] = idempotency_key
        mission = MissionRecord(
            id=mission_id,
            task_id=contract.id,
            contract=contract_payload,
            desired_state={"outcome": contract.desired_outcome},
            next_action="resolve capability",
        )
        self.ledger.create(mission)
        self.ledger.save(mission, event_type="contract.created")
        return MissionHandle(mission_id, contract.id, contract.intent_family, mission.status)

    def record_evidence(self, mission_id: str, evidence: EvidenceRecordV2) -> EvidenceRecordV2:
        mission = self._require(mission_id)
        mission.evidence_ids.append(evidence.id)
        mission.checkpoints.append({"type": "evidence", "evidence": evidence.to_dict()})
        self.ledger.save(mission, event_type="evidence.recorded")
        return evidence

    def transition(self, mission_id: str, status: str, **fields: Any) -> MissionRecord:
        mission = self._require(mission_id)
        mission.status = str(status)
        for key in ("desired_state", "observed_state", "next_action", "rollback_plan", "error"):
            if key in fields and fields[key] is not None:
                setattr(mission, key, fields[key])
        if "checkpoint" in fields:
            mission.checkpoints.append(dict(fields["checkpoint"]))
        mission.attempts = int(fields.get("attempts", mission.attempts))
        return self.ledger.save(mission, event_type=f"mission.{mission.status}")

    def run(self, mission_id: str, *, capability: str = "", **kwargs: Any) -> VerificationOutcome:
        mission = self._require(mission_id)
        if mission.status in {"cancelled", "verified"}:
            return VerificationOutcome(mission.status == "verified", mission_id=mission_id)
        self.transition(mission_id, "running", next_action="execute")
        event = self._cancel.setdefault(mission_id, threading.Event())
        if event.is_set():
            return VerificationOutcome(False, blocked_reason="CANCELLED", mission_id=mission_id)
        # A resumed mission can omit the capability: use the persisted intake
        # family and the live graph rather than manufacturing a foreign tool.
        selected = str(capability or "")
        if not selected:
            family = str(mission.contract.get("intent_family", ""))
            candidates = self.capabilities.resolve(family)
            if len(candidates) == 1:
                selected = candidates[0].name
        executor = self._executors.get(selected)
        if executor is None and selected:
            item = self.capabilities.get(selected)
            executor = getattr(item, "executor", None) if item else None
        if executor is None:
            self.transition(mission_id, "research_pending", next_action="capability research")
            return VerificationOutcome(False, blocked_reason="CAPABILITY_RESEARCH_REQUIRED", mission_id=mission_id)
        started = time.perf_counter()
        try:
            result = executor(mission=mission, cancel=event, **kwargs)
            if isinstance(result, VerificationOutcome):
                outcome = result
            elif isinstance(result, Mapping):
                outcome = VerificationOutcome(**{k: result[k] for k in VerificationOutcome.__dataclass_fields__ if k in result})
            else:
                outcome = VerificationOutcome(bool(getattr(result, "verified", False)), action_taken=True)
        except Exception as exc:  # pragma: no cover - defensive boundary
            outcome = VerificationOutcome(False, blocked_reason=type(exc).__name__, mission_id=mission_id)
        outcome.mission_id = mission_id
        # A plan, a clean return code, or ``ok`` alone is not a verified
        # mission.  The canonical contract requires an action and an observed
        # verified state.
        if outcome.success and not outcome.action_taken:
            outcome.success = False
            outcome.blocked_reason = outcome.blocked_reason or "EXECUTION_NOT_CONFIRMED"
        if outcome.success:
            mission.observed_state = dict(outcome.verified_fields)
        evidence = EvidenceRecordV2(
            claim=f"capability {selected or 'research'} execution outcome",
            source=f"cognitive_kernel:{selected or 'unknown'}",
            confidence=1.0 if outcome.success else 0.0,
            expected_state=dict(mission.desired_state),
            observed_state=dict(outcome.verified_fields),
            freshness="fresh",
            latency_ms=(time.perf_counter() - started) * 1000.0,
            path="deliberate" if mission.contract.get("mode") not in {"conversation", "operator"} else "fast",
        )
        self.record_evidence(mission_id, evidence)
        status = "verified" if outcome.success else "verification_failed"
        self.transition(mission_id, status, next_action="" if outcome.success else "repair or research", error=outcome.blocked_reason or "")
        outcome.evidence_ids.append(evidence.id)
        return outcome

    def resume(self, mission_id: str, **kwargs: Any) -> VerificationOutcome:
        mission = self._require(mission_id)
        return self.run(mission.id, **kwargs)

    def cancel(self, mission_id: str, reason: str = "user_cancelled") -> CancellationResult:
        mission = self._require(mission_id)
        event = self._cancel.setdefault(mission_id, threading.Event())
        event.set()
        if mission.status not in {"verified", "verification_failed", "cancelled"}:
            self.transition(mission_id, "cancelled", next_action="", error=reason)
        return CancellationResult(mission_id, True, stopped_before_mutation=True, reason=reason)

    def undo(self, mission_id: str) -> VerificationOutcome:
        mission = self._require(mission_id)
        if not mission.rollback_plan:
            return VerificationOutcome(False, blocked_reason="ROLLBACK_UNAVAILABLE", mission_id=mission_id)
        capability = str(mission.rollback_plan.get("capability", "")).strip()
        executor = self._rollback_executors.get(capability)
        if executor is None:
            return VerificationOutcome(False, blocked_reason="ROLLBACK_EXECUTOR_UNAVAILABLE", mission_id=mission_id)
        cancel = self._cancel.setdefault(mission_id, threading.Event())
        self.transition(mission_id, "rollback", next_action=f"rollback:{capability}")
        started = time.perf_counter()
        try:
            try:
                raw = executor(mission=mission, cancel=cancel, rollback=True)
            except TypeError:
                raw = executor(mission=mission, cancel=cancel)
            if isinstance(raw, VerificationOutcome):
                outcome = raw
            elif isinstance(raw, Mapping):
                outcome = VerificationOutcome(**{k: raw[k] for k in VerificationOutcome.__dataclass_fields__ if k in raw})
            else:
                outcome = VerificationOutcome(bool(getattr(raw, "verified", False)), action_taken=True)
        except Exception as exc:
            outcome = VerificationOutcome(False, blocked_reason=type(exc).__name__)
        outcome.mission_id = mission_id
        if outcome.success and not outcome.action_taken:
            outcome.success = False
            outcome.blocked_reason = outcome.blocked_reason or "ROLLBACK_NOT_VERIFIED"
        evidence = EvidenceRecordV2(
            claim=f"rollback {capability} outcome",
            source=f"cognitive_kernel:rollback:{capability}",
            confidence=1.0 if outcome.success else 0.0,
            expected_state=dict(mission.rollback_plan.get("expected_state", {})),
            observed_state=dict(outcome.verified_fields),
            freshness="fresh",
            latency_ms=(time.perf_counter() - started) * 1000.0,
            path="deliberate",
        )
        self.record_evidence(mission_id, evidence)
        self.transition(mission_id, "rolled_back" if outcome.success else "verification_failed",
                        next_action="" if outcome.success else "repair or research",
                        error=outcome.blocked_reason or "")
        outcome.evidence_ids.append(evidence.id)
        return outcome

    def explain_decision(self, mission_id: str) -> DecisionTrace:
        mission = self._require(mission_id)
        selected = str(mission.next_action or "")
        return DecisionTrace(mission_id, selected_capability=selected, path="deliberate" if mission.status != "queued" else "fast", evidence_ids=tuple(mission.evidence_ids))

    def close(self) -> None:
        self.ledger.close()

    def _require(self, mission_id: str) -> MissionRecord:
        mission = self.ledger.load(str(mission_id))
        if mission is None:
            raise KeyError(f"unknown mission: {mission_id}")
        return mission


__all__ = ["CognitiveKernel"]
