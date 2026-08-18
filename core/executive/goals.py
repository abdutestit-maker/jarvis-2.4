"""Persistent Goal Graph with dependencies and verified resume."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from .models import GoalNode, GoalStatus, normalize_tokens, now_iso
from .store import ExecutiveStore


class GoalGraph:
    def __init__(self, store: ExecutiveStore | str | None = None) -> None:
        self.store = store if isinstance(store, ExecutiveStore) else ExecutiveStore(store or "data/executive")
        self._lock = threading.RLock()
        self._goals: dict[str, GoalNode] = {}
        self._load()

    def _load(self) -> None:
        raw = self.store.read("goals", [])
        if isinstance(raw, dict):
            raw = list(raw.values())
        self._goals = {str(item["id"]): GoalNode.from_dict(item) for item in raw if isinstance(item, dict) and item.get("id")}

    def _save(self) -> None:
        self.store.write("goals", [goal.to_dict() for goal in self._goals.values()])

    def add(self, title: str, *, desired_state: Optional[dict[str, Any]] = None,
            constraints: Optional[Iterable[str]] = None, parent_id: Optional[str] = None,
            dependencies: Optional[Iterable[str]] = None, deadline: Optional[str] = None,
            source: str = "user", confidence: float = 0.6, priority: float = 0.5) -> GoalNode:
        title = " ".join((title or "").split())
        if not title:
            raise ValueError("goal title is required")
        node = GoalNode(title=title, desired_state=dict(desired_state or {}),
                        constraints=list(constraints or []), parent_id=parent_id,
                        dependencies=list(dependencies or []), deadline=deadline,
                        source=source, confidence=max(0.0, min(1.0, confidence)),
                        priority=max(0.0, min(1.0, priority)))
        with self._lock:
            self._goals[node.id] = node
            self._save()
        return node

    def upsert(self, title: str, **kwargs: Any) -> GoalNode:
        tokens = normalize_tokens(title)
        with self._lock:
            for node in self.open():
                if tokens and len(tokens & normalize_tokens(node.title)) >= max(1, min(3, len(tokens))):
                    node.updated_at = now_iso()
                    if kwargs.get("desired_state"):
                        node.desired_state.update(kwargs["desired_state"])
                    self._save()
                    return node
        return self.add(title, **kwargs)

    def get(self, goal_id: str) -> Optional[GoalNode]:
        return self._goals.get(goal_id)

    def all(self) -> list[GoalNode]:
        with self._lock:
            return list(self._goals.values())

    def open(self) -> list[GoalNode]:
        return [node for node in self._goals.values()
                if node.status in {GoalStatus.OPEN, GoalStatus.ACTIVE, GoalStatus.PAUSED, GoalStatus.BLOCKED}]

    def blockers(self, node: GoalNode | str) -> list[str]:
        current = self.get(node) if isinstance(node, str) else node
        if current is None:
            return []
        return [dep for dep in current.dependencies
                if (self._goals.get(dep) is None or self._goals[dep].status != GoalStatus.COMPLETED)]

    def mark(self, goal_id: str, status: GoalStatus | str, *, next_action: Optional[str] = None,
             verified: bool = False) -> Optional[GoalNode]:
        with self._lock:
            node = self._goals.get(goal_id)
            if node is None:
                return None
            node.status = GoalStatus(status)
            if next_action is not None:
                node.next_action = next_action
            node.updated_at = now_iso()
            if verified:
                node.last_verified = node.updated_at
                node.confidence = min(1.0, node.confidence + 0.1)
            self._save()
            return node

    def resume(self, hint: str = "") -> Optional[GoalNode]:
        candidates = [node for node in self.open() if not self.blockers(node)]
        if not candidates:
            return None
        hint_tokens = normalize_tokens(hint)
        def score(node: GoalNode) -> tuple[float, float, str]:
            overlap = len(hint_tokens & normalize_tokens(node.title))
            age = node.updated_at or node.created_at
            return (overlap * 2.0 + node.priority + (0.3 if node.last_verified else 0.0), node.confidence, age)
        return max(candidates, key=score)

    def current_priority(self) -> Optional[GoalNode]:
        return self.resume()

    def diff(self, goal_id: str, actual: dict[str, Any]) -> dict[str, Any]:
        node = self.get(goal_id)
        expected = node.desired_state if node else {}
        return {key: {"expected": expected.get(key), "actual": actual.get(key)}
                for key in set(expected) | set(actual) if expected.get(key) != actual.get(key)}

