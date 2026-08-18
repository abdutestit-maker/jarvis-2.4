"""Unified local world state with provenance, freshness and state diffs."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Optional

from .models import WorldFact, now_iso
from .store import ExecutiveStore


def _parse(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


class UnifiedWorldState:
    def __init__(self, store: ExecutiveStore | str | None = None) -> None:
        self.store = store if isinstance(store, ExecutiveStore) else ExecutiveStore(store or "data/executive")
        self._lock = threading.RLock()
        raw = self.store.read("world", [])
        self._facts = {str(item["key"]): WorldFact.from_dict(item) for item in raw if isinstance(item, dict) and item.get("key")}

    def _save(self) -> None:
        self.store.write("world", [fact.to_dict() for fact in self._facts.values()])

    def observe(self, key: str, value: Any, *, source: str, confidence: float = 0.7,
                valid_until: Optional[str] = None, volatility: str = "normal") -> WorldFact:
        key = " ".join((key or "").split()).strip()
        if not key:
            raise ValueError("world fact key is required")
        with self._lock:
            previous = self._facts.get(key)
            fact = WorldFact(key=key, value=value, source=source, confidence=max(0.0, min(1.0, confidence)),
                             valid_until=valid_until, volatility=volatility,
                             supersedes=previous.observed_at if previous else None)
            self._facts[key] = fact
            self._save()
            return fact

    update = observe

    def get(self, key: str, *, include_expired: bool = False) -> Optional[WorldFact]:
        fact = self._facts.get(key)
        if fact is None:
            return None
        if not include_expired and self._expired(fact):
            return None
        return fact

    def current(self) -> dict[str, WorldFact]:
        return {key: fact for key, fact in self._facts.items() if not self._expired(fact)}

    def snapshot(self) -> dict[str, Any]:
        return {key: fact.value for key, fact in self.current().items()}

    def diff_since(self, since: str | datetime) -> list[dict[str, Any]]:
        moment = _parse(since) if isinstance(since, str) else since
        if moment is None:
            return []
        return [fact.to_dict() for fact in self._facts.values()
                if (_parse(fact.observed_at) or moment) > moment and not self._expired(fact)]

    def expire(self, *, now: Optional[datetime] = None) -> int:
        current = now or datetime.now(timezone.utc)
        expired = [key for key, fact in self._facts.items() if (deadline := _parse(fact.valid_until)) and deadline <= current]
        for key in expired:
            self._facts.pop(key, None)
        if expired:
            self._save()
        return len(expired)

    @staticmethod
    def _expired(fact: WorldFact) -> bool:
        deadline = _parse(fact.valid_until)
        return bool(deadline and deadline <= datetime.now(timezone.utc))


WorldState = UnifiedWorldState

