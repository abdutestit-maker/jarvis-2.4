"""Bounded suspended-goal stack and deterministic continuation resolution."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from core.cognitive.models import (
    ContinuationResolution, CurrentMindState, GoalFrame,
)
from core.memory.secret_filter import sanitize_for_memory
from core.security.atomic import atomic_json_write


def _as_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=timezone.utc)


def _tokens(text: str) -> set[str]:
    return {
        word for word in re.findall(r"[a-zа-яё0-9]+", text.casefold())
        if len(word) > 2 and word not in {"там", "что", "это", "как", "тогда"}
    }


class GoalStack:
    def __init__(self, directory: Path | str, *, max_depth: int = 5,
                 ttl_days: int = 7) -> None:
        self.path = Path(directory) / "goal_stack.json"
        self.max_depth = max(1, int(max_depth))
        self.ttl = timedelta(days=max(1, int(ttl_days)))

    def suspend(self, frame: GoalFrame, *, now: datetime | None = None) -> None:
        current = now or datetime.now(timezone.utc)
        frame.goal = sanitize_for_memory(frame.goal)
        frame.active_task = sanitize_for_memory(frame.active_task)
        frames = [item for item in self._read() if item.goal_id != frame.goal_id]
        frames.append(frame)
        self._write(self._prune(frames, current)[-self.max_depth:])

    def frames(self, *, now: datetime | None = None) -> list[GoalFrame]:
        current = now or datetime.now(timezone.utc)
        frames = self._prune(self._read(), current)[-self.max_depth:]
        self._write(frames)
        return frames

    def remove(self, goal_id: str) -> None:
        self._write([frame for frame in self._read() if frame.goal_id != goal_id])

    def _prune(self, frames: Iterable[GoalFrame], now: datetime) -> list[GoalFrame]:
        fresh = [frame for frame in frames if now - _as_utc(frame.updated_at) <= self.ttl]
        return sorted(fresh, key=lambda frame: _as_utc(frame.updated_at))

    def _read(self) -> list[GoalFrame]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return [GoalFrame.from_dict(item) for item in payload if isinstance(item, dict)]
        except (OSError, ValueError, TypeError):
            return []

    def _write(self, frames: Iterable[GoalFrame]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [frame.__dict__ for frame in frames]
        atomic_json_write(self.path, payload)


class ContinuityResolver:
    _CONTINUE = re.compile(r"(?i)\b(продолжай|продолжим|дальше|вернись|continue|resume)\b")
    _STATUS = re.compile(r"(?i)(что\s+там\s+с|как\s+там|статус|status)")
    _RETRY = re.compile(r"(?i)\b(повтори|ещ[её]\s+раз|retry)\b")

    def __init__(self, stack: GoalStack) -> None:
        self.stack = stack

    def resolve(self, text: str, state: CurrentMindState,
                *, now: datetime | None = None) -> ContinuationResolution:
        action = "status" if self._STATUS.search(text) else (
            "retry" if self._RETRY.search(text) else (
                "continue" if self._CONTINUE.search(text) else "none"
            )
        )
        if action == "none":
            return ContinuationResolution()

        frames = self.stack.frames(now=now)
        query = _tokens(text)
        matches = []
        for frame in frames:
            goal_tokens = _tokens(frame.goal)
            overlap = query & goal_tokens
            # Lightweight Russian morphology: case endings should not turn an
            # explicit reference ("установкой") into an ambiguous continuation.
            stem_overlap = {
                token for token in query
                if any(len(token) >= 5 and len(candidate) >= 5 and
                       token[:5] == candidate[:5] for candidate in goal_tokens)
            }
            overlap |= stem_overlap
            if overlap:
                matches.append((len(overlap), _as_utc(frame.updated_at), frame))
        if matches:
            frame = max(matches, key=lambda item: (item[0], item[1]))[2]
            return ContinuationResolution(
                action, frame.goal, frame.goal_id, confidence=0.92,
                evidence=("explicit goal reference",),
            )
        if len(frames) == 1:
            frame = frames[0]
            return ContinuationResolution(
                action, frame.goal, frame.goal_id, confidence=0.86,
                evidence=("single suspended goal",),
            )
        if len(frames) > 1:
            names = [frame.goal for frame in frames[-2:]]
            return ContinuationResolution(
                action="clarify", question=f"Продолжить «{names[0]}» или «{names[1]}»?",
                confidence=0.45, evidence=("multiple suspended goals",),
            )
        if state.current_goal and state.mission_state not in {
            "completed", "cancelled", "failed", "idle",
        }:
            return ContinuationResolution(
                action, state.current_goal, state.active_mission_id,
                confidence=0.72, evidence=("current mind state",),
            )
        return ContinuationResolution(
            action="clarify", question="Какую задачу продолжить?", confidence=0.2,
            evidence=("no goal referent",),
        )


__all__ = ["ContinuityResolver", "GoalStack"]
