"""Sprint 9 Capability Engine built above the existing Tool Registry.

The module stores task-class capabilities and successful episodes, composes
existing primitive tools into a DAG, verifies desired state, performs targeted
repair, and persists resumable mission state. It deliberately reuses
``execute_tool``, ``RiskAssessment`` and the existing tool passports.
"""
from __future__ import annotations

import json
import re
import shutil
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from core.actions.base import ActionResult, ToolContext
from core.actions.executor import execute_tool
from core.actions.registry import ToolRegistry


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tokens(text: str) -> set[str]:
    raw = re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]+", (text or "").lower())
    stop = {"the", "and", "from", "with", "для", "как", "это", "или", "мне", "this"}
    return {word for word in raw if len(word) > 2 and word not in stop}


class CapabilityKind(str, Enum):
    BUILTIN = "builtin"
    COMPOSED = "composed"
    LEARNED = "learned"
    EXPERIMENTAL = "experimental"


@dataclass
class CapabilityDefinition:
    id: str
    description: str
    inputs: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    learned_from: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    risk_class: str = "low"
    confidence: float = 0.5
    kind: CapabilityKind = CapabilityKind.EXPERIMENTAL
    generalized_procedure: list[str] = field(default_factory=list)
    procedure_steps: list[dict[str, Any]] = field(default_factory=list)
    desired_state: dict[str, Any] = field(default_factory=dict)
    times_used: int = 0
    success_count: int = 0
    failure_count: int = 0
    average_duration: float = 0.0
    last_used: Optional[str] = None
    last_verified: Optional[str] = None
    environment: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CapabilityDefinition":
        payload = dict(data)
        payload["kind"] = CapabilityKind(payload.get("kind", "experimental"))
        return cls(**payload)

    def record_result(self, *, success: bool, duration: float) -> None:
        previous_total = self.average_duration * self.times_used
        self.times_used += 1
        self.success_count += int(success)
        self.failure_count += int(not success)
        self.average_duration = (previous_total + max(0.0, duration)) / self.times_used
        self.last_used = _utcnow()
        if success:
            self.last_verified = self.last_used
        observed = self.success_count / max(1, self.times_used)
        self.confidence = round(max(0.05, min(0.99, 0.65 * self.confidence + 0.35 * observed)), 3)


@dataclass
class CapabilityEpisode:
    goal: str
    capability: str
    task_class: str
    successful_strategy: list[str]
    failures: list[str] = field(default_factory=list)
    repairs: list[str] = field(default_factory=list)
    verification: list[str] = field(default_factory=list)
    generalized_procedure: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    important_observations: list[str] = field(default_factory=list)
    risk_profile: str = "low"
    duration: float = 0.0
    environment_assumptions: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    episode_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = field(default_factory=_utcnow)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CapabilityEpisode":
        return cls(**data)


