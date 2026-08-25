"""ExecutiveMind façade integrating goals, commitments and verified outcomes."""

from __future__ import annotations

import re
from typing import Any, Optional

from .capability_graph import CapabilityGraph
from .commands import CommandOS
from .commitments import CommitmentEngine
from .goals import GoalGraph
from .learning import (
    AskOncePolicy, CounterfactualEngine, DemonstrationLearner, PersonalEvalLab,
    SemanticUndo, ShadowRehearsal, SleepMode, TemporalMemory,
    TwoSpeedCognition, LocalPresenceMesh,
)
from .models import ActionMode, CommandPlan, EvalCase, GoalNode, IntentContract, now_iso
from .store import ExecutiveStore
from .world import UnifiedWorldState


_ACTION_WORDS = re.compile(r"(?i)\b(открой|закрой|запусти|найди|поставь|сделай|создай|прочитай|проверь|настрой|установи|сравни|продолжи|подготовь|покажи|отмени|верни)\b")


class ExecutiveMind:
    """One local executive state owner; execution remains in existing Agent."""

    def __init__(self, root: str | Any = "data/executive", *, registry: Any = None,
                 capability_registry: Any = None, world_observer: Any = None) -> None:
        self.store = ExecutiveStore(root)
        self.goals = GoalGraph(self.store)
        self.commitments = CommitmentEngine(self.store)
        self.world = UnifiedWorldState(self.store, observer=world_observer)
        self.commands = CommandOS()
        self.capabilities = CapabilityGraph(capability_registry, registry)
        self.demonstrations = DemonstrationLearner(self.store)
        self.rehearsal = ShadowRehearsal()
        self.two_speed = TwoSpeedCognition()
        self.temporal = TemporalMemory(self.store)
        self.sleep_mode = SleepMode()
        self.undo = SemanticUndo(self.store)
        self.ask_once = AskOncePolicy()
        self.counterfactual = CounterfactualEngine()
        self.evals = PersonalEvalLab(self.store)
        self.presence = LocalPresenceMesh(self.store)
        # Named aliases keep the façade discoverable for integrations while
        # the short attributes remain convenient for internal callers.
        self.goal_graph = self.goals
        self.promise_engine = self.commitments
        self.world_state = self.world
        self.command_os = self.commands
        self.capability_graph = self.capabilities

    def begin_turn(self, raw: str, intent: Optional[str] = None, *, source: str = "user") -> IntentContract:
        text = " ".join((raw or "").split())
        resolved = intent or "none"
        mode = self.commands.mode_for(text)
        contract = IntentContract(raw=text, intent=resolved, goal=text, mode=mode,
                                  confidence=0.9 if resolved != "none" else 0.5, source=source)
        if text and (resolved not in {"none", "conversation"} or _ACTION_WORDS.search(text)):
            self.goals.upsert(text, source=source, confidence=contract.confidence,
                              priority=0.7 if mode == ActionMode.DELIBERATE else 0.5)
        self.commitments.observe(text, source=source)
        return contract

    def complete_turn(self, contract: IntentContract | str, *, verified: bool,
                      result: str = "", tool: Optional[str] = None, mode: str = "",
                      desired_state: Optional[dict[str, Any]] = None,
                      actual_state: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        goal_text = contract.goal if isinstance(contract, IntentContract) else str(contract)
        node = self.goals.resume(goal_text)
        if node and verified:
            self.goals.mark(node.id, "completed", verified=True)
        elif node and not verified and mode not in {"conversation", "empty"}:
            self.goals.mark(node.id, "active", next_action="повторно проверить способ")
        if tool:
            self.world.observe(f"tool.{tool}", {"goal": goal_text, "result": str(result)[:300], "verified": verified},
                               source="agent", confidence=1.0 if verified else 0.4)
        if desired_state is not None:
            self.world.observe(f"goal.{node.id if node else goal_text}", desired_state,
                               source="verified_state" if verified else "observed_state",
                               confidence=1.0 if verified else 0.5)
        self.evals.record(EvalCase(name=tool or mode or "conversation", goal=goal_text),
                          result=str(result)[:300], verified=verified)
        return {"verified": verified, "goal_id": node.id if node else None,
                "tool": tool, "diff": self.goals.diff(node.id, actual_state or {}) if node and actual_state else {}}

    def compile(self, goal: str, *, intent: str = "none", tool: Optional[str] = None,
                args: Optional[dict[str, Any]] = None, desired_state: Optional[dict[str, Any]] = None,
                constraints: Optional[list[str]] = None, risk: str = "low") -> CommandPlan:
        return self.commands.compile(goal, intent=intent, tool=tool, args=args,
                                     desired_state=desired_state, constraints=constraints, risk=risk)

    def rehearse(self, plan: CommandPlan, current_state: Optional[dict[str, Any]] = None):
        return self.rehearsal.rehearse(plan, current_state)

    def context_for(self, query: str, *, limit: int = 4) -> str:
        tokens = set(re.findall(r"[\w-]{2,}", (query or "").casefold(), flags=re.UNICODE))
        parts: list[str] = []
        goals = self.goals.open()
        goals.sort(key=lambda node: (len(tokens & set(re.findall(r"[\w-]{2,}", node.title.casefold()))) if tokens else 0, node.priority), reverse=True)
        for node in goals[:limit]:
            blockers = self.goals.blockers(node)
            parts.append(f"goal: {node.title} ({node.status.value})" + (f"; blockers={len(blockers)}" if blockers else ""))
        for item in self.commitments.open()[:max(1, limit // 2)]:
            parts.append(f"commitment: {item.text}")
        for item in self.temporal.current(query, limit=limit):
            parts.append(f"memory: {item['fact']} [confidence={item.get('confidence', 0):.2f}]")
        return "\n".join(parts[:limit])

    def sleep(self) -> dict[str, Any]:
        return self.sleep_mode.run(temporal=self.temporal)

    def snapshot(self) -> dict[str, Any]:
        priority = self.goals.current_priority()
        return {"active_goal": priority.to_dict() if priority else None,
                "open_goals": len(self.goals.open()),
                "open_commitments": len(self.commitments.open()),
                "world_facts": len(self.world.current()),
                "eval": self.evals.summary(),
                "capabilities": len(self.capabilities.all())}
