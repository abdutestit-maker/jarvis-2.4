"""Machine-readable metacognition audit without private reasoning fields."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.metacognition.models import utcnow
from core.metacognition.store import safe_value
from core.security.atomic import atomic_json_write, load_json


_PRIVATE_KEYS = {"reasoning", "thoughts", "chain_of_thought", "scratchpad", "private_reasoning"}


def _public(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _public(item) for key, item in value.items()
            if str(key).casefold() not in _PRIVATE_KEYS
        }
    if isinstance(value, list):
        return [_public(item) for item in value]
    return safe_value(value)


class AuditTrail:
    def __init__(self, directory: Path | str, *, max_events: int = 1000) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "metacognition_events.json"
        self.max_events = max(10, int(max_events))

    def record(self, event_type: str, payload: dict[str, Any]) -> None:
        events = self.events()
        events.append({
            "type": str(event_type)[:80], "timestamp": utcnow(),
            "payload": _public(payload),
        })
        self._write(self.path, {"version": 1, "events": events[-self.max_events:]})

    def events(self) -> list[dict[str, Any]]:
        try:
            payload = load_json(self.path, default={})
            return [item for item in payload.get("events", ()) if isinstance(item, dict)]
        except (OSError, TypeError, ValueError):
            return []

    def export_bundle(self, destination: Path | str, *, beliefs: list[Any],
                      failures: list[Any]) -> Path:
        target = Path(destination)
        payload = {
            "schema": "atlas.metacognition.audit.v1",
            "created_at": utcnow(),
            "beliefs": [_public(item.to_dict() if hasattr(item, "to_dict") else item)
                        for item in beliefs],
            "failure_episodes": [_public(item.to_dict() if hasattr(item, "to_dict") else item)
                                 for item in failures],
            "events": self.events(),
        }
        self._write(target, payload)
        return target

    @staticmethod
    def _write(path: Path, payload: dict[str, Any]) -> None:
        atomic_json_write(path, payload)


__all__ = ["AuditTrail"]
