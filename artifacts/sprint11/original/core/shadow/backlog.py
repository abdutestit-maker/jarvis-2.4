"""Bounded, resource-aware backlog for predictive Shadow rehearsal."""
from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


@dataclass
class ShadowBacklogItem:
    id: str
    priority: float
    reason: str
    status: str = "pending"
    attempts: int = 0
    updated_at: str = ""


class ShadowBacklog:
    def __init__(self, directory: Path | str, max_items: int = 100) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "backlog.json"
        self.max_items = max_items
        self._lock = threading.RLock()

    def add(self, item_id: str, *, priority: float, reason: str) -> ShadowBacklogItem:
        with self._lock:
            items = self._load()
            existing = next((item for item in items if item.id == item_id), None)
            if existing is None:
                existing = ShadowBacklogItem(item_id, max(0.0, min(1.0, priority)), reason)
                items.append(existing)
            else:
                existing.priority = max(existing.priority, max(0.0, min(1.0, priority)))
                existing.reason = reason
                if existing.status == "completed": existing.status = "pending"
            existing.updated_at = datetime.now(timezone.utc).isoformat()
            items.sort(key=lambda item: (-item.priority, item.updated_at))
            self._save(items[:self.max_items])
            return existing

    def next(self, *, cpu_percent: float, gpu_percent: float, gaming: bool) -> Optional[ShadowBacklogItem]:
        if gaming or cpu_percent >= 70 or gpu_percent >= 70:
            return None
        return next((item for item in self._load()
                     if item.status == "pending" and item.attempts < 3), None)

    def mark(self, item_id: str, *, success: bool) -> None:
        items = self._load()
        for item in items:
            if item.id != item_id: continue
            item.attempts += 1
            item.status = "completed" if success else ("failed" if item.attempts >= 3 else "pending")
            item.updated_at = datetime.now(timezone.utc).isoformat()
        self._save(items)

    def _load(self) -> list[ShadowBacklogItem]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return [ShadowBacklogItem(**item) for item in raw.get("items", [])]
        except (OSError, ValueError, TypeError):
            return []

    def _save(self, items: list[ShadowBacklogItem]) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"items": [asdict(item) for item in items]},
                                  ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)