class CapabilityCatalog:
    """Atomic JSON persistence for capabilities and episodes."""

    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.episodes_dir = self.directory / "episodes"
        self.episodes_dir.mkdir(exist_ok=True)
        self._lock = threading.RLock()

    def save(self, capability: CapabilityDefinition) -> Path:
        path = self.directory / f"{_safe_id(capability.id)}.json"
        self._atomic_json(path, capability.to_dict())
        return path

    def get(self, capability_id: str) -> Optional[CapabilityDefinition]:
        path = self.directory / f"{_safe_id(capability_id)}.json"
        try:
            return CapabilityDefinition.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            return None

    def all(self) -> list[CapabilityDefinition]:
        result = []
        for path in sorted(self.directory.glob("*.json")):
            item = self.get(path.stem)
            if item is not None:
                result.append(item)
        return result

    def find(self, goal: str, threshold: float = 0.18) -> Optional[CapabilityDefinition]:
        query = _tokens(goal)
        scored = []
        for cap in self.all():
            corpus = _tokens(" ".join([cap.id, cap.description, *cap.generalized_procedure]))
            score = len(query & corpus) / max(1, len(query | corpus))
            if score >= threshold:
                scored.append((score * cap.confidence, cap))
        return max(scored, default=(0.0, None), key=lambda item: item[0])[1]

    def record_episode(self, episode: CapabilityEpisode) -> Path:
        path = self.episodes_dir / f"{episode.episode_id}.json"
        self._atomic_json(path, asdict(episode))
        return path

    def retrieve_episodes(self, goal: str, limit: int = 5) -> list[CapabilityEpisode]:
        query = _tokens(goal)
        scored: list[tuple[float, CapabilityEpisode]] = []
        for path in self.episodes_dir.glob("*.json"):
            try:
                episode = CapabilityEpisode.from_dict(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError, TypeError):
                continue
            corpus = _tokens(" ".join([
                episode.goal, episode.capability, episode.task_class,
                *episode.successful_strategy, *episode.generalized_procedure,
            ]))
            overlap = len(query & corpus) / max(1, len(query))
            if overlap > 0:
                scored.append((overlap * episode.confidence, episode))
        scored.sort(key=lambda item: (-item[0], item[1].created_at))
        return [item[1] for item in scored[:limit]]

    def _atomic_json(self, path: Path, payload: dict[str, Any]) -> None:
        with self._lock:
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(path)


@dataclass(frozen=True)
class DesiredStateResult:
    verified: bool
    missing: dict[str, Any]
    observed: dict[str, Any]


class DesiredStateVerifier:
    def verify(self, desired: dict[str, Any], observed: dict[str, Any]) -> DesiredStateResult:
        missing: dict[str, Any] = {}
        for key, expected in desired.items():
            actual = observed.get(key)
            if isinstance(expected, dict) and isinstance(actual, dict):
                nested = self.verify(expected, actual)
                if not nested.verified:
                    missing[key] = nested.missing
            elif actual != expected:
                missing[key] = {"expected": expected, "actual": actual}
        return DesiredStateResult(not missing, missing, dict(observed))


@dataclass(frozen=True)
class RiskDecision:
    action: str
    auto_execute: bool
    reason: str


class RiskConfidencePolicy:
    """Two-dimensional policy; confidence never overrides elevated risk."""

    def decide(self, *, confidence: float, risk: str) -> RiskDecision:
        level = (risk or "medium").lower()
        if level in {"critical", "high"}:
            return RiskDecision("confirm", False, f"{level} risk requires confirmation")
        if level == "medium":
            return RiskDecision("confirm", False, "system/network change requires confirmation")
        if confidence >= 0.9:
            return RiskDecision("execute", True, "low risk and verified confidence")
        if confidence >= 0.6:
            return RiskDecision("sandbox", False, "low risk requires rehearsal")
        return RiskDecision("research", False, "insufficient confidence")


class Transaction:
    """Checkpoint/rollback for file changes; every restore is idempotent."""

    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._entries: list[dict[str, Any]] = []

    def checkpoint_file(self, path: Path | str) -> Path:
        target = Path(path).resolve()
        backup = self.directory / f"{len(self._entries):04d}-{target.name}.bak"
        existed = target.is_file()
        if existed:
            shutil.copy2(target, backup)
        self._entries.append({"kind": "file", "path": str(target),
                              "backup": str(backup), "existed": existed})
        return backup

    @property
    def entries(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._entries]

    def rollback(self) -> list[str]:
        restored: list[str] = []
        for item in reversed(self._entries):
            target, backup = Path(item["path"]), Path(item["backup"])
            if item["existed"] and backup.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup, target)
            elif not item["existed"] and target.exists():
                target.unlink()
            restored.append(str(target))
        return restored


