"""Persistent, secret-safe semantic knowledge about explored applications."""

from __future__ import annotations

import json
import re
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.security.redaction import redact
from core.security.atomic import atomic_json_write, load_json


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("._")
    return cleaned[:120] or "application"


_SECRET_WORDS = ("password", "passwd", "secret", "token", "api key", "api_key", "credential")


def _redact(value: Any, *, sensitive: bool = False) -> Any:
    if isinstance(value, dict):
        label = " ".join(str(value.get(key, "")) for key in ("name", "label", "automation_id"))
        node_sensitive = sensitive or any(word in label.casefold() for word in _SECRET_WORDS)
        result = {}
        for key, item in value.items():
            key_sensitive = node_sensitive or any(word.replace(" ", "_") in key.casefold()
                                                  for word in _SECRET_WORDS)
            result[key] = "[REDACTED]" if key == "value" and node_sensitive else _redact(
                item, sensitive=key_sensitive,
            )
        return result
    if isinstance(value, list):
        return [_redact(item, sensitive=sensitive) for item in value]
    if sensitive and isinstance(value, str) and value:
        return "[REDACTED]"
    return redact(value)


@dataclass
class AppKnowledge:
    application: str
    executable: str = ""
    windows: list[dict[str, Any]] = field(default_factory=list)
    menus: list[dict[str, Any]] = field(default_factory=list)
    settings: list[dict[str, Any]] = field(default_factory=list)
    controls: list[dict[str, Any]] = field(default_factory=list)
    successful_selectors: dict[str, dict[str, Any]] = field(default_factory=dict)
    settings_locations: dict[str, list[str]] = field(default_factory=dict)
    best_execution_method: str = "uia"
    fallback_method: str = "vision"
    verification_rules: list[dict[str, Any]] = field(default_factory=list)
    software: dict[str, Any] = field(default_factory=dict)
    discovery_steps: int = 0
    reuse_count: int = 0
    updated_at: str = field(default_factory=_now)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppKnowledge":
        allowed = {key: data[key] for key in cls.__dataclass_fields__ if key in data}
        return cls(**allowed)


class AppKnowledgeStore:
    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def path_for(self, application: str) -> Path:
        return self.directory / f"{_safe_id(application)}.json"

    def save(self, knowledge: AppKnowledge) -> Path:
        knowledge.updated_at = _now()
        target = self.path_for(knowledge.application)
        payload = _redact(asdict(knowledge))
        with self._lock:
            atomic_json_write(target, payload)
        return target

    def load(self, application: str) -> AppKnowledge | None:
        try:
            data = load_json(self.path_for(application), default={})
            return AppKnowledge.from_dict(data)
        except (OSError, ValueError, TypeError):
            return None

    def mark_reused(self, application: str) -> AppKnowledge | None:
        knowledge = self.load(application)
        if knowledge is None:
            return None
        knowledge.reuse_count += 1
        self.save(knowledge)
        return knowledge
