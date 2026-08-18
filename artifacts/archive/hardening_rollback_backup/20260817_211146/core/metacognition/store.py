"""Bounded local persistence for safe structured beliefs."""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any

from core.memory.secret_filter import sanitize_for_memory
from core.security.atomic import atomic_json_write, load_json
from core.security.redaction import redact
from core.metacognition.models import Belief


def safe_value(value: Any) -> Any:
    return redact(value)


class BeliefStore:
    def __init__(self, directory: Path | str, *, max_beliefs: int = 500) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "beliefs.json"
        self.max_beliefs = max(1, int(max_beliefs))
        self._lock = threading.RLock()

    def get(self, key: str) -> Belief | None:
        normalized = self._key(key)
        return next((item for item in self.all() if item.key == normalized), None)

    def all(self) -> list[Belief]:
        try:
            payload = load_json(self.path, default={})
            return [Belief.from_dict(item) for item in payload.get("beliefs", ())
                    if isinstance(item, dict)]
        except (OSError, TypeError, ValueError):
            return []

    def upsert(self, belief: Belief) -> Belief:
        belief.key = self._key(belief.key)
        belief.claim = sanitize_for_memory(belief.claim)[:500]
        belief.value = safe_value(belief.value)
        belief.contradictions = [sanitize_for_memory(item)[:300]
                                 for item in belief.contradictions if sanitize_for_memory(item)]
        belief.supersedes = [sanitize_for_memory(item)[:160]
                             for item in belief.supersedes if sanitize_for_memory(item)]
        for item in belief.evidence_refs:
            item.ref_id = sanitize_for_memory(item.ref_id)[:160]
            item.origin_id = sanitize_for_memory(item.origin_id)[:160]
        with self._lock:
            beliefs = [item for item in self.all() if item.key != belief.key]
            beliefs.append(belief)
            beliefs.sort(key=lambda item: item.updated_at)
            self._write(beliefs[-self.max_beliefs:])
        return Belief.from_dict(belief.to_dict())

    def _write(self, beliefs: list[Belief]) -> None:
        atomic_json_write(self.path, {"version": 1, "beliefs": [item.to_dict() for item in beliefs]})

    @staticmethod
    def _key(value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_.:-]+", "_", (value or "unknown").strip())[:160] or "unknown"


__all__ = ["BeliefStore", "safe_value"]
