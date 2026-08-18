"""Bounded, resource-aware backlog for predictive Shadow rehearsal."""
from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from core.security.atomic import atomic_json_write, load_json


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

    def add_ranked(self, item_id: str, *, reason: str, user_pain: float,
                   frequency: float, time_saved: float, reuse_probability: float,
                   risk: float, learning_cost: float) -> ShadowBacklogItem:
        """Rank by expected user value instead of novelty or fixed rules."""
        from core.living.resources import ShadowPriorityFactors

        factors = ShadowPriorityFactors(
            user_pain, frequency, time_saved, reuse_probability, risk, learning_cost,
        )
        detail = (
            f"{reason}; pain={user_pain:.3f}; frequency={frequency:.3f}; "
            f"time_saved={time_saved:.3f}; reuse={reuse_probability:.3f}; "
            f"risk={risk:.3f}; cost={learning_cost:.3f}"
        )
        return self.add(item_id, priority=factors.score(), reason=detail)

    def next(self, *, cpu_percent: float, gpu_percent: float, gaming: bool,
             ram_percent: float = 0.0, foreground_latency_ms: float = 0.0,
             fullscreen: bool = False, active_tts: bool = False,
             active_user_mission: bool = False, on_battery: bool = False,
             battery_percent: float = 100.0) -> Optional[ShadowBacklogItem]:
        from core.living.resources import BackgroundBudgetManager, BackgroundMode, ResourceSnapshot

        decision = BackgroundBudgetManager().assess(ResourceSnapshot(
            cpu_percent=cpu_percent, gpu_percent=gpu_percent, ram_percent=ram_percent,
            foreground_latency_ms=foreground_latency_ms, gaming=gaming,
            fullscreen=fullscreen, active_tts=active_tts,
            active_user_mission=active_user_mission, on_battery=on_battery,
            battery_percent=battery_percent,
        ))
        if decision.mode is BackgroundMode.PAUSE:
            return None
        with self._lock:
            return next((item for item in self._load()
                         if item.status == "pending" and item.attempts < 3), None)

    def mark(self, item_id: str, *, success: bool) -> None:
        with self._lock:
            items = self._load()
            for item in items:
                if item.id != item_id:
                    continue
                item.attempts += 1
                item.status = "completed" if success else ("failed" if item.attempts >= 3 else "pending")
                item.updated_at = datetime.now(timezone.utc).isoformat()
            self._save(items)

    def _load(self) -> list[ShadowBacklogItem]:
        try:
            raw = load_json(self.path, default={})
            return [ShadowBacklogItem(**item) for item in raw.get("items", [])]
        except (OSError, ValueError, TypeError):
            return []

    def _save(self, items: list[ShadowBacklogItem]) -> None:
        atomic_json_write(self.path, {"items": [asdict(item) for item in items]})
