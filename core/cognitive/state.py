"""Selective persistence and restart reconstruction for cognitive state."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

from core.cognitive.models import CognitiveEpisode, CurrentMindState, utcnow
from core.memory.secret_filter import sanitize_for_memory
from core.security.atomic import atomic_json_write


_PERSISTED_FIELDS = (
    "current_goal", "active_task", "subgoals", "relevant_context_refs",
    "recalled_memory_refs", "mission_state", "uncertainties",
    "pending_verification", "interaction_mode", "confidence",
    "last_verified_result", "pending_user_question", "active_mission_id",
    "known", "unknown", "uncertain", "conflicted", "needs_verification",
    "active_epistemic_key",
    "updated_at",
)


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_json_write(path, payload)


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_for_memory(value)
    if isinstance(value, list):
        return [cleaned for item in value if (cleaned := _clean(item))]
    if isinstance(value, tuple):
        return tuple(cleaned for item in value if (cleaned := _clean(item)))
    return value


class MindStateStore:
    """Stores only the minimum state required to continue verified work."""

    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)
        self.path = self.directory / "current_mind_state.json"
        self.episodes_path = self.directory / "verified_episodes.json"

    def save(self, state: CurrentMindState) -> CurrentMindState:
        state.updated_at = utcnow()
        payload = {name: _clean(getattr(state, name)) for name in _PERSISTED_FIELDS}
        _atomic_json(self.path, payload)
        return state

    def load(self) -> CurrentMindState:
        if not self.path.exists():
            return CurrentMindState()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return CurrentMindState()
        allowed = CurrentMindState.__dataclass_fields__
        return CurrentMindState(**{
            key: value for key, value in payload.items() if key in allowed
        })

    def reconstruct(self, *, task_runtime: Any = None,
                    living_context: Any = None) -> CurrentMindState:
        state = self.load()
        missions = list(task_runtime.list_missions()) if task_runtime else []
        candidates = [
            mission for mission in missions
            if not bool(getattr(getattr(mission, "status", None), "is_terminal", False))
        ]
        if candidates:
            mission = max(candidates, key=lambda item: getattr(item, "updated_at", ""))
            status = getattr(mission, "status", "idle")
            state.current_goal = getattr(mission, "goal", "") or state.current_goal
            state.active_task = getattr(mission, "current_step", "") or ""
            state.active_mission_id = getattr(mission, "task_id", "") or ""
            state.mission_state = getattr(status, "value", str(status))
            verification = getattr(mission, "verification", None) or {}
            if verification.get("verified") is True and getattr(mission, "result", None):
                state.last_verified_result = _clean(str(mission.result))

        current = getattr(living_context, "current", None)
        if current is None:
            current = getattr(getattr(living_context, "context", None), "current", None)
        if current is not None:
            state.current_app = getattr(current, "active_application", "") or ""
            state.attention_state = "busy" if getattr(current, "user_busy", False) else "available"
            living_goal = _clean(str(getattr(current, "goal", "") or ""))
            try:
                living_confidence = float(getattr(current, "goal_confidence", 0.0) or 0.0)
            except (TypeError, ValueError):
                living_confidence = 0.0
            if not candidates and not state.current_goal and living_goal and living_confidence >= 0.7:
                state.current_goal = living_goal
                state.mission_state = "context_reconstructed"
                state.confidence = round(max(0.0, min(1.0, living_confidence)), 3)
                state.relevant_context_refs = ["living:goal"]
        return state

    def observe_result(self, state: CurrentMindState, *, result: str,
                       verified: bool, pending: Iterable[str] = (),
                       evidence: Iterable[str] = ()) -> CurrentMindState:
        if not verified:
            state.pending_verification = list(pending)
            self.save(state)
            return state
        clean_result = _clean(result)
        state.last_verified_result = clean_result
        state.pending_verification = []
        self._append_episode(CognitiveEpisode(
            goal=_clean(state.current_goal), result=clean_result,
            evidence=tuple(_clean(list(evidence))),
        ))
        self.save(state)
        return state

    def recent_verified(self, *, limit: int = 10) -> list[CognitiveEpisode]:
        if not self.episodes_path.exists():
            return []
        try:
            payload = json.loads(self.episodes_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return []
        episodes = [CognitiveEpisode(
            goal=item.get("goal", ""), result=item.get("result", ""),
            verified_at=item.get("verified_at", utcnow()),
            evidence=tuple(item.get("evidence", ())),
        ) for item in payload if isinstance(item, dict)]
        return episodes[-max(0, limit):] if limit else []

    def _append_episode(self, episode: CognitiveEpisode) -> None:
        existing = [asdict(item) for item in self.recent_verified(limit=99)]
        existing.append(asdict(episode))
        _atomic_json(self.episodes_path, existing[-100:])


__all__ = ["MindStateStore"]
