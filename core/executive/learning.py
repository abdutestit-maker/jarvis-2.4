"""Learning primitives: semantic demonstrations, rehearsal, temporal memory and evals."""

from __future__ import annotations

import re
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterable, Optional

from .models import (
    CommandPlan,
    DemoStep,
    EvalCase,
    LearnedWorkflow,
    RehearsalReport,
    UndoRecord,
    now_iso,
)
from .store import ExecutiveStore


_RAW_ACTIONS = re.compile(r"(?i)(coordinate|координат|pixel|пиксел|mouse\s*move|keylog|keystroke|скриншот|screenshot)")


class TwoSpeedCognition:
    """Select reflex vs deliberate execution without adding a model."""

    def choose(self, goal: str, *, known: bool = False, risk: str = "low",
               complexity: float = 0.0) -> dict[str, Any]:
        deliberate = (not known) or risk.casefold() in {"high", "critical"} or float(complexity) >= 0.6
        return {"path": "deliberate" if deliberate else "reflex",
                "evaluator": bool(deliberate), "reason": "unknown/risky/long" if deliberate else "known/reversible"}


class DemonstrationLearner:
    """Turns semantic observations into a parameterised workflow."""

    def __init__(self, store: ExecutiveStore | str | None = None) -> None:
        self.store = store if isinstance(store, ExecutiveStore) else ExecutiveStore(store or "data/executive")
        self._active: list[DemoStep] = []
        self._name = ""
        self._scope = "local"

    def start(self, name: str, *, scope: str = "local") -> None:
        self._name = " ".join((name or "learned_workflow").split())
        self._scope = scope
        self._active = []

    def observe(self, action: str, *, target: str = "", parameters: Optional[dict[str, Any]] = None) -> DemoStep:
        raw = " ".join((action or "").split())
        if _RAW_ACTIONS.search(raw) or _RAW_ACTIONS.search(target or ""):
            raise ValueError("demonstration accepts semantic actions only")
        step = DemoStep(action=raw, target=" ".join((target or "").split()), parameters=dict(parameters or {}))
        self._active.append(step)
        return step

    def finish(self, *, verify: bool = False, parameters: Optional[Iterable[str]] = None) -> LearnedWorkflow:
        if not self._name:
            self.start("learned_workflow")
        workflow = LearnedWorkflow(name=self._name, steps=list(self._active),
                                   parameters=list(parameters or self._infer_parameters()),
                                   confidence=0.85 if verify else 0.55, scope=self._scope,
                                   last_verified=now_iso() if verify else None)
        existing = self.store.read("workflows", [])
        if not isinstance(existing, list):
            existing = []
        existing = [item for item in existing if item.get("name") != workflow.name]
        existing.append(workflow.to_dict())
        self.store.write("workflows", existing[-200:])
        self._active = []
        return workflow

    learn = finish

    def _infer_parameters(self) -> list[str]:
        values: list[str] = []
        for step in self._active:
            for key, value in step.parameters.items():
                if isinstance(value, (str, int, float)) and str(value) not in {"", "0"}:
                    values.append(str(key))
        return list(dict.fromkeys(values))


TeachByDemonstration = DemonstrationLearner


class ShadowRehearsal:
    """Simulates a CommandPlan without invoking tools or external services."""

    def rehearse(self, plan: CommandPlan, current_state: Optional[dict[str, Any]] = None) -> RehearsalReport:
        blockers: list[str] = []
        warnings: list[str] = []
        simulated: list[str] = []
        side_effects: list[str] = []
        state = dict(current_state or {})
        for step in plan.steps:
            simulated.append(step.primitive.value)
            # Empty args are valid for no-argument tools (clock/status).  A
            # planner that needs parameters must express the missing field in
            # ``expected_state`` or constraints; rehearsal never guesses.
            if not step.reversible:
                side_effects.append(step.tool or step.description)
            if step.expected_state and state:
                unknown = [key for key in step.expected_state if key not in state]
                if unknown:
                    warnings.append(f"state not observed: {', '.join(unknown)}")
        if not plan.steps:
            blockers.append("empty plan")
        return RehearsalReport(ready=not blockers, plan_id=plan.plan_id, blockers=blockers,
                               warnings=warnings, simulated_steps=simulated,
                               rollback_ready=all(step.reversible for step in plan.steps),
                               side_effects=side_effects)


