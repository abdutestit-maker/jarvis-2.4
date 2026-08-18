"""Semantic workflow discovery and verified Capability Engine integration."""

from __future__ import annotations

import json
import math
import re
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from core.capability_engine import (
    CapabilityCatalog,
    CapabilityDefinition,
    CapabilityEpisode,
    CapabilityKind,
    DesiredStateVerifier,
)
from core.security.atomic import atomic_json_write, load_json
from core.security.redaction import redact


_COORDINATE_KEYS = {"x", "y", "left", "top", "right", "bottom", "coordinates", "rectangle"}
@dataclass(frozen=True)
class SemanticAction:
    verb: str
    target_role: str
    target_name: str
    provider: str
    parameters: dict[str, Any] = field(default_factory=dict)
    risk: str = "low"

    @property
    def signature(self) -> str:
        return "|".join((self.verb.casefold(), self.target_role.casefold(),
                         self.target_name.casefold(), self.provider.casefold()))


@dataclass
class WorkflowRun:
    run_id: str
    actions: list[SemanticAction]
    duration_seconds: float = 0.0
    estimated_automated_seconds: float = 0.0
    success: bool = True
    desired_state: dict[str, Any] = field(default_factory=dict)
    observed_state: dict[str, Any] = field(default_factory=dict)
    observed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class WorkflowCandidate:
    id: str
    description: str
    actions: list[SemanticAction]
    frequency: int
    similarity: float
    time_saved_seconds: float
    reliability: float
    risk: str
    confidence: float
    desired_state: dict[str, Any]
    evidence: list[str] = field(default_factory=list)
    ready_threshold: float = 0.75

    @property
    def ready(self) -> bool:
        return (self.confidence >= self.ready_threshold and self.reliability >= 0.6
                and self.risk in {"low", "medium"})


@dataclass(frozen=True)
class WorkflowExecution:
    verified: bool
    observed: dict[str, Any]
    missing: dict[str, Any]
    action_results: tuple[dict[str, Any], ...]


