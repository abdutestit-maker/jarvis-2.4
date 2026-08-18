"""Private, local pattern collection for the Sprint 8 Shadow Engine."""
from __future__ import annotations

import json
import re
import threading
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, List, Optional
from core.security.atomic import atomic_json_write, load_json


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: Optional[datetime] = None) -> str:
    return (value or _now()).astimezone(timezone.utc).isoformat()


def _slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return result[:48] or "shadow_tool"


@dataclass(frozen=True)
class Pattern:
    id: str
    type: str
    description: str
    frequency: int
    last_seen: str
    confidence: float
    suggested_tool: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PatternWatcher:
    """Stores minimal local observations and emits only aggregate patterns.

    Screen data is accepted only from an already-authorized capture source. OCR
    text is never collected by this class itself; callers may pass a concise
    summary after obtaining explicit permission.
    """

    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._history_path = self.directory / "history.json"
        self._patterns_path = self.directory / "patterns.json"
        self._lock = threading.RLock()

    @property
    def patterns_path(self) -> Path:
        return self._patterns_path

    def record_command(self, text: str, *, outcome: str = "success",
                       observed_at: Optional[datetime] = None) -> None:
        if not (text or "").strip():
            return
        self._append({"kind": "command", "text": text.strip()[:1000],
                      "outcome": outcome, "at": _iso(observed_at)})

    def record_manual_workaround(self, text: str,
                                 observed_at: Optional[datetime] = None) -> None:
        """Records a user-performed workaround linked by an authorized source."""
        self.record_command(text, outcome="workaround", observed_at=observed_at)

    def record_screen_context(self, *, active_window: str, permission: bool,
                              ocr_summary: str = "",
                              observed_at: Optional[datetime] = None) -> bool:
        """Records a permissioned screen observation without capturing a screen."""
        if not permission:
            return False
        if not (active_window or "").strip():
            return False
        self._append({"kind": "screen", "active_window": active_window.strip()[:300],
                      "ocr_summary": (ocr_summary or "").strip()[:1000],
                      "at": _iso(observed_at)})
        return True

    def analyze(self) -> List[Pattern]:
        events = self._load_history()
        patterns: list[Pattern] = []
        commands = [e for e in events if e.get("kind") == "command"]
        patterns.extend(self._command_patterns(commands, "unfulfilled", "unfulfilled_request"))
        patterns.extend(self._command_patterns(commands, "failure", "failure_log"))
        patterns.extend(self._repeated_command_patterns(commands))
        patterns.extend(self._time_patterns(e for e in events if e.get("kind") == "screen"))
        # Stable identifiers make writes idempotent when the worker runs again.
        patterns.sort(key=lambda p: (-p.confidence, p.id))
        self._write_json(self._patterns_path, {"patterns": [p.to_dict() for p in patterns]})
        return patterns

    def _command_patterns(self, events: list[dict[str, Any]], outcome: str,
                          pattern_type: str) -> list[Pattern]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event in events:
            if event.get("outcome") == outcome or (
                outcome == "unfulfilled" and event.get("outcome") == "workaround"
            ):
                grouped[self._normalise_command(event.get("text", ""))].append(event)
        return [self._make_command_pattern(key, group, pattern_type)
                for key, group in grouped.items() if len(group) >= 2 and key]

    def _repeated_command_patterns(self, events: list[dict[str, Any]]) -> list[Pattern]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event in events:
            if event.get("outcome") == "success":
                grouped[self._normalise_command(event.get("text", ""))].append(event)
        return [self._make_command_pattern(key, group, "command_pattern")
                for key, group in grouped.items() if len(group) >= 3 and key]

    @staticmethod
    def _normalise_command(text: str) -> str:
        cleaned = re.sub(r"\d+", "#", (text or "").lower())
        return re.sub(r"\s+", " ", cleaned).strip()

    def _make_command_pattern(self, command: str, events: list[dict[str, Any]],
                              pattern_type: str) -> Pattern:
        suggested = "pdf_converter" if "pdf" in command and any(
            word in command for word in ("конверт", "convert", "перевод")
        ) else _slug(command)
        frequency = len(events)
        return Pattern(
            id=f"{pattern_type}:{suggested}", type=pattern_type,
            description=f"user requested '{command}' {frequency} times",
            frequency=frequency, last_seen=max(e["at"] for e in events),
            confidence=min(0.99, round(0.55 + frequency * 0.12, 2)),
            suggested_tool=suggested,
        )

    def _time_patterns(self, events: Iterable[dict[str, Any]]) -> list[Pattern]:
        groups: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
        for event in events:
            try:
                hour = datetime.fromisoformat(event["at"]).hour
            except (KeyError, TypeError, ValueError):
                continue
            window = str(event.get("active_window", "")).strip()
            if window:
                groups[(window, hour)].append(event)
        patterns: list[Pattern] = []
        for (window, hour), group in groups.items():
            if len(group) < 3:
                continue
            slug = _slug(window)
            patterns.append(Pattern(
                id=f"time_pattern:{slug}:{hour:02d}", type="time_pattern",
                description=f"opens {window} around {hour:02d}:00", frequency=len(group),
                last_seen=max(e["at"] for e in group),
                confidence=min(0.99, round(0.62 + len(group) * 0.09, 2)),
                suggested_tool=f"{slug}_routine",
            ))
        return patterns

    def _append(self, event: dict[str, Any]) -> None:
        with self._lock:
            events = self._load_history()
            events.append(event)
            # Bound local telemetry. Aggregates remain enough for learning.
            self._write_json(self._history_path, {"events": events[-2000:]})

    def _load_history(self) -> list[dict[str, Any]]:
        with self._lock:
            try:
                raw = load_json(self._history_path, default={})
                return list(raw.get("events") or [])
            except (OSError, ValueError, TypeError):
                return []

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        atomic_json_write(path, payload)
