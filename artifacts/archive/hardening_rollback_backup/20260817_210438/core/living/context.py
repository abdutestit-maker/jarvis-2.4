"""LivingContextEngine: transient situation model plus compact episodes."""

from __future__ import annotations

import json
import re
import statistics
import threading
import uuid
from collections import Counter, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from .inference import FrictionDetector, GoalTracker
from .models import ActivityEpisode, ContextObservation, CurrentContext, ReturnContext
from core.security.redaction import redact, redact_text
from core.security.atomic import atomic_json_write, load_json


_FORBIDDEN_METADATA = {
    "screen", "screenshot", "screen_pixels", "pixels", "image_bytes",
    "keystroke", "keystrokes", "typed_text", "password", "secret", "token",
    "private_value", "clipboard_value",
}
_ALLOWED_METADATA = {
    "project", "goal_hint", "activity", "jarvis_intervention", "workflow",
    "provider", "capability_id", "mission_id", "mission_status",
    "mission_goal", "ui_focus_role", "ui_role_counts", "shadow_pattern", "file_role",
}
_SECRET_VALUE = re.compile(
    r"(?i)\b(password|passwd|secret|token|api[_ -]?key|credential)\s*"
    r"(?:=|:|\bis\b|\bэто\b)\s*([^\s,;]+)"
)


