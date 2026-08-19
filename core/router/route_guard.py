"""Deterministic tool-selection guard for the active execution path.

The model may propose a syntactically valid tool that is semantically wrong
for the user's sentence.  This module is the final, model-independent check
before any side effect.  It intentionally blocks only high-confidence
contradictions and leaves genuinely ambiguous goals on the deliberate path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from .intent_router import INTENT_MEDIA, INTENT_NONE, resolve_keyword_tool

__all__ = ["RouteGuardResult", "validate_tool_selection"]


@dataclass(frozen=True)
class RouteGuardResult:
    allowed: bool
    intent: str
    expected_tools: Tuple[str, ...] = ()
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "intent": self.intent,
            "expected_tools": list(self.expected_tools),
            "reason": self.reason,
        }


_TIME_MARKERS = (
    "который час", "сколько времени", "текущее время", "какая дата",
    "время сейчас", "what time", "current time", "clock",
)
_MEDIA_MARKERS = (
    "музык", "трек", "песн", "плеер", "play music", "play track",
    "включи музыку", "поставь музыку", "включи трек", "поставь трек",
)
_REMINDER_MARKERS = (
    "напомни", "напоминан", "будильник", "reminder", "alarm",
)


def _contains_any(text: str, markers: Tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def validate_tool_selection(goal: str, tool: str, args: Dict[str, Any] | None = None) -> RouteGuardResult:
    """Validate a proposed tool without calling a model or touching the OS."""
    text = " ".join((goal or "").casefold().split())
    name = str(tool or "").casefold().strip()
    intent = resolve_keyword_tool(text, text)

    if _contains_any(text, _TIME_MARKERS) and name != "current_time":
        return RouteGuardResult(
            False, intent, ("current_time",),
            f"временной запрос требует current_time, выбран {tool}",
        )

    if _contains_any(text, _MEDIA_MARKERS):
        if name in {"add_reminder", "list_reminders", "cancel_reminder", "current_time"}:
            return RouteGuardResult(
                False, INTENT_MEDIA, ("play_music",),
                f"медиа-запрос требует play_music, выбран {tool}",
            )
        if name == "play_music":
            return RouteGuardResult(True, INTENT_MEDIA, ("play_music",))

    if _contains_any(text, _REMINDER_MARKERS) and name == "play_music":
        return RouteGuardResult(
            False, intent, ("add_reminder",),
            "запрос напоминания не должен вызывать play_music",
        )

    if name == "play_music" and intent not in {INTENT_MEDIA, INTENT_NONE}:
        return RouteGuardResult(
            False, intent, ("play_music",),
            f"play_music не соответствует намерению {intent}",
        )
    if name == "current_time" and not _contains_any(text, _TIME_MARKERS):
        return RouteGuardResult(
            False, intent, ("current_time",),
            "current_time разрешён только для явного запроса времени",
        )

    return RouteGuardResult(True, intent)