class WorkflowLearner:
    """Clusters sequences by semantic similarity, never by screen coordinates."""

    def __init__(self, directory: Path | str, *, ready_threshold: float = 0.75,
                 cluster_similarity: float = 0.65) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "workflow_runs.json"
        self.ready_threshold = float(ready_threshold)
        self.cluster_similarity = float(cluster_similarity)
        self._runs: list[WorkflowRun] = []
        self._lock = threading.RLock()
        self._load()

    def observe(self, run: WorkflowRun) -> None:
        if not run.actions:
            return
        actions = [self._sanitize_action(action) for action in run.actions]
        sanitized = WorkflowRun(
            run.run_id, actions, max(0.0, run.duration_seconds),
            max(0.0, run.estimated_automated_seconds), bool(run.success),
            self._safe_mapping(run.desired_state), self._safe_mapping(run.observed_state),
            run.observed_at,
        )
        with self._lock:
            self._runs.append(sanitized)
            self._save()

    def discover(self) -> list[WorkflowCandidate]:
        clusters: list[list[WorkflowRun]] = []
        for run in self._runs:
            placed = False
            for cluster in clusters:
                if self.sequence_similarity(run.actions, cluster[0].actions) >= self.cluster_similarity:
                    cluster.append(run)
                    placed = True
                    break
            if not placed:
                clusters.append([run])
        candidates = [self._candidate(cluster) for cluster in clusters]
        return sorted(candidates, key=lambda item: (-item.confidence, item.id))

    @staticmethod
    def sequence_similarity(left: list[SemanticAction], right: list[SemanticAction]) -> float:
        a, b = [item.signature for item in left], [item.signature for item in right]
        if not a or not b:
            return 0.0
        table = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
        for i, x in enumerate(a, 1):
            for j, y in enumerate(b, 1):
                table[i][j] = table[i - 1][j - 1] + 1 if x == y else max(
                    table[i - 1][j], table[i][j - 1],
                )
        return 2 * table[-1][-1] / (len(a) + len(b))

    def _candidate(self, runs: list[WorkflowRun]) -> WorkflowCandidate:
        similarities = [
            self.sequence_similarity(left.actions, right.actions)
            for index, left in enumerate(runs) for right in runs[index + 1:]
        ]
        similarity = sum(similarities) / len(similarities) if similarities else 0.5
        frequency = len(runs)
        reliability = sum(run.success for run in runs) / frequency
        saved = [max(0.0, run.duration_seconds - run.estimated_automated_seconds) for run in runs]
        time_saved = sum(saved) / frequency
        durations = sum(max(1.0, run.duration_seconds) for run in runs) / frequency
        time_score = min(1.0, time_saved / durations)
        frequency_score = 1 - math.exp(-frequency / 2.5)
        risk = max((action.risk for run in runs for action in run.actions),
                   key=lambda item: {"low": 0, "medium": 1, "high": 2, "critical": 3}.get(item, 2))
        safety_score = 1 - {"low": 0.1, "medium": 0.45, "high": 0.8, "critical": 1}.get(risk, 0.8)
        confidence = min(0.99, 0.22 * frequency_score + 0.25 * similarity
                         + 0.25 * reliability + 0.18 * time_score + 0.10 * safety_score)
        actions = self._generalize([run.actions for run in runs])
        description = " ".join(dict.fromkeys(
            word for action in actions for word in (
                action.verb, action.target_role, action.target_name,
            ) if word
        ))
        identifier = re.sub(r"[^a-z0-9]+", "_", description.casefold()).strip("_")[:72]
        desired = next((run.desired_state for run in reversed(runs) if run.success and run.desired_state), {})
        return WorkflowCandidate(
            f"workflow_{identifier or 'semantic'}", description, actions, frequency,
            round(similarity, 3), round(time_saved, 3), round(reliability, 3), risk,
            round(confidence, 3), dict(desired),
            [f"frequency={frequency}", f"similarity={similarity:.3f}",
             f"reliability={reliability:.3f}", f"time_saved={time_saved:.3f}s"],
            self.ready_threshold,
        )

    @staticmethod
    def _generalize(sequences: list[list[SemanticAction]]) -> list[SemanticAction]:
        length = min(map(len, sequences))
        result: list[SemanticAction] = []
        for index in range(length):
            group = [sequence[index] for sequence in sequences]
            reference = group[0]
            parameters: dict[str, Any] = {}
            keys = set().union(*(action.parameters for action in group))
            for key in sorted(keys):
                values = [action.parameters.get(key) for action in group]
                parameters[key] = values[0] if all(value == values[0] for value in values) else {"$slot": key}
            result.append(SemanticAction(
                reference.verb, reference.target_role, reference.target_name,
                reference.provider, parameters, reference.risk,
            ))
        return result

    @staticmethod
    def _sanitize_action(action: SemanticAction) -> SemanticAction:
        keys = {str(key).casefold() for key in action.parameters}
        if keys & _COORDINATE_KEYS:
            raise ValueError("workflow actions must be semantic; coordinates are excluded")
        return SemanticAction(
            action.verb, action.target_role, action.target_name, action.provider,
            WorkflowLearner._safe_mapping(action.parameters), action.risk,
        )

    @staticmethod
    def _safe_mapping(value: dict[str, Any]) -> dict[str, Any]:
        return redact(value)

    def _save(self) -> None:
        payload = {"runs": [
            {**asdict(run), "actions": [asdict(action) for action in run.actions]}
            for run in self._runs[-200:]
        ]}
        atomic_json_write(self.path, payload)

    def _load(self) -> None:
        try:
            payload = load_json(self.path, default={}) or {}
        except (OSError, ValueError, TypeError):
            return
        restored: list[WorkflowRun] = []
        for raw in list(payload.get("runs") or [])[-200:]:
            try:
                actions = [self._sanitize_action(SemanticAction(**item))
                           for item in raw.get("actions") or []]
                restored.append(WorkflowRun(
                    run_id=str(raw["run_id"]), actions=actions,
                    duration_seconds=float(raw.get("duration_seconds", 0)),
                    estimated_automated_seconds=float(raw.get("estimated_automated_seconds", 0)),
                    success=bool(raw.get("success", False)),
                    desired_state=dict(raw.get("desired_state") or {}),
                    observed_state=dict(raw.get("observed_state") or {}),
                    observed_at=str(raw.get("observed_at") or datetime.now(timezone.utc).isoformat()),
                ))
            except (KeyError, TypeError, ValueError):
                continue
        self._runs = restored


