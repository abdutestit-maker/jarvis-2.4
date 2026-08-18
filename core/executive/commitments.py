"""Promise and commitment memory with explicit status and low-noise reminders."""

from __future__ import annotations

import re
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional

from .models import Commitment, CommitmentStatus, CommitmentType, normalize_tokens, now_iso
from .store import ExecutiveStore


_TRIGGERS = re.compile(r"(?i)\b(не забудь|надо|нужно|сделаю|сделать|верн[её]мся|обещаю|напомни|до\s+\d{1,2}(?::\d{2})?)\b")
_TOMORROW = re.compile(r"(?i)\b(завтра|tomorrow)\b")
_DATE = re.compile(r"(?i)\bдо\s+(\d{1,2})(?::(\d{2}))?\b")


class CommitmentEngine:
    def __init__(self, store: ExecutiveStore | str | None = None) -> None:
        self.store = store if isinstance(store, ExecutiveStore) else ExecutiveStore(store or "data/executive")
        self._lock = threading.RLock()
        self._items: dict[str, Commitment] = {}
        self._load()

    def _load(self) -> None:
        raw = self.store.read("commitments", [])
        self._items = {str(item["id"]): Commitment.from_dict(item) for item in raw if isinstance(item, dict) and item.get("id")}

    def _save(self) -> None:
        self.store.write("commitments", [item.to_dict() for item in self._items.values()])

    def add(self, text: str, *, kind: CommitmentType | str = CommitmentType.INTENTION,
            due_at: Optional[str] = None, source: str = "user", confidence: float = 0.7,
            importance: float = 0.5, owner: str = "user", next_action: str = "") -> Commitment:
        clean = " ".join((text or "").split()).strip(" .,!?")
        if not clean:
            raise ValueError("commitment text is required")
        item = Commitment(text=clean, kind=CommitmentType(kind), due_at=due_at,
                          source=source, confidence=max(0.0, min(1.0, confidence)),
                          importance=max(0.0, min(1.0, importance)), owner=owner,
                          next_action=next_action)
        with self._lock:
            existing = self.find(clean)
            if existing:
                existing.confidence = min(1.0, existing.confidence + 0.1)
                existing.last_checked = now_iso()
                self._save()
                return existing
            self._items[item.id] = item
            self._save()
        return item

    def observe(self, text: str, *, source: str = "user") -> list[Commitment]:
        raw = " ".join((text or "").split())
        if not raw or not _TRIGGERS.search(raw):
            return []
        kind = CommitmentType.PROMISE if re.search(r"(?i)\b(обещаю|сделаю)\b", raw) else CommitmentType.INTENTION
        due = None
        if _TOMORROW.search(raw):
            due = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0).isoformat()
        else:
            match = _DATE.search(raw)
            if match:
                hour, minute = int(match.group(1)), int(match.group(2) or 0)
                now = datetime.now().astimezone()
                due = now.replace(hour=hour, minute=minute, second=0, microsecond=0).astimezone(timezone.utc).isoformat()
        cleaned = re.sub(r"(?i)^(не забудь|напомни)\s*", "", raw).strip()
        return [self.add(cleaned, kind=kind, due_at=due, source=source, confidence=0.75)]

    def find(self, text: str) -> Optional[Commitment]:
        tokens = normalize_tokens(text)
        if not tokens:
            return None
        candidates = [item for item in self._items.values() if item.status == CommitmentStatus.OPEN]
        return max(candidates, key=lambda item: len(tokens & normalize_tokens(item.text)), default=None)

    def open(self) -> list[Commitment]:
        return [item for item in self._items.values() if item.status == CommitmentStatus.OPEN]

    def complete(self, commitment_id: str) -> Optional[Commitment]:
        item = self._items.get(commitment_id)
        if item is None:
            return None
        item.status = CommitmentStatus.COMPLETED
        item.completed_at = now_iso()
        item.last_checked = item.completed_at
        self._save()
        return item

    def dismiss(self, commitment_id: str) -> Optional[Commitment]:
        item = self._items.get(commitment_id)
        if item is None:
            return None
        item.status = CommitmentStatus.DISMISSED
        item.last_checked = now_iso()
        self._save()
        return item

    def due_or_stale(self, *, now: Optional[datetime] = None) -> list[Commitment]:
        current = now or datetime.now(timezone.utc)
        result = []
        for item in self.open():
            if not item.due_at:
                continue
            try:
                due = datetime.fromisoformat(item.due_at)
                if due.tzinfo is None:
                    due = due.replace(tzinfo=timezone.utc)
                if due <= current:
                    result.append(item)
            except ValueError:
                continue
        return result


PromiseCommitmentEngine = CommitmentEngine