class TemporalMemory:
    def __init__(self, store: ExecutiveStore | str | None = None) -> None:
        self.store = store if isinstance(store, ExecutiveStore) else ExecutiveStore(store or "data/executive")
        self._lock = threading.RLock()
        self._items: list[dict[str, Any]] = [item for item in self.store.read("temporal", []) if isinstance(item, dict)]

    def _save(self) -> None:
        self.store.write("temporal", self._items[-1000:])

    def remember(self, fact: str, *, source: str, confidence: float = 0.7,
                 importance: float = 0.5, valid_from: Optional[str] = None,
                 valid_until: Optional[str] = None, volatility: str = "normal",
                 supersedes: Optional[str] = None) -> dict[str, Any]:
        item = {"fact": " ".join((fact or "").split()), "source": source,
                "confidence": max(0.0, min(1.0, confidence)), "importance": importance,
                "valid_from": valid_from or now_iso(), "valid_until": valid_until,
                "volatility": volatility, "last_verified": now_iso(),
                "supersedes": supersedes}
        if not item["fact"]:
            raise ValueError("fact is required")
        with self._lock:
            self._items = [old for old in self._items if old.get("fact") != item["fact"]]
            self._items.append(item)
            self._save()
        return item

    def current(self, query: str = "", *, limit: int = 8) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        tokens = set(re.findall(r"[\w-]{2,}", (query or "").casefold(), flags=re.UNICODE))
        values = []
        for item in self._items:
            try:
                until = datetime.fromisoformat(item["valid_until"]) if item.get("valid_until") else None
                if until and until.tzinfo is None:
                    until = until.replace(tzinfo=timezone.utc)
                if until and until <= now:
                    continue
            except (TypeError, ValueError):
                continue
            score = len(tokens & set(re.findall(r"[\w-]{2,}", str(item.get("fact", "")).casefold())))
            if not tokens or score:
                values.append((score, float(item.get("confidence", 0.0)), item))
        values.sort(key=lambda row: (row[0], row[1]), reverse=True)
        return [item for _, _, item in values[:max(1, int(limit))]]

    def forget(self, fact: str) -> int:
        needle = " ".join((fact or "").split()).casefold()
        before = len(self._items)
        self._items = [item for item in self._items if needle not in str(item.get("fact", "")).casefold()]
        if len(self._items) != before:
            self._save()
        return before - len(self._items)

    def expire(self) -> int:
        before = len(self._items)
        self._items = self.current("")
        if len(self._items) != before:
            self._save()
        return before - len(self._items)

    def why(self, fact: str) -> Optional[dict[str, Any]]:
        needle = (fact or "").casefold()
        return next((item for item in self._items if needle in str(item.get("fact", "")).casefold()), None)


class SleepMode:
    """Runs only bounded local consolidation hooks."""

    def run(self, *, temporal: Optional[TemporalMemory] = None,
            hooks: Iterable[Callable[[], Any]] = ()) -> dict[str, Any]:
        report = {"expired": 0, "hooks": [], "external_actions": 0}
        if temporal is not None:
            report["expired"] = temporal.expire()
        for hook in hooks:
            try:
                report["hooks"].append({"name": getattr(hook, "__name__", "hook"), "result": hook()})
            except Exception as exc:  # sleep maintenance is best effort
                report["hooks"].append({"name": getattr(hook, "__name__", "hook"), "error": type(exc).__name__})
        return report


class SemanticUndo:
    def __init__(self, store: ExecutiveStore | str | None = None) -> None:
        self.store = store if isinstance(store, ExecutiveStore) else ExecutiveStore(store or "data/executive")

    def record(self, action_id: str, *, before: dict[str, Any], after: dict[str, Any],
               inverse: Optional[dict[str, Any]] = None, verified: bool = False) -> UndoRecord:
        record = UndoRecord(action_id=action_id, before=dict(before), after=dict(after),
                            inverse=dict(inverse or before), verified=verified)
        self.store.append("undo", record.to_dict(), limit=500)
        return record

    def latest(self, action_id: Optional[str] = None) -> Optional[UndoRecord]:
        raw = self.store.read("undo", [])
        values = [item for item in raw if not action_id or item.get("action_id") == action_id]
        return UndoRecord(**values[-1]) if values else None

    def inverse_state(self, action_id: Optional[str] = None) -> Optional[dict[str, Any]]:
        item = self.latest(action_id)
        return dict(item.inverse) if item else None


