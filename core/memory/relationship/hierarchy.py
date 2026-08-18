"""Bounded retrieval across working, session, long-term and relationship layers."""

from __future__ import annotations

from typing import Any, Callable

from core.memory.relationship.models import MemoryContext
from core.memory.relationship.store import RelationshipMemoryStore
from core.memory.short_term import SessionManager


class WorkingMemory:
    def __init__(self) -> None:
        self._values: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        if key:
            self._values[str(key)] = value

    def update(self, values: dict[str, Any]) -> None:
        for key, value in values.items():
            self.set(str(key), value)

    def snapshot(self) -> dict[str, Any]:
        return dict(self._values)

    def clear(self) -> None:
        self._values.clear()


class MemoryHierarchy:
    def __init__(self, relationship: RelationshipMemoryStore, *,
                 session: SessionManager | None = None,
                 long_term: Callable[[str, int], list[str]] | None = None) -> None:
        self.relationship_store = relationship
        self.session_store = session or SessionManager(max_size=20)
        self.long_term_retriever = long_term
        self.working = WorkingMemory()

    def retrieve(self, query: str, *, max_chars: int = 1200,
                 relationship_limit: int = 4, session_limit: int = 6) -> MemoryContext:
        long_term: list[str] = []
        if self.long_term_retriever is not None:
            try:
                long_term = [str(item)[:240] for item in self.long_term_retriever(query, 3)][:3]
            except Exception:
                long_term = []
        context = MemoryContext(
            working=self.working.snapshot(),
            session=self.session_store.get_recent(session_limit),
            long_term=long_term,
            relationship=self.relationship_store.retrieve(query, limit=relationship_limit),
        )
        # Keep the public result typed; prompt material is independently bounded by to_prompt().
        context.to_prompt(max_chars=max_chars)
        return context

