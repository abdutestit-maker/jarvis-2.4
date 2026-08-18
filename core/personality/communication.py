"""Context-aware conversion of task state into a bounded style profile."""

from __future__ import annotations

from typing import Any, Mapping

from core.personality.humor import HumorPolicy
from core.personality.models import PersonalityProfile, StyleProfile, UserProfile


def _value(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


class CommunicationAdapter:
    def __init__(self, personality: PersonalityProfile | None = None,
                 humor_policy: HumorPolicy | None = None) -> None:
        self.personality = personality or PersonalityProfile()
        self.humor_policy = humor_policy or HumorPolicy(self.personality.humor)

    def adapt(self, user_context: Any = None, urgency: str = "normal",
              task_type: str = "conversation",
              user_preference: UserProfile | Mapping[str, Any] | None = None,
              *, risk: str = "low", is_error: bool = False) -> StyleProfile:
        context = user_context or {}
        preference = user_preference or UserProfile()
        kind = str(task_type or "conversation").casefold()
        urgent = str(urgency or "normal").casefold() in {"high", "urgent", "critical"}
        busy = bool(_value(context, "busy", False) or _value(context, "user_busy", False)
                    or _value(context, "typing_active", False)
                    or _value(context, "meeting_active", False) or _value(context, "fullscreen", False))
        requested = str(_value(preference, "communication_style", "adaptive") or "adaptive").casefold()

        verbosity = "balanced"
        max_sentences = 5
        depth = "concise"
        structured = kind == "report"
        if kind in {"learning", "tutorial", "explanation"}:
            verbosity, max_sentences, depth = "detailed", 12, "step_by_step"
        elif kind == "report":
            verbosity, max_sentences, depth = "balanced", 10, "evidence_first"
        elif kind == "conversation":
            verbosity, max_sentences, depth = "natural", 5, "natural"

        if requested in {"short", "brief", "concise"}:
            verbosity, max_sentences, depth = "short", 3, "concise"
        elif requested in {"detailed", "verbose"}:
            verbosity, max_sentences = "detailed", 12
            depth = "step_by_step" if kind != "report" else "evidence_first"
        technical_level = str(_value(preference, "technical_level", "adaptive") or "adaptive")
        if kind in {"learning", "tutorial", "explanation"}:
            if technical_level == "advanced":
                depth = "technical"
            elif technical_level == "beginner":
                depth = "simple_step_by_step"
        elif bool(_value(preference, "prefers_action_over_explanation", False)):
            depth = "action_first"
        if busy or urgent:
            verbosity, max_sentences, depth = "short", 2, "action_first"
            structured = False if kind != "report" else structured

        preference_humor = _value(preference, "humor_preference", None)
        humor = self.humor_policy.calibrate(
            task_type=kind, risk=risk, is_error=is_error, preference=preference_humor,
        )
        return StyleProfile(
            tone="calm" if is_error or risk not in {"", "none", "low"} else self.personality.tone,
            verbosity=verbosity,
            max_sentences=max_sentences,
            explanation_depth=depth,
            structured=structured,
            formality="respectful" if self.personality.respect_level == "high" else "neutral",
            humor_level=humor,
            initiative=self.personality.initiative,
            address=str(_value(preference, "preferred_address", self.personality.address)
                        or self.personality.address),
        )
