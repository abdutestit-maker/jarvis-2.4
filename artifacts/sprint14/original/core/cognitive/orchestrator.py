"""High-level coordinator joining existing ATLAS subsystems into one turn."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.cognitive.addressing import AddressFormStore, AddressMatch, AddressRecognizer
from core.cognitive.continuity import ContinuityResolver, GoalStack
from core.cognitive.models import CurrentMindState, GoalFrame
from core.cognitive.self_model import CapabilitySelfModel
from core.cognitive.state import MindStateStore
from core.voice.tts_sanitizer import sanitize_for_tts


_ACTION = re.compile(
    r"(?i)\b(сделай|создай|подготов|организ|настро(?!ени)|установ|открой|закрой|"
    r"найди|проверь|исправ|измени|запусти|удали|скачай|перемест|запиши)\w*"
)


@dataclass
class CognitiveTurn:
    text: str
    addressed: bool
    action: str
    goal: str = ""
    response: str = ""
    confidence: float = 0.0
    evidence: tuple[str, ...] = ()
    memory_refs: tuple[str, ...] = ()
    plan: Any = None


class CognitiveOrchestrator:
    """Coordinates state, memory, planning, risk and verified outcomes.

    It owns no replacement tools or models. Execution remains in the existing
    Capability Engine/Operator/Agent; this layer selects and joins their facts.
    """

    def __init__(self, directory: Path | str, *, registry: Any,
                 capability_registry: Any = None, providers: dict[str, Any] | None = None,
                 task_runtime: Any = None, living_context: Any = None,
                 memory_hierarchy: Any = None, capability_planner: Any = None,
                 capability_engine: Any = None, personality: Any = None,
                 risk_policy: Any = None, address_recognizer: AddressRecognizer | None = None,
                 shadow_engine: Any = None, attention_manager: Any = None,
                 goal_tracker: Any = None) -> None:
        root = Path(directory)
        root.mkdir(parents=True, exist_ok=True)
        self.store = MindStateStore(root / "state")
        self.goal_stack = GoalStack(root / "continuity")
        self.continuity = ContinuityResolver(self.goal_stack)
        self.addressing = address_recognizer or AddressRecognizer(AddressFormStore(root / "addressing"))
        self.risk_policy = risk_policy or self._default_risk_policy()
        self.self_model = CapabilitySelfModel(
            registry, capability_registry=capability_registry,
            providers=providers, risk_policy=self.risk_policy,
        )
        self.registry = registry
        self.task_runtime = task_runtime
        self.living_context = living_context
        self.memory_hierarchy = memory_hierarchy
        self.capability_planner = capability_planner
        self.capability_engine = capability_engine
        self.personality = personality
        # References to the existing owners are intentional: the coordinator
        # consults them but does not reimplement their policies.
        self.shadow_engine = shadow_engine
        self.attention_manager = attention_manager
        self.goal_tracker = goal_tracker
        self.state = self.store.reconstruct(
            task_runtime=task_runtime, living_context=living_context,
        )

    @staticmethod
    def _default_risk_policy() -> Any:
        from core.capability_engine import RiskConfidencePolicy
        return RiskConfidencePolicy()

    def begin_interaction(self, text: str, *, channel: str = "text",
                          implicit_address: bool = False) -> CognitiveTurn:
        raw = (text or "").strip()
        match = self.addressing.recognize(
            raw, conversational_context=self.state.interaction_mode != "idle",
        )
        addressed = bool(implicit_address or match.addressed_to_atlas)
        if not addressed:
            return CognitiveTurn(raw, False, "wait", confidence=match.confidence,
                                 evidence=match.evidence)
        if match.addressed_to_atlas:
            self.addressing.confirm(match, accepted=True)
        command = match.remaining_text if match.addressed_to_atlas and match.remaining_text else raw

        continuation = self.continuity.resolve(command, self.state)
        if continuation.action == "clarify":
            self.state.pending_user_question = continuation.question
            self.store.save(self.state)
            return CognitiveTurn(command, True, "clarify", response=continuation.question,
                                 confidence=continuation.confidence,
                                 evidence=continuation.evidence)
        if continuation.action != "none":
            frames = {frame.goal_id: frame for frame in self.goal_stack.frames()}
            frame = frames.get(continuation.goal_id)
            self.state.current_goal = continuation.goal
            self.state.active_task = frame.active_task if frame else self.state.active_task
            self.state.mission_state = "executing" if continuation.action != "status" else "paused"
            self.state.pending_user_question = ""
            self.state.confidence = continuation.confidence
            self.store.save(self.state)
            return CognitiveTurn(
                command, True, continuation.action, continuation.goal,
                confidence=continuation.confidence, evidence=continuation.evidence,
            )

        self_answer = self.self_model.answer(command, self.state)
        if self_answer.known:
            return CognitiveTurn(
                command, True, "self_knowledge", response=self_answer.text,
                confidence=1.0, evidence=self_answer.evidence,
            )

        memory_refs = self._retrieve_memory_refs(command)
        if not _ACTION.search(command):
            self.state.interaction_mode = "conversation"
            self.state.recalled_memory_refs = list(memory_refs)
            self.store.save(self.state)
            return CognitiveTurn(command, True, "conversation", response="Я здесь.",
                                 confidence=max(0.75, match.confidence),
                                 memory_refs=memory_refs)

        self.state.current_goal = command
        self.state.active_task = "select capability"
        self.state.mission_state = "planning"
        self.state.interaction_mode = "work"
        self.state.recalled_memory_refs = list(memory_refs)
        self.state.confidence = max(0.7, match.confidence)
        plan = self.capability_planner.plan(command) if self.capability_planner else None
        if plan is None:
            self.store.save(self.state)
            return CognitiveTurn(command, True, "delegate", command, confidence=self.state.confidence,
                                 memory_refs=memory_refs)
        if getattr(plan, "acquisition", "") == "research" or not getattr(plan, "steps", []):
            self.state.active_task = "research capability"
            self.state.mission_state = "researching"
            self.store.save(self.state)
            return CognitiveTurn(command, True, "research", command, "Сейчас разберусь.",
                                 self.state.confidence, memory_refs=memory_refs, plan=plan)
        decision = self.risk_policy.decide(
            confidence=float(getattr(plan, "confidence", 0.0)),
            risk=str(getattr(plan, "risk_class", "medium")),
        )
        if getattr(decision, "action", "") == "confirm":
            self.state.mission_state = "waiting_for_user"
            self.state.pending_user_question = "Подтвердите выполнение операции."
            self.store.save(self.state)
            return CognitiveTurn(command, True, "confirm", command,
                                 "Мне потребуется ваше подтверждение.",
                                 float(getattr(plan, "confidence", 0.0)),
                                 (str(getattr(decision, "reason", "risk gate")),),
                                 memory_refs, plan)
        self.state.active_task = "execute plan"
        self.state.mission_state = "executing"
        self.store.save(self.state)
        return CognitiveTurn(command, True, "execute", command, "Уже смотрю.",
                             float(getattr(plan, "confidence", 0.0)),
                             (str(getattr(decision, "reason", "")),), memory_refs, plan)

    def execute(self, turn: CognitiveTurn) -> tuple[str, Any]:
        if turn.action != "execute" or turn.plan is None or self.capability_engine is None:
            raise ValueError("turn has no executable capability plan")
        report = self.capability_engine.execute(turn.plan)
        return self.complete_execution(turn, report), report

    def complete_execution(self, turn: CognitiveTurn, report: Any) -> str:
        verification = getattr(report, "verification", None)
        verified = bool(
            getattr(report, "completed", False)
            and getattr(verification, "verified", False)
        )
        if getattr(report, "needs_confirmation", False):
            self.state.mission_state = "waiting_for_user"
            self.store.observe_result(
                self.state, result="", verified=False,
                pending=["user confirmation"],
            )
            return "Мне потребуется ваше подтверждение."
        if verified:
            observed = getattr(verification, "observed", {})
            episode = getattr(report, "episode", None)
            result = f"desired state verified: {sorted(observed)}"
            evidence = [f"capability_episode:{getattr(episode, 'episode_id', '')}"] if episode else []
            self.state.mission_state = "completed"
            self.store.observe_result(
                self.state, result=result, verified=True, evidence=evidence,
            )
            if self.state.active_mission_id:
                self.goal_stack.remove(self.state.active_mission_id)
            return "Готово. Проверил — работает."
        missing = getattr(verification, "missing", {}) if verification is not None else {}
        pending = [str(item) for item in (missing or {"result": "independent verification"})]
        self.state.mission_state = "verifying"
        self.store.observe_result(self.state, result=str(getattr(report, "state", "")),
                                  verified=False, pending=pending)
        return "Действие выполнено, результат ещё проверяю."

    def record_external_outcome(self, *, goal: str, result: str,
                                verified: bool, pending: list[str] | None = None,
                                mission_id: str = "") -> None:
        self.state.current_goal = goal or self.state.current_goal
        self.state.active_mission_id = mission_id or self.state.active_mission_id
        self.state.mission_state = "completed" if verified else "verifying"
        self.store.observe_result(
            self.state, result=result, verified=verified, pending=pending or [],
        )

    def suspend_current(self) -> GoalFrame | None:
        if not self.state.current_goal:
            return None
        goal_id = self.state.active_mission_id or f"goal-{abs(hash(self.state.current_goal))}"
        frame = GoalFrame(goal_id, self.state.current_goal, self.state.active_task)
        self.goal_stack.suspend(frame)
        self.state.current_goal = ""
        self.state.active_task = ""
        self.state.mission_state = "suspended"
        self.store.save(self.state)
        return frame

    def speech_text(self, text: str) -> str:
        return sanitize_for_tts(text, fallback="")

    def _retrieve_memory_refs(self, query: str) -> tuple[str, ...]:
        if self.memory_hierarchy is None:
            return ()
        try:
            context = self.memory_hierarchy.retrieve(query, max_chars=800,
                                                     relationship_limit=4, session_limit=4)
        except Exception:
            return ()
        refs = [
            f"relationship:{item.id}" for item in getattr(context, "relationship", ())[:4]
            if getattr(item, "id", "")
        ]
        return tuple(refs)


__all__ = ["CognitiveOrchestrator", "CognitiveTurn"]
