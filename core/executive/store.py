"""Crash-safe, local-only persistence for Executive Mind records."""

from __future__ import annotations

import copy
import threading
from pathlib import Path
from typing import Any

from core.memory.secret_filter import sanitize_for_memory
from core.security.atomic import atomic_json_write, load_json


_SECRET_KEYS = {"password", "passwd", "secret", "token", "api_key", "apikey", "private_key", "credential"}


def _safe(value: Any, key: str = "") -> Any:
    if key.casefold() in _SECRET_KEYS:
        return None
    if isinstance(value, dict):
        return {str(k): v for k, raw in value.items() if (v := _safe(raw, str(k))) is not None}
    if isinstance(value, list):
        return [item for raw in value if (item := _safe(raw, key)) is not None]
    if isinstance(value, str):
        safe = sanitize_for_memory(value)
        return safe if safe else ("***" if value.strip() else "")
    return copy.deepcopy(value)


class ExecutiveStore:
    """Named JSON collections with atomic writes and a single process lock."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def path(self, name: str) -> Path:
        return self.root / f"{name}.json"

    def read(self, name: str, default: Any) -> Any:
        with self._lock:
            value = load_json(self.path(name), default=default)
            return copy.deepcopy(value)

    def write(self, name: str, value: Any) -> Path:
        with self._lock:
            return atomic_json_write(self.path(name), _safe(value))

    def append(self, name: str, item: dict[str, Any], *, limit: int = 500) -> list[dict[str, Any]]:
        with self._lock:
            values = self.read(name, [])
            if not isinstance(values, list):
                values = []
            values.append(_safe(item))
            values = [v for v in values if isinstance(v, dict)][-max(1, int(limit)):]
            self.write(name, values)
            return values