class AskOncePolicy:
    """Select one high-information question and suppress duplicates."""

    def __init__(self) -> None:
        self._asked: set[str] = set()

    def choose(self, uncertainties: Iterable[str], *, observations: Optional[dict[str, Any]] = None) -> Optional[str]:
        known = set((observations or {}).keys())
        options = [" ".join(str(item).split()).strip() for item in uncertainties if str(item).strip()]
        options = [item for item in options if item.casefold() not in self._asked and item.casefold() not in known]
        if not options:
            return None
        selected = max(options, key=lambda item: (len(set(item.casefold().split())), -len(item)))
        self._asked.add(selected.casefold())
        return selected

    def reset(self) -> None:
        self._asked.clear()

    def choose_for(
        self, mission_context: dict[str, Any], uncertainties: Iterable[str],
        *, observations: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        """Choose once using durable mission context instead of process memory."""
        state = mission_context.setdefault("ask_once", {})
        asked = state.setdefault("asked", [])
        answers = state.setdefault("answers", {})
        known = {_key.casefold() for _key in (observations or {}).keys()}
        known.update(str(item).casefold() for item in answers)
        prior = {str(item).casefold() for item in asked}
        options = [" ".join(str(item).split()).strip() for item in uncertainties if str(item).strip()]
        options = [item for item in options if item.casefold() not in prior and item.casefold() not in known]
        if not options:
            return None
        selected = max(options, key=lambda item: (len(set(item.casefold().split())), -len(item)))
        asked.append(selected)
        return selected

    @staticmethod
    def record_answer(mission_context: dict[str, Any], question: str, answer: Any) -> None:
        state = mission_context.setdefault("ask_once", {})
        asked = state.setdefault("asked", [])
        if question not in asked:
            asked.append(question)
        state.setdefault("answers", {})[question] = answer


class CounterfactualEngine:
    def evaluate(self, goal: str, options: Iterable[str], *, constraints: Iterable[str] = ()) -> dict[str, Any]:
        values = [" ".join(str(item).split()) for item in options if str(item).strip()]
        blocked = {str(item).casefold() for item in constraints}
        analyses = []
        for option in values:
            risk = "high" if any(word in option.casefold() for word in ("удал", "отправ", "формат", "парол")) else "low"
            analyses.append({"option": option, "consequence": f"изменит состояние для цели: {goal}",
                             "risk": risk, "blocked": any(item in option.casefold() for item in blocked)})
        viable = [item for item in analyses if not item["blocked"]]
        recommendation = min(viable, key=lambda item: (item["risk"] != "low", len(item["option"])), default=None)
        return {"goal": goal, "options": analyses, "recommendation": recommendation}


class PersonalEvalLab:
    def __init__(self, store: ExecutiveStore | str | None = None) -> None:
        self.store = store if isinstance(store, ExecutiveStore) else ExecutiveStore(store or "data/executive")

    def record(self, case: EvalCase | str, *, goal: str = "", verified: bool = False,
               result: str = "", repairs: int = 0, expected_state: Optional[dict[str, Any]] = None,
               reused: bool = False, stale_memory_uses: int = 0,
               questions: int = 0, rollback_verified: bool = False,
               accepted: Optional[bool] = None) -> EvalCase:
        item = case if isinstance(case, EvalCase) else EvalCase(name=str(case), goal=goal,
            expected_state=dict(expected_state or {}), last_result=result, verified=verified,
            repair_count=int(repairs))
        if isinstance(case, EvalCase):
            item.last_result, item.verified, item.repair_count = result, verified, int(repairs)
        record = item.to_dict()
        record.update({"reused": bool(reused), "stale_memory_uses": int(stale_memory_uses),
                       "questions": int(questions), "rollback_verified": bool(rollback_verified),
                       "accepted": accepted})
        self.store.append("evals", record, limit=1000)
        return item

    def summary(self) -> dict[str, Any]:
        rows = [item for item in self.store.read("evals", []) if isinstance(item, dict)]
        total = len(rows)
        passed = sum(bool(item.get("verified")) for item in rows)
        repairs = sum(int(item.get("repair_count", 0)) for item in rows)
        return {"total": total, "verified": passed, "verified_rate": passed / total if total else 0.0,
                "repairs": repairs,
                "stale_memory_uses": sum(int(item.get("stale_memory_uses", 0)) for item in rows),
                "second_run_reuse": sum(bool(item.get("reused")) for item in rows),
                "questions": sum(int(item.get("questions", 0)) for item in rows),
                "rollback_verified": sum(bool(item.get("rollback_verified")) for item in rows),
                "accepted_suggestions": sum(item.get("accepted") is True for item in rows),
                "rejected_suggestions": sum(item.get("accepted") is False for item in rows)}


class LocalPresenceMesh:
    """Prepare explicit local-device handoffs without cloud synchronization."""

    def __init__(self, store: ExecutiveStore | str | None = None) -> None:
        self.store = store if isinstance(store, ExecutiveStore) else ExecutiveStore(store or "data/executive")

    def register(self, device_id: str, *, kind: str = "desktop", endpoint: str = "",
                 trusted: bool = False) -> dict[str, Any]:
        if not device_id.strip():
            raise ValueError("device_id is required")
        # Only local/loopback endpoints are retained.  The mesh never stores
        # credentials and never performs a network call by itself.
        allowed = not endpoint or endpoint.casefold().startswith(("127.0.0.1", "localhost", "192.168.", "10."))
        item = {"device_id": device_id.strip(), "kind": kind, "endpoint": endpoint if allowed else "",
                "trusted": bool(trusted and allowed), "updated_at": now_iso()}
        devices = [row for row in self.store.read("presence", []) if isinstance(row, dict) and row.get("device_id") != item["device_id"]]
        devices.append(item)
        self.store.write("presence", devices[-32:])
        return item

    def devices(self, *, trusted_only: bool = False) -> list[dict[str, Any]]:
        rows = [row for row in self.store.read("presence", []) if isinstance(row, dict)]
        return [row for row in rows if not trusted_only or row.get("trusted")]

    def prepare_handoff(self, goal: str, device_id: str) -> dict[str, Any]:
        device = next((row for row in self.devices(trusted_only=True) if row.get("device_id") == device_id), None)
        if device is None:
            return {"prepared": False, "reason": "untrusted_or_unknown_device"}
        return {"prepared": True, "device_id": device_id, "goal": " ".join((goal or "").split()),
                "endpoint": device.get("endpoint", ""), "network_action": False}
