"""Contextual failure episodes that avoid repeating a proven bad strategy."""

from __future__ import annotations

import hashlib
import json
import re
import threading
import uuid
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

from core.memory.secret_filter import sanitize_for_memory
from core.metacognition.models import utcnow
from core.metacognition.store import safe_value
from core.security.atomic import atomic_json_write, load_json


def fingerprint_environment(environment: dict[str, Any]) -> str:
    safe = safe_value(environment)
    encoded = json.dumps(safe, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:24]


@dataclass
class FailureEpisode:
    goal: str
    task_class: str
    strategy: str
    failure_category: str
    observed_mismatch: dict[str, Any]
    environment_fingerprint: str
    confidence: float
    successful_repair: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    episode_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FailureEpisodeStore:
    def __init__(self, directory: Path | str, *, max_episodes: int = 300) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "failure_episodes.json"
        self.max_episodes = max(1, int(max_episodes))
        self._lock = threading.RLock()

    def record(self, episode: FailureEpisode) -> FailureEpisode:
        category = sanitize_for_memory(episode.failure_category)[:160]
        if re.search(r"(?i)(traceback|exception|\berror\b)", category):
            category = "execution_failure"
        safe = FailureEpisode(
            goal=sanitize_for_memory(episode.goal)[:300],
            task_class=sanitize_for_memory(episode.task_class)[:120] or "unknown",
            strategy=sanitize_for_memory(episode.strategy)[:160] or "unknown",
            failure_category=category or "execution_failure",
            observed_mismatch=safe_value(episode.observed_mismatch),
            environment_fingerprint=sanitize_for_memory(episode.environment_fingerprint)[:100],
            confidence=max(0.0, min(1.0, float(episode.confidence))),
            successful_repair=sanitize_for_memory(episode.successful_repair)[:160],
            evidence_refs=[sanitize_for_memory(item)[:160] for item in episode.evidence_refs
                           if sanitize_for_memory(item)],
            episode_id=episode.episode_id, created_at=episode.created_at,
        )
        with self._lock:
            items = [item for item in self.all() if item.episode_id != safe.episode_id]
            items.append(safe)
            items.sort(key=lambda item: item.created_at)
            self._write(items[-self.max_episodes:])
        return safe

    def all(self) -> list[FailureEpisode]:
        try:
            payload = load_json(self.path, default={})
            return [FailureEpisode(**item) for item in payload.get("episodes", ())
                    if isinstance(item, dict)]
        except (OSError, TypeError, ValueError):
            return []

    def retrieve(self, task_class: str, environment_fingerprint: str,
                 *, limit: int = 10) -> list[FailureEpisode]:
        matches = [
            item for item in self.all()
            if item.task_class == task_class
            and item.environment_fingerprint == environment_fingerprint
        ]
        return matches[-max(0, int(limit)):]

    def avoid_strategies(self, task_class: str, environment_fingerprint: str) -> set[str]:
        return {
            item.strategy for item in self.retrieve(task_class, environment_fingerprint)
            if item.confidence >= 0.6
        }

    def mark_repair(self, episode_ids: list[str], repair: str) -> list[FailureEpisode]:
        ids = set(episode_ids)
        changed = []
        items = []
        for item in self.all():
            if item.episode_id in ids:
                item = replace(item, successful_repair=sanitize_for_memory(repair)[:160])
                changed.append(item)
            items.append(item)
        with self._lock:
            self._write(items)
        return changed

    def _write(self, episodes: list[FailureEpisode]) -> None:
        atomic_json_write(self.path, {"version": 1, "episodes": [item.to_dict() for item in episodes]})


__all__ = ["FailureEpisode", "FailureEpisodeStore", "fingerprint_environment"]