class WorkflowCapabilityBridge:
    def __init__(self, catalog: CapabilityCatalog) -> None:
        self.catalog = catalog

    def rehearse(self, candidate: WorkflowCandidate,
                 rehearsal: Callable[[WorkflowCandidate], dict[str, Any]]) -> CapabilityDefinition | None:
        if not candidate.ready:
            return None
        result = dict(rehearsal(candidate) or {})
        if not result.get("verified"):
            return None
        procedure = [
            f"{action.provider}:{action.verb}:{action.target_role}:{action.target_name}"
            for action in candidate.actions
        ]
        capability = CapabilityDefinition(
            id=candidate.id,
            description=candidate.description,
            tools=list(dict.fromkeys(action.provider for action in candidate.actions)),
            kind=CapabilityKind.LEARNED,
            success_criteria=[f"{key}={value!r}" for key, value in candidate.desired_state.items()],
            risk_class=candidate.risk,
            confidence=candidate.confidence,
            generalized_procedure=procedure,
            procedure_steps=[{
                "id": f"workflow-{index + 1}", "tool": action.provider,
                "args": dict(action.parameters), "depends_on": [f"workflow-{index}"] if index else [],
                "produces": {}, "verification": [],
            } for index, action in enumerate(candidate.actions)],
            desired_state=dict(candidate.desired_state),
        )
        duration = float(result.get("duration", 0))
        capability.record_result(success=True, duration=duration)
        self.catalog.save(capability)
        observed = dict(result.get("observed") or {})
        episode = CapabilityEpisode(
            goal=candidate.description, capability=capability.id,
            task_class="semantic_workflow", successful_strategy=procedure,
            verification=[f"{key}={value!r}" for key, value in observed.items()],
            generalized_procedure=procedure, tools_used=list(capability.tools),
            duration=duration, risk_profile=candidate.risk,
            confidence=capability.confidence,
        )
        self.catalog.record_episode(episode)
        return capability


class WorkflowExecutor:
    def __init__(self, providers: dict[str, Callable[[SemanticAction, dict[str, Any]], Any]],
                 *, observer: Callable[[], dict[str, Any]]) -> None:
        self.providers = dict(providers)
        self.observer = observer
        self.verifier = DesiredStateVerifier()

    def execute(self, candidate: WorkflowCandidate, *, slots: dict[str, Any] | None = None) -> WorkflowExecution:
        slots = dict(slots or {})
        results: list[dict[str, Any]] = []
        for action in candidate.actions:
            provider = self.providers.get(action.provider)
            if provider is None:
                results.append({"provider": action.provider, "accepted": False, "error": "missing provider"})
                continue
            params = self._slots(action.parameters, slots)
            missing_slots = sorted(self._missing_slots(action.parameters, slots))
            if missing_slots:
                results.append({
                    "provider": action.provider, "verb": action.verb, "accepted": False,
                    "error": "missing slots: " + ", ".join(missing_slots),
                })
                continue
            try:
                raw_result = provider(action, params)
                if isinstance(raw_result, dict):
                    accepted = bool(raw_result.get(
                        "verified", raw_result.get("ok", raw_result.get("success", False)),
                    ))
                else:
                    accepted = bool(raw_result)
                results.append({"provider": action.provider, "verb": action.verb,
                                "accepted": accepted})
            except Exception as exc:
                results.append({
                    "provider": action.provider, "verb": action.verb, "accepted": False,
                    "error": f"{type(exc).__name__}: {exc}",
                })
        try:
            observed = dict(self.observer())
            verification = self.verifier.verify(candidate.desired_state, observed)
            missing = dict(verification.missing)
        except Exception as exc:
            observed = {}
            missing = {"observation": {"error": f"{type(exc).__name__}: {exc}"}}
        rejected = [index for index, item in enumerate(results) if not item.get("accepted")]
        if rejected:
            missing["workflow_actions"] = {"expected": "all accepted", "failed_indexes": rejected}
        return WorkflowExecution(not missing, observed, missing, tuple(results))

    @classmethod
    def _slots(cls, value: Any, slots: dict[str, Any]) -> Any:
        if isinstance(value, dict) and set(value) == {"$slot"}:
            return slots.get(str(value["$slot"]))
        if isinstance(value, dict):
            return {key: cls._slots(item, slots) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._slots(item, slots) for item in value]
        return value

    @classmethod
    def _missing_slots(cls, value: Any, slots: dict[str, Any]) -> set[str]:
        if isinstance(value, dict) and set(value) == {"$slot"}:
            name = str(value["$slot"])
            return {name} if name not in slots or slots[name] is None else set()
        if isinstance(value, dict):
            return set().union(*(cls._missing_slots(item, slots) for item in value.values())) if value else set()
        if isinstance(value, list):
            return set().union(*(cls._missing_slots(item, slots) for item in value)) if value else set()
        return set()


__all__ = [
    "SemanticAction", "WorkflowCandidate", "WorkflowCapabilityBridge",
    "WorkflowExecution", "WorkflowExecutor", "WorkflowLearner", "WorkflowRun",
]
