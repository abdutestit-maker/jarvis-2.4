"""Local, quality-controlled storage for non-sensitive interaction preferences."""

from __future__ import annotations

import json
import re
import threading
import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from core.memory.relationship.models import RelationshipMemory
from core.memory.secret_filter import contains_secret_or_raw, sanitize_for_memory
from core.security.atomic import atomic_json_write, load_json

_SENSITIVE = re.compile(
    r"(?i)\b(диагноз|медицинск|здоровь|религи|вероисповед|политическ|"
    r"биометр|паспорт|номер\s+карты|банковск|точн(?:ый|ого)\s+адрес|"
    r"sexual|medical|diagnosis|religion|political|biometric|passport)\b"
)
_DIRECT_IDENTIFIER = re.compile(
    r"(?i)([\w.+-]+@[\w.-]+\.[a-z]{2,}|(?:\+?\d[\d\s()\-]{7,}\d))"
)
_WORD = re.compile(r"[\wа-яё]+", re.IGNORECASE)
_GLOBAL_PREFERENCES = {
    "communication_style", "prefers_action_over_explanation", "humor_preference",
    "likes_confirmation", "preferred_address", "technical_level",
}


def _utc(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    return current if current.tzinfo else current.replace(tzinfo=timezone.utc)


def _tokens(value: str) -> set[str]:
    return {word.casefold()[:5] for word in _WORD.findall(value) if len(word) >= 3}


class RelationshipMemoryStore:
    """Atomic JSON store with confidence reinforcement, expiry and retrieval bounds."""

    def __init__(self, directory: Path | str, *, max_records: int = 300) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "memories.json"
        self.max_records = max(1, int(max_records))
        self._lock = threading.RLock()

    def remember(self, fact: str, *, source: str, confidence: float,
                 importance: float, category: str = "preference", key: str = "",
                 ttl_days: int = 365, now: datetime | None = None) -> RelationshipMemory | None:
        raw = " ".join(str(fact or "").split())
        if (not raw or contains_secret_or_raw(raw) or _SENSITIVE.search(raw)
                or _DIRECT_IDENTIFIER.search(raw)):
            return None
        clean = sanitize_for_memory(raw)[:500]
        if not clean or "***" in clean:
            return None
        moment = _utc(now)
        stamp = moment.isoformat()
        expires = (moment + timedelta(days=max(1, int(ttl_days)))).isoformat()
        normalized_key = " ".join((key or clean).casefold().split())[:160]
        incoming_confidence = max(0.0, min(1.0, float(confidence)))
        incoming_importance = max(0.0, min(1.0, float(importance)))
        with self._lock:
            records = self._load()
            previous = next((item for item in records if item.key == normalized_key), None)
            if previous is None:
                saved = RelationshipMemory(
                    id=uuid.uuid4().hex, fact=clean, source=str(source)[:80],
                    confidence=round(incoming_confidence, 3), last_confirmed=stamp,
                    importance=round(incoming_importance, 3), category=str(category)[:40],
                    key=normalized_key, created_at=stamp, expires_at=expires,
                )
                records.append(saved)
            else:
                same_fact = previous.fact.casefold() == clean.casefold()
                reinforced = (1 - (1 - previous.confidence) * (1 - incoming_confidence * 0.5)
                              if same_fact else incoming_confidence)
                saved = replace(
                    previous, fact=clean, source=str(source)[:80],
                    confidence=round(max(0.0, min(1.0, reinforced)), 3),
                    importance=round(max(previous.importance, incoming_importance), 3),
                    last_confirmed=stamp, expires_at=expires, category=str(category)[:40],
                )
                records = [saved if item.id == previous.id else item for item in records]
            records.sort(key=lambda item: item.last_confirmed)
            self._save(records[-self.max_records:])
            return saved

    def all_memories(self, *, now: datetime | None = None,
                     include_expired: bool = False) -> list[RelationshipMemory]:
        moment = _utc(now)
        with self._lock:
            values = self._load()
        if include_expired:
            return values
        return [item for item in values if not self._expired(item, moment)]

    def retrieve(self, query: str, *, limit: int = 4, min_confidence: float = 0.35,
                 now: datetime | None = None) -> list[RelationshipMemory]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []
        scored: list[tuple[float, RelationshipMemory]] = []
        for item in self.all_memories(now=now):
            if item.confidence < min_confidence:
                continue
            overlap = len(query_tokens & _tokens(f"{item.key} {item.fact}")) / len(query_tokens)
            if overlap <= 0 and item.key in _GLOBAL_PREFERENCES:
                overlap = 0.25
            if overlap <= 0:
                continue
            score = 0.6 * overlap + 0.25 * item.confidence + 0.15 * item.importance
            scored.append((score, item))
        scored.sort(key=lambda pair: (pair[0], pair[1].last_confirmed), reverse=True)
        return [item for _, item in scored[:max(0, min(10, int(limit)))]]

    def prune(self, *, now: datetime | None = None) -> int:
        moment = _utc(now)
        with self._lock:
            records = self._load()
            kept = [item for item in records if not self._expired(item, moment)]
            removed = len(records) - len(kept)
            if removed:
                self._save(kept)
            return removed

    @staticmethod
    def _expired(item: RelationshipMemory, now: datetime) -> bool:
        try:
            expiry = datetime.fromisoformat(item.expires_at)
            expiry = expiry if expiry.tzinfo else expiry.replace(tzinfo=timezone.utc)
            return expiry <= now
        except (TypeError, ValueError):
            return True

    def _load(self) -> list[RelationshipMemory]:
        try:
            payload = load_json(self.path, default={})
            records: Iterable[dict] = payload.get("memories") or []
            return [RelationshipMemory.from_dict(item) for item in records if isinstance(item, dict)]
        except (OSError, TypeError, ValueError):
            return []

    def _save(self, records: list[RelationshipMemory]) -> None:
        atomic_json_write(self.path, {"version": 1, "memories": [item.to_dict() for item in records]})
