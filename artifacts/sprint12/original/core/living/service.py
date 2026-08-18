"""Integration facade for context, proactive policy, Shadow and Mission Runtime."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from core.capability_engine import DesiredStateVerifier
from core.shadow.backlog import ShadowBacklog
from core.task_runtime import Mission, MissionStatus, TaskRuntime

from .context import LivingContextEngine
from .models import ContextObservation
from .monitor import LivingContextMonitor
from .proactive import (
    AssistancePolicy,
    AttentionSnapshot,
    ProactiveCandidate,
    ProactiveDecision,
    ProactiveDecisionEngine,
    ProactiveMemoryStore,
    UserProfileStore,
)
from .resources import (
    BackgroundBudgetManager,
    BackgroundMode,
    CapabilityQualityLoop,
    LocalResourceSampler,
    QualityResult,
    ResourceSnapshot,
)
from .workflow import WorkflowLearner, WorkflowRun


@dataclass(frozen=True)
class ProactiveCycleResult:
    decision: ProactiveDecision
    mission: Mission | None = None


@dataclass(frozen=True)
class ProactiveExecutionResult:
    action: str
    executed: bool
    verified: bool
    observed: dict[str, Any]
    missing: dict[str, Any]
    rolled_back: bool
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class AssistanceExecutionResult:
    message: str
    executed: bool
    verified: bool
    result: Any = None


class LivingIntelligence:
    def __init__(self, directory: Path | str, *, task_runtime: TaskRuntime | None = None,
                 shadow_engine: Any = None) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.context = LivingContextEngine(self.directory / "context")
        self.workflows = WorkflowLearner(self.directory / "workflows")
        self.memory = ProactiveMemoryStore(self.directory / "memory")
        self.profile_store = UserProfileStore(self.directory / "profile")
        self.decisions = ProactiveDecisionEngine(self.memory)
        self.resources = BackgroundBudgetManager()
        self.resource_sampler = LocalResourceSampler()
        self.task_runtime = task_runtime or TaskRuntime(
            persistence_dir=self.directory / "missions",
        )
        self.shadow_backlog = (
            shadow_engine.backlog if shadow_engine is not None
            else ShadowBacklog(self.directory / "shadow")
        )
        self.quality = CapabilityQualityLoop(self.directory / "quality", self.shadow_backlog)
        self.verifier = DesiredStateVerifier()
        self.monitor = LivingContextMonitor(self.context)

    def start(self) -> None:
        self.monitor.start()

    def stop(self) -> None:
        self.monitor.stop()

    def observe_user_input(self, text: str, *, active_mission: bool = False) -> None:
        """Adds declared intent while retaining the last sampled application metadata."""
        current = self.context.current
        self.context.update(ContextObservation(
            source="user_language",
            application=current.active_application,
            process=current.active_process,
            window_title=current.window_title,
            domain=current.browser_domain,
            page_title=current.page_title,
            action="user_request",
            user_language=(text or "").strip(),
            active_mission=active_mission,
        ))

    def observe_action(self, *, action: str, outcome: str = "unknown",
                       application: str = "", target: str = "", source: str = "local_action",
                       error_signature: str = "", active_mission: bool = False,
                       metadata: dict[str, Any] | None = None) -> None:
        current = self.context.current
        self.context.update(ContextObservation(
            source=source,
            application=application or current.active_application,
            process=current.active_process,
            window_title=current.window_title,
            domain=current.browser_domain,
            page_title=current.page_title,
            action=action,
            target=target,
            outcome=outcome,
            error_signature=error_signature,
            active_mission=active_mission,
            metadata=dict(metadata or {}),
        ))

    def observe_mission_event(self, event: Any) -> None:
        event_type = str(getattr(event, "event_type", ""))
        payload = dict(getattr(event, "payload", {}) or {})
        status = str(payload.get("status") or getattr(event, "phase", ""))
        outcome = "failure" if "failed" in event_type or status == "failed" else (
            "success" if "completed" in event_type or status == "completed" else "unknown"
        )
        active = status not in {"completed", "failed", "cancelled"}
        self.observe_action(
            action=event_type or "mission_event", outcome=outcome, source="mission_runtime",
            error_signature=str(payload.get("error") or ""),
            active_mission=active,
            metadata={
                "mission_id": str(getattr(event, "task_id", "")),
                "mission_status": status,
                "mission_goal": str(payload.get("goal") or ""),
            },
        )

    def observe_capability_outcome(self, request: str, *, verified: bool,
                                   capability_id: str = "", error: str = "") -> None:
        self.observe_action(
            action="capability_verified" if verified else "capability_failed",
            outcome="success" if verified else "failure", source="jarvis_capability",
            error_signature=error,
            metadata={"goal_hint": request, "capability_id": capability_id},
        )

    def observe_file_activity(self, action: str, path_role: str, *, outcome: str = "success",
                              project: str = "", workflow: str = "") -> None:
        self.observe_action(
            action=action, outcome=outcome, application="File Explorer",
            target=path_role, source="file_activity",
            metadata={"project": project, "workflow": workflow},
        )

    def observe_workflow(self, run: WorkflowRun) -> None:
        self.workflows.observe(run)
        self.observe_action(
            action="workflow_observed", outcome="success" if run.success else "failure",
            source="workflow_learner",
            metadata={"workflow": run.run_id, "goal_hint": " ".join(
                item.target_name for item in run.actions if item.target_name
            )},
        )

    def opportunity_candidates(self) -> list[ProactiveCandidate]:
        """Converts evidence-backed learned workflows into policy candidates."""
        result: list[ProactiveCandidate] = []
        for workflow in self.workflows.discover():
            if not workflow.ready:
                continue
            expected = max(0.5, min(1.0, workflow.time_saved_seconds / 60.0))
            result.append(ProactiveCandidate(
                id=workflow.id, topic=workflow.description,
                opportunity=f"automate semantic workflow: {workflow.description}",
                confidence=workflow.confidence, expected_value=expected,
                reversible=workflow.risk == "low", risk=workflow.risk,
                evidence=list(workflow.evidence), can_prepare=True,
                capability_id=workflow.id,
            ))
        return result

    def observe_clipboard_metadata(self, metadata: dict[str, Any], *, permission: bool) -> bool:
        if not permission:
            return False
        allowed = {key: value for key, value in metadata.items()
                   if key in {"type", "format", "size", "item_count"}}
        current = self.context.current
        self.context.update(ContextObservation(
            source="clipboard_metadata", application=current.active_application,
            process=current.active_process, window_title=current.window_title,
            action="clipboard_metadata_changed", clipboard_metadata=allowed,
        ))
        return True

    def answer_context(self, question: str) -> dict[str, Any] | None:
        normalized = " ".join((question or "").casefold().replace("ё", "е").split())
        markers = (
            "что я сейчас делал", "что я делал", "на чем остановились",
            "на чем мы остановились", "что ты заметил", "чему я тебя научил",
            "чему ты научился", "что ты делал пока меня не было",
        )
        if not any(marker in normalized for marker in markers):
            return None
        return self.context.answer(normalized)

    def proactive_cycle(self, candidate: ProactiveCandidate,
                        attention: AttentionSnapshot, *,
                        resources: ResourceSnapshot | None = None,
                        prepare: Callable[[], dict[str, Any]] | None = None) -> ProactiveCycleResult:
        decision = self.decisions.decide(
            candidate, attention, profile=self.profile_store.load(),
        )
        mission = None
        if decision.action.value == "PREPARE" and prepare is not None:
            mission = self.schedule_prepare(
                candidate, prepare, resources=resources or self.resource_sampler.sample(),
            )
        return ProactiveCycleResult(decision, mission)

    def schedule_prepare(self, candidate: ProactiveCandidate,
                         prepare: Callable[[], dict[str, Any]], *,
                         resources: ResourceSnapshot) -> Mission | None:
        budget = self.resources.assess(resources)
        if budget.mode is BackgroundMode.PAUSE:
            self.shadow_backlog.add_ranked(
                candidate.id, reason="background budget paused preparation",
                user_pain=candidate.expected_value,
                frequency=min(1.0, candidate.confidence),
                time_saved=candidate.expected_value,
                reuse_probability=candidate.confidence,
                risk={"low": 0.1, "medium": 0.5, "high": 0.9, "critical": 1}.get(candidate.risk, 0.9),
                learning_cost=0.4,
            )
            return None

        def runner(mission: Mission, cancel: threading.Event) -> str:
            latest_error = ""
            for attempt in range(1, 4):
                while mission.status is MissionStatus.PAUSED and not cancel.is_set():
                    time.sleep(0.05)
                if cancel.is_set():
                    raise RuntimeError("preparation cancelled")
                if budget.mode is BackgroundMode.THROTTLE:
                    time.sleep(max(0.05, min(0.5, 0.15 - budget.cpu_quota)))
                mission.set_progress((attempt - 1) / 3, f"prepare attempt {attempt}")
                try:
                    result = dict(prepare() or {})
                    if not result.get("verified"):
                        raise RuntimeError("prepared capability did not pass rehearsal")
                    mission.verification = {"verified": True, "evidence": list(candidate.evidence)}
                    mission.set_progress(1.0, "prepared and verified")
                    return json.dumps(result, ensure_ascii=False)
                except Exception as exc:
                    latest_error = str(exc)
                    mission.note_error(latest_error)
                    time.sleep(0.05 * attempt)
            raise RuntimeError(latest_error or "preparation failed")

        return self.task_runtime.submit(
            f"Prepare: {candidate.opportunity}", runner,
            metadata={
                "proactive": True, "candidate_id": candidate.id,
                "risk": candidate.risk, "evidence": list(candidate.evidence),
                "foreground_interruption": False,
                "background_mode": budget.mode.value, "cpu_quota": budget.cpu_quota,
            },
        )

    def execute_proactive(self, candidate: ProactiveCandidate,
                          attention: AttentionSnapshot, *,
                          desired_state: dict[str, Any], checkpoint: Callable[[], Any],
                          executor: Callable[[], Any], observer: Callable[[], dict[str, Any]],
                          rollback: Callable[[Any], Any]) -> ProactiveExecutionResult:
        decision = self.decisions.decide(
            candidate, attention, profile=self.profile_store.load(),
        )
        if decision.action.value != "ACT":
            return ProactiveExecutionResult(
                decision.action.value, False, False, {}, dict(desired_state), False,
                decision.evidence,
            )
        saved = checkpoint()
        try:
            executor()  # return flags are never treated as verification
            observed = dict(observer())
        except Exception as exc:
            rolled_back = False
            rollback_error = ""
            try:
                rolled_back = bool(rollback(saved))
            except Exception as rollback_exc:
                rollback_error = f"; rollback_error={type(rollback_exc).__name__}: {rollback_exc}"
            return ProactiveExecutionResult(
                decision.action.value, True, False, {}, dict(desired_state), rolled_back,
                (*decision.evidence, f"execution_error={type(exc).__name__}: {exc}{rollback_error}"),
            )
        verification = self.verifier.verify(desired_state, observed)
        rolled_back = False
        if not verification.verified:
            rolled_back = bool(rollback(saved))
        return ProactiveExecutionResult(
            decision.action.value, True, verification.verified, observed,
            verification.missing, rolled_back, decision.evidence,
        )

    def assist(self, request: str, *, capability_available: bool,
               operator: Callable[[str], Any] | None = None,
               requires_user_input: str = "", provider_trace: str = "") -> AssistanceExecutionResult:
        profile = self.profile_store.load()
        policy = AssistancePolicy().plan(
            request, assistance=profile.assistance,
            capability_available=capability_available,
            requires_user_input=requires_user_input,
            provider_trace=provider_trace,
        )
        if not policy.execute_safe_parts or operator is None:
            return AssistanceExecutionResult(policy.message, False, False)
        result = operator(request)
        verified = bool(result.get("verified")) if isinstance(result, dict) else bool(
            getattr(result, "verified", False)
        )
        return AssistanceExecutionResult(policy.message, True, verified, result)

    def record_capability_outcome(self, capability_id: str, *, verified: bool,
                                  duration: float, expected_duration: float,
                                  repairs: int = 0, fallbacks: int = 0) -> QualityResult:
        return self.quality.record(
            capability_id, verified=verified, duration=duration,
            expected_duration=expected_duration, repairs=repairs,
            fallbacks=fallbacks,
        )


__all__ = [
    "AssistanceExecutionResult", "LivingIntelligence", "ProactiveCycleResult",
    "ProactiveExecutionResult",
]