@dataclass
class MissionState:
    mission_id: str
    goal: str
    state: str = "queued"
    current_step: int = 0
    desired_state: dict[str, Any] = field(default_factory=dict)
    completed_steps: list[str] = field(default_factory=list)
    pending_steps: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    rollback: list[dict[str, Any]] = field(default_factory=list)
    updated_at: str = field(default_factory=_utcnow)

    def pause(self) -> None:
        self.state, self.updated_at = "paused", _utcnow()

    def cancel(self) -> None:
        self.state, self.updated_at = "cancelled", _utcnow()

    def skip(self) -> Optional[str]:
        if not self.pending_steps:
            return None
        skipped = self.pending_steps.pop(0)
        self.current_step += 1
        self.updated_at = _utcnow()
        return skipped

    def explain_current_step(self) -> str:
        return self.pending_steps[0] if self.pending_steps else "completed"


class MissionStateStore:
    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, mission: MissionState) -> Path:
        path = self.directory / f"{_safe_id(mission.mission_id)}.json"
        mission.updated_at = _utcnow()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(mission), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
        return path

    def load(self, mission_id: str) -> Optional[MissionState]:
        path = self.directory / f"{_safe_id(mission_id)}.json"
        try:
            return MissionState(**json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            return None

    def resumable(self) -> list[MissionState]:
        result = []
        for path in self.directory.glob("*.json"):
            item = self.load(path.stem)
            if item is not None and item.state not in {"completed", "cancelled", "failed"}:
                result.append(item)
        return result


@dataclass(frozen=True)
class InterpretedReference:
    application: str
    desired_state: dict[str, Any]
    source_type: str


class ReferenceInterpreter:
    """Converts supplied structured evidence into state, never click replay."""

    def interpret(self, reference: Any) -> InterpretedReference:
        if isinstance(reference, dict):
            desired = dict(reference.get("desired_state") or reference.get("settings") or {})
            return InterpretedReference(
                application=str(reference.get("application", "")), desired_state=desired,
                source_type=str(reference.get("type", "structured")),
            )
        return InterpretedReference("", {"description": str(reference)}, "text")


@dataclass
class ExecutionStep:
    id: str
    tool: str
    args: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    produces: dict[str, Any] = field(default_factory=dict)
    verification: list[str] = field(default_factory=list)


@dataclass
class ExecutionPlan:
    goal: str
    acquisition: str
    desired_state: dict[str, Any] = field(default_factory=dict)
    steps: list[ExecutionStep] = field(default_factory=list)
    capability_id: Optional[str] = None
    requirements: list[str] = field(default_factory=list)
    sources: list[dict[str, str]] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    confidence: float = 0.7
    risk_class: str = "low"

    def ordered_steps(self) -> list[ExecutionStep]:
        """Stable topological ordering; raises on missing deps or cycles."""
        by_id = {step.id: step for step in self.steps}
        if len(by_id) != len(self.steps):
            raise ValueError("duplicate execution step id")
        emitted: list[ExecutionStep] = []
        pending = list(self.steps)
        while pending:
            ready = [step for step in pending if all(dep in {x.id for x in emitted}
                                                     for dep in step.depends_on)]
            if not ready:
                missing = {dep for step in pending for dep in step.depends_on if dep not in by_id}
                raise ValueError(f"invalid execution DAG; missing={sorted(missing)}")
            for step in ready:
                emitted.append(step)
                pending.remove(step)
        return emitted

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data


class CapabilityPlanner:
    """Search → composition → structured research/acquisition, in that order."""

    def __init__(self, catalog: CapabilityCatalog, registry: ToolRegistry,
                 acquire: Optional[Callable[[str], Any]] = None) -> None:
        self.catalog = catalog
        self.registry = registry
        self.acquire = acquire

    def plan(self, goal: str, desired_state: Optional[dict[str, Any]] = None) -> ExecutionPlan:
        learned = self.catalog.find(goal)
        if (
            learned is not None
            and learned.kind is not CapabilityKind.EXPERIMENTAL
            and bool(learned.tools)
            and all(self.registry.get(name) is not None for name in learned.tools)
        ):
            if learned.procedure_steps:
                steps = [ExecutionStep(**data) for data in learned.procedure_steps]
            else:
                steps = []
                previous = None
                for index, tool in enumerate(learned.tools):
                    step_id = f"learned-{index + 1}"
                    steps.append(ExecutionStep(step_id, tool,
                                               depends_on=[previous] if previous else []))
                    previous = step_id
            return ExecutionPlan(
                goal, "learned", desired_state or learned.desired_state, steps, learned.id,
                confidence=learned.confidence, risk_class=learned.risk_class,
            )

        composed = self._compose(goal, desired_state or {})
        if composed is not None:
            return composed

        acquired = self.acquire(goal) if self.acquire is not None else None
        if isinstance(acquired, CapabilityDefinition):
            self.catalog.save(acquired)
            return ExecutionPlan(
                goal, "acquired", desired_state or {},
                [ExecutionStep(f"acquired-{i + 1}", tool,
                               depends_on=[f"acquired-{i}"] if i else [])
                 for i, tool in enumerate(acquired.tools)],
                acquired.id, confidence=acquired.confidence,
                risk_class=acquired.risk_class,
            )

        # Research output is a plan artifact, not a verbose user response.
        return ExecutionPlan(
            goal=goal, acquisition="research", desired_state=desired_state or {},
            requirements=["identify official documentation", "identify missing primitives"],
            sources=[], risks=["unverified execution method"], confidence=0.3,
        )

    def _compose(self, goal: str, desired: dict[str, Any]) -> Optional[ExecutionPlan]:
        low = goal.lower()
        organize = any(word in low for word in ("организ", "сортир", "group", "organize"))
        files = any(word in low for word in ("файл", "file", "extension", "расширен"))
        needed = ("list_files", "file_move", "list_files_recursive")
        if organize and files and all(self.registry.get(name) is not None for name in needed):
            desired = desired or {"organized_by_extension": True}
            return ExecutionPlan(
                goal=goal, acquisition="composed", desired_state=desired,
                capability_id="organize_files_by_extension",
                steps=[
                    ExecutionStep("discover", "list_files"),
                    ExecutionStep("move", "file_move",
                                  args={"foreach": "root_files", "group_by": "extension"},
                                  depends_on=["discover"],
                                  produces={"files_moved": True}),
                    ExecutionStep("verify", "list_files_recursive", depends_on=["move"],
                                  produces={"organized_by_extension": True}),
                ], confidence=0.9, risk_class="low",
            )
        return None


@dataclass(frozen=True)
class StructuredResearchPlan:
    goal: str
    requirements: list[str]
    sources: list[dict[str, Any]]
    steps: list[str]
    verification: list[str]
    risks: list[str]


class CapabilityResearch:
    """Turns research candidates into an execution-oriented, trusted plan."""

    _rank = {"official": 0, "package_manager": 1, "repository": 2,
             "documentation": 3, "third_party": 9}

    def structure(self, goal: str,
                  candidates: Iterable[dict[str, Any]]) -> StructuredResearchPlan:
        verified = [dict(item) for item in candidates if bool(item.get("verified"))]
        verified.sort(key=lambda item: self._rank.get(str(item.get("kind")), 8))
        return StructuredResearchPlan(
            goal=goal,
            requirements=["determine current state", "derive desired state",
                          "resolve required capabilities"],
            sources=verified,
            steps=["inspect current state", "select highest-reliability execution ladder",
                   "checkpoint mutable state", "execute minimal delta", "observe result"],
            verification=["compare observed state with desired state",
                          "verify artifacts independently from tool return value"],
            risks=["network acquisition requires confirmation",
                   "unverified executable sources are excluded"],
        )


@dataclass
class ExecutionReport:
    completed: bool
    state: str
    results: list[ActionResult]
    verification: DesiredStateResult
    repairs: list[str] = field(default_factory=list)
    action_trace: list[str] = field(default_factory=list)
    needs_confirmation: bool = False
    episode: Optional[CapabilityEpisode] = None
    duration: float = 0.0


class CapabilityEngine:
    """Executes a capability DAG and learns only after observed verification."""

    def __init__(self, catalog: CapabilityCatalog, registry: ToolRegistry,
                 *, executor: Optional[Callable[[str, dict[str, Any]], ActionResult]] = None,
                 observer: Optional[Callable[[], dict[str, Any]]] = None,
                 context: Optional[ToolContext] = None) -> None:
        self.catalog = catalog
        self.registry = registry
        self._executor = executor
        self._observer = observer or (lambda: {})
        self._context = context or ToolContext()
        self.verifier = DesiredStateVerifier()
        self.policy = RiskConfidencePolicy()
        self._move_rollback: list[tuple[str, str]] = []

    def execute(self, plan: ExecutionPlan, *, max_repairs: int = 2,
                cancel: Optional[threading.Event] = None) -> ExecutionReport:
        started = time.perf_counter()
        decision = self.policy.decide(confidence=plan.confidence, risk=plan.risk_class)
        empty_verification = self.verifier.verify(plan.desired_state, {})
        if plan.acquisition == "research" or not plan.steps:
            return ExecutionReport(False, "research_required", [], empty_verification,
                                   action_trace=["missing capability requires structured research"])
        if decision.action == "confirm":
            return ExecutionReport(False, "waiting_for_user", [], empty_verification,
                                   needs_confirmation=True,
                                   action_trace=[decision.reason])

        results: list[ActionResult] = []
        trace: list[str] = []
        for step in plan.ordered_steps():
            if cancel is not None and cancel.is_set():
                return ExecutionReport(False, "cancelled", results, empty_verification,
                                       action_trace=trace, duration=time.perf_counter() - started)
            result = self._run_step(step)
            results.append(result)
            trace.append(f"{step.id}: {step.tool} -> {'ok' if result.ok else 'failed'}")
            if not result.ok:
                observed = self._observer()
                verification = self.verifier.verify(plan.desired_state, observed)
                return ExecutionReport(False, "failed", results, verification,
                                       action_trace=trace, duration=time.perf_counter() - started)

        observed = self._observe(plan)
        verification = self.verifier.verify(plan.desired_state, observed)
        repairs: list[str] = []
        attempts = 0
        while not verification.verified and attempts < max_repairs:
            failed_keys = set(verification.missing)
            targets = [step for step in plan.steps if failed_keys & set(step.produces)]
            if not targets:
                break
            for step in targets:
                if cancel is not None and cancel.is_set():
                    return ExecutionReport(False, "cancelled", results, verification,
                                           repairs, trace, duration=time.perf_counter() - started)
                result = self._run_step(step)
                results.append(result)
                repairs.append(step.tool)
                trace.append(f"repair {step.id}: {step.tool} -> {'ok' if result.ok else 'failed'}")
            attempts += 1
            observed = self._observe(plan)
            verification = self.verifier.verify(plan.desired_state, observed)

        duration = time.perf_counter() - started
        completed = verification.verified
        rollback_trace: list[str] = []
        if not completed:
            if self._move_rollback:
                rollback_trace = self._rollback_moves()
                trace.extend(rollback_trace)
            self._record_failure(plan, duration)
        elif completed:
            self._move_rollback.clear()
        episode = self._learn(plan, results, repairs, verification, duration) if completed else None
        return ExecutionReport(completed, "completed" if completed else "verification_failed",
                               results, verification, repairs, trace, episode=episode,
                               duration=duration)

    def _run_step(self, step: ExecutionStep) -> ActionResult:
        if self._executor is not None:
            return self._executor(step.tool, dict(step.args))
        if step.tool == "file_move" and step.args.get("foreach") == "root_files":
            return self._move_root_files_by_extension()
        return execute_tool(self.registry, step.tool, dict(step.args), self._context,
                            max_retries=0)

    def _move_root_files_by_extension(self) -> ActionResult:
        settings = getattr(self._context, "settings", None)
        if settings is None:
            return ActionResult("file_move", {}, False, error="settings are required")
        from core.actions.filesystem import list_files
        files = list_files("", settings, recursive=False)
        moved = []
        for source in files:
            path = Path(source)
            extension = path.suffix.lower().lstrip(".") or "no_extension"
            result = execute_tool(
                self.registry, "file_move",
                {"source": source, "destination": str(Path(extension) / path.name)},
                self._context, max_retries=0,
            )
            if not result.ok:
                self._rollback_moves()
                return result
            moved.append(source)
            self._move_rollback.append((source, str(Path(extension) / path.name)))
        return ActionResult("file_move", {"count": len(moved)}, True,
                            f"Moved {len(moved)} files by extension")

    def _observe(self, plan: ExecutionPlan) -> dict[str, Any]:
        observed = self._observer()
        if observed:
            return observed
        if "organized_by_extension" in plan.desired_state:
            settings = getattr(self._context, "settings", None)
            docs = settings.paths.resolved("documents_dir") if settings is not None else None
            if docs is not None and docs.is_dir():
                root_files = [path for path in docs.iterdir() if path.is_file()]
                nested = [path for path in docs.rglob("*") if path.is_file()]
                organized = not root_files and all(
                    path.parent.name == (path.suffix.lower().lstrip(".") or "no_extension")
                    for path in nested if ".capabilities" not in path.parts
                )
                return {"organized_by_extension": organized}
        return observed

    def _learn(self, plan: ExecutionPlan, results: list[ActionResult], repairs: list[str],
               verification: DesiredStateResult, duration: float) -> CapabilityEpisode:
        capability_id = plan.capability_id or _safe_id(plan.goal)
        capability = self.catalog.get(capability_id) or CapabilityDefinition(
            id=capability_id, description=plan.goal,
            tools=[step.tool for step in plan.steps], kind=CapabilityKind.LEARNED,
            success_criteria=[f"{key}={value!r}" for key, value in plan.desired_state.items()],
            risk_class=plan.risk_class, confidence=plan.confidence,
            generalized_procedure=["observe current state", "apply minimal delta", "verify desired state"],
            procedure_steps=[asdict(step) for step in plan.steps],
            desired_state=dict(plan.desired_state),
        )
        capability.record_result(success=True, duration=duration)
        self.catalog.save(capability)
        episode = CapabilityEpisode(
            goal=plan.goal, capability=capability.id,
            task_class=capability.id,
            successful_strategy=[step.tool for step in plan.steps],
            repairs=list(repairs),
            verification=[f"{key}={value!r}" for key, value in verification.observed.items()],
            generalized_procedure=list(capability.generalized_procedure),
            tools_used=[result.tool for result in results],
            duration=duration, risk_profile=plan.risk_class,
            confidence=capability.confidence,
        )
        self.catalog.record_episode(episode)
        return episode

    def _rollback_moves(self) -> list[str]:
        trace = []
        for source, destination in reversed(self._move_rollback):
            result = execute_tool(
                self.registry, "file_move",
                {"source": destination, "destination": source},
                self._context, max_retries=0,
            )
            trace.append(f"rollback {destination} -> {source}: {'ok' if result.ok else 'failed'}")
        self._move_rollback.clear()
        return trace

    def _record_failure(self, plan: ExecutionPlan, duration: float) -> None:
        if not plan.capability_id:
            return
        capability = self.catalog.get(plan.capability_id)
        if capability is None:
            return
        capability.record_result(success=False, duration=duration)
        self.catalog.save(capability)


def _safe_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("._")
    return cleaned[:100] or "capability"