class LivingContextEngine:
    """Maintains useful structured context without a surveillance stream."""

    def __init__(self, directory: Path | str, *, max_observations: int = 240,
                 minimum_episode_gap_seconds: float = 300,
                 sensitive_app_patterns: Iterable[str] = ()) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.summary_path = self.directory / "session_summaries.json"
        self.episode_path = self.directory / "activity_episodes.json"
        self.observations: deque[ContextObservation] = deque(maxlen=max(20, max_observations))
        self.minimum_episode_gap_seconds = max(30.0, float(minimum_episode_gap_seconds))
        defaults = ["password", "credential", "private browsing", "incognito", "bank"]
        self.sensitive_patterns = tuple(item.casefold() for item in [*defaults, *sensitive_app_patterns])
        self.goal_tracker = GoalTracker()
        self.friction_detector = FrictionDetector()
        self._episodes: list[ActivityEpisode] = []
        self._active: ActivityEpisode | None = None
        self._lock = threading.RLock()
        self.current = CurrentContext()

    def update(self, observation: ContextObservation | dict[str, Any]) -> CurrentContext:
        event = observation if isinstance(observation, ContextObservation) else ContextObservation(**observation)
        event = self._sanitize(event)
        with self._lock:
            if self._should_segment(event):
                self.close_episode(outcome="context_switched")
            self.observations.append(event)
            if self._active is None:
                self._active = ActivityEpisode(uuid.uuid4().hex, event.observed_at)
            self._extend_episode(self._active, event)
            self.current = self._build_current()
            return self.current

    def episodes(self, *, include_active: bool = False) -> list[ActivityEpisode]:
        result = list(self._episodes)
        if include_active and self._active is not None:
            result.append(self._active)
        return result

    def close_episode(self, *, outcome: str = "completed") -> dict[str, Any] | None:
        with self._lock:
            if self._active is None:
                return None
            latest = self.observations[-1] if self.observations else None
            self._active.end = latest.observed_at if latest else datetime.now(timezone.utc)
            self._active.outcome = outcome
            episode = self._active
            self._episodes.append(episode)
            self._active = None
            summary = {
                "episode_id": episode.episode_id,
                "start": episode.start.isoformat(),
                "end": episode.end.isoformat() if episode.end else None,
                "goal": episode.goal_hypothesis,
                "goal_confidence": episode.goal_confidence,
                "project": episode.project,
                "important_events": list(episode.high_level_actions[-8:]),
                "problems": list(episode.problems[-5:]),
                "learned_workflows": list(dict.fromkeys(
                    str(item.metadata.get("workflow")) for item in self.observations
                    if item.observed_at >= episode.start and item.metadata.get("workflow")
                ))[-5:],
                "unfinished_work": outcome not in {"completed", "success"},
                "outcome": outcome,
            }
            self._append_json(self.summary_path, "summaries", summary, limit=100)
            self._append_json(self.episode_path, "episodes", episode.to_dict(), limit=100)
            return summary

    def return_context(self, *, now: datetime | None = None,
                       min_confidence: float = 0.8) -> ReturnContext | None:
        summaries = self._load_items(self.summary_path, "summaries")
        if not summaries:
            return None
        item = summaries[-1]
        confidence = float(item.get("goal_confidence", 0))
        end = datetime.fromisoformat(item["end"])
        age = (now or datetime.now(timezone.utc)) - end
        if confidence < min_confidence or age > timedelta(days=7) or not item.get("unfinished_work"):
            return None
        subject = item.get("project") or item.get("goal")
        events = list(item.get("important_events") or [])
        stopped_at = events[-1] if events else (subject or "последнем подтверждённом шаге")
        message = f"Продолжим {subject}? Остановились на {stopped_at}."
        return ReturnContext(message, confidence,
                             (f"unfinished episode {item['episode_id']}", f"age={age}"),
                             str(item["episode_id"]))

    def answer(self, question: str) -> dict[str, Any]:
        low = " ".join((question or "").casefold().split())
        events = list(self.observations)
        if not events and not self._episodes:
            return {"known": False, "answer": "Контекст пока не зафиксирован.", "evidence": []}
        current = self.current
        if any(text in low for text in ("сейчас делал", "остановились", "что заметил", "ты заметил")):
            action = current.recent_actions[-1] if current.recent_actions else ""
            answer = f"Последнее подтверждённое действие: {action}."
            if current.current_project:
                answer += f" Проект: {current.current_project}."
            return {"known": bool(action), "answer": answer,
                    "evidence": list(current.evidence)}
        if "научил" in low or "научился" in low:
            workflows = [item.metadata.get("workflow") for item in events if item.metadata.get("workflow")]
            return {"known": bool(workflows), "answer": ", ".join(workflows) if workflows else "Новых workflow нет.",
                    "evidence": ["structured workflow observations"] if workflows else []}
        if "пока меня не было" in low:
            background = [item.action for item in events
                          if item.source in {"mission_runtime", "shadow_engine", "jarvis_capability"}
                          and item.action]
            return {
                "known": bool(background),
                "answer": ("Последние фоновые действия: " + ", ".join(background[-5:]) + ".")
                          if background else "Фоновых действий не зафиксировано.",
                "evidence": [f"background_events={len(background)}"] if background else [],
            }
        return {"known": True, "answer": f"Активное приложение: {current.active_application}.",
                "evidence": list(current.evidence)}

    def _sanitize(self, event: ContextObservation) -> ContextObservation:
        metadata = {
            str(key): self._redact_value(value) for key, value in dict(event.metadata).items()
            if str(key).casefold() in _ALLOWED_METADATA
            and str(key).casefold() not in _FORBIDDEN_METADATA
        }
        clipboard = {
            key: self._redact_value(value) for key, value in dict(event.clipboard_metadata).items()
            if key in {"type", "format", "size", "item_count"}
        }
        haystack = " ".join((event.application, event.process, event.window_title,
                             event.domain, event.page_title)).casefold()
        sensitive = any(pattern in haystack for pattern in self.sensitive_patterns)
        values = event.to_dict()
        values["observed_at"] = event.observed_at
        values["metadata"] = metadata
        values["clipboard_metadata"] = clipboard
        if sensitive:
            values.update({
                "application": "sensitive_application", "process": "",
                "window_title": "", "domain": "", "page_title": "",
                "action": "sensitive_activity", "target": "", "user_language": "",
                "error_signature": "", "metadata": {},
            })
        else:
            for key in ("window_title", "domain", "page_title", "action", "target",
                        "error_signature", "user_language"):
                values[key] = self._redact_text(str(values.get(key) or ""))
        return ContextObservation(**values)

    @staticmethod
    def _redact_text(value: str) -> str:
        return redact_text(value)

    @classmethod
    def _redact_value(cls, value: Any) -> Any:
        return redact(value)

    def _should_segment(self, event: ContextObservation) -> bool:
        if not self.observations or self._active is None:
            return False
        previous = self.observations[-1]
        gap = (event.observed_at - previous.observed_at).total_seconds()
        gaps = [
            (right.observed_at - left.observed_at).total_seconds()
            for left, right in zip(self.observations, list(self.observations)[1:])
            if right.observed_at > left.observed_at
        ]
        adaptive = self.minimum_episode_gap_seconds
        if gaps:
            adaptive = max(adaptive, min(1800.0, statistics.median(gaps) * 8))
        goal_before = str(previous.metadata.get("goal_hint", "")).casefold()
        goal_after = str(event.metadata.get("goal_hint", "")).casefold()
        meaningful_boundary = bool(goal_before and goal_after and goal_before != goal_after
                                   and previous.application != event.application)
        return gap >= adaptive or (meaningful_boundary and gap >= self.minimum_episode_gap_seconds / 2)

    def _extend_episode(self, episode: ActivityEpisode, event: ContextObservation) -> None:
        if event.application and event.application not in episode.applications:
            episode.applications.append(event.application)
        if event.action and (not episode.high_level_actions or episode.high_level_actions[-1] != event.action):
            episode.high_level_actions.append(event.action)
        if event.outcome == "failure":
            problem = event.error_signature or f"{event.action} failed"
            if problem not in episode.problems:
                episode.problems.append(problem)
        intervention = str(event.metadata.get("jarvis_intervention", ""))
        if intervention and intervention not in episode.jarvis_interventions:
            episode.jarvis_interventions.append(intervention)
        episode.project = episode.project or str(event.metadata.get("project", ""))
        episode.evidence_count += 1
        goal = self.goal_tracker.infer(list(self.observations))
        episode.goal_hypothesis = goal.goal
        episode.goal_confidence = goal.confidence

    def _build_current(self) -> CurrentContext:
        events = list(self.observations)
        latest = events[-1]
        active_events = [event for event in events if self._active and event.observed_at >= self._active.start]
        goal = self.goal_tracker.infer(active_events)
        friction = self.friction_detector.detect(active_events)
        actions = [item.action for item in active_events if item.action][-8:]
        repetition = 0.0
        if actions:
            count = Counter(actions).most_common(1)[0][1]
            repetition = min(1.0, count / len(actions) * (1 - 1 / (count + 1)))
        project = next((str(item.metadata.get("project")) for item in reversed(active_events)
                        if item.metadata.get("project")), "")
        activity = next((str(item.metadata.get("activity")) for item in reversed(active_events)
                         if item.metadata.get("activity")), "") or goal.goal
        busy = any((latest.fullscreen, latest.media_active, latest.meeting_active,
                    latest.typing_active, latest.do_not_disturb, latest.active_mission))
        evidence = [f"observation_count={len(active_events)}"]
        evidence.extend(goal.evidence)
        if friction:
            evidence.extend(friction[0].evidence)
        duration = (latest.observed_at - self._active.start).total_seconds() if self._active else 0.0
        return CurrentContext(
            latest.application, latest.process, latest.window_title, latest.domain,
            latest.page_title, max(0.0, duration), project, activity, goal.goal,
            goal.confidence, actions, round(repetition, 3),
            friction[0].confidence if friction else 0.0, busy, False,
            evidence, latest.observed_at.isoformat(),
        )

    def _append_json(self, path: Path, key: str, value: dict[str, Any], *, limit: int) -> None:
        items = self._load_items(path, key)
        items.append(value)
        atomic_json_write(path, {key: items[-max(1, int(limit)):]})

    @staticmethod
    def _load_items(path: Path, key: str) -> list[dict[str, Any]]:
        try:
            return list(load_json(path, default={}).get(key) or [])
        except (OSError, ValueError, TypeError):
            return []


__all__ = ["LivingContextEngine"]
