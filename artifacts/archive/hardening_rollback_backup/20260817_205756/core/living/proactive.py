"""Scored proactive policy with evidence, attention and adaptive no-spam memory."""

from __future__ import annotations

import json
import math
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core.capabilities import RiskLevel
from core.safety import assess_risk
from core.security.atomic import atomic_json_write, load_json

from .models import (
    AutonomyLevel,
    ComputerAssistanceLevel,
    InterruptionLevel,
    ProactiveAction,
)


@dataclass
class ProactiveCandidate:
    id: str
    topic: str
    opportunity: str
    confidence: float
    expected_value: float
    reversible: bool
    risk: str
    evidence: list[str]
    ambiguity: float = 0.0
    urgency: float = 0.0
    can_prepare: bool = False
    external_side_effect: bool = False
    requires_credentials: bool = False
    missing_information: str = ""
    danger: bool = False
    capability_id: str = ""


@dataclass
class AttentionSnapshot:
    fullscreen: bool = False
    gaming: bool = False
    media_active: bool = False
    meeting_active: bool = False
    typing_active: bool = False
    active_conversation: bool = False
    active_mission: bool = False
    do_not_disturb: bool = False
    seconds_since_interruption: float | None = None


@dataclass(frozen=True)
class AttentionDecision:
    level: InterruptionLevel
    can_interrupt: bool
    availability: float
    reasons: tuple[str, ...]


@dataclass
class UserProfile:
    autonomy: AutonomyLevel = AutonomyLevel.ASSISTANT
    assistance: ComputerAssistanceLevel = ComputerAssistanceLevel.NORMAL
    allow_low_risk_autonomy: bool = True
    proactive_enabled: bool = True


@dataclass(frozen=True)
class ProactiveDecision:
    action: ProactiveAction
    user_message: str
    score: float
    evidence: tuple[str, ...]
    reason: str
    attention_level: InterruptionLevel
    background_allowed: bool = False


@dataclass(frozen=True)
class AssistanceResponse:
    message: str
    execute_safe_parts: bool
    ask_user: bool
    show_trace: bool


class AttentionManager:
    """Scores interruption availability without inferring mood or emotion."""

    weights = {
        "fullscreen": 0.28, "gaming": 0.45, "media_active": 0.25,
        "meeting_active": 0.48, "typing_active": 0.16,
        "active_conversation": 0.42, "active_mission": 0.16,
        "do_not_disturb": 0.75,
    }

    def assess(self, snapshot: AttentionSnapshot, *, urgency: float = 0.0) -> AttentionDecision:
        reasons: list[str] = []
        load = 0.0
        for name, weight in self.weights.items():
            if getattr(snapshot, name):
                load += weight
                reasons.append(name)
        if snapshot.seconds_since_interruption is not None:
            recency = math.exp(-max(0.0, snapshot.seconds_since_interruption) / 900)
            load += 0.35 * recency
            if recency > 0.25:
                reasons.append("recent_interruption")
        availability = max(0.0, min(1.0, 1.0 - load))
        urgency = max(0.0, min(1.0, urgency))
        engaged = any((snapshot.fullscreen, snapshot.gaming, snapshot.media_active,
                       snapshot.meeting_active, snapshot.typing_active,
                       snapshot.active_mission))
        if snapshot.do_not_disturb or (engaged and urgency < 0.85) or snapshot.active_conversation:
            return AttentionDecision(InterruptionLevel.NONE, False, round(availability, 3), tuple(reasons))
        pressure = 0.7 * urgency + 0.3 * availability
        if pressure >= 0.88:
            level = InterruptionLevel.URGENT
        elif pressure >= 0.7:
            level = InterruptionLevel.IMPORTANT
        elif pressure >= 0.42:
            level = InterruptionLevel.NORMAL
        else:
            level = InterruptionLevel.PASSIVE
        return AttentionDecision(level, availability >= 0.35 or urgency >= 0.8,
                                 round(availability, 3), tuple(reasons))


class ProactiveMemoryStore:
    """Persists suggestion outcomes, never observed content or private fields."""

    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "proactive_memory.json"
        self._lock = threading.RLock()

    def record(self, topic: str, *, outcome: str, useful: bool | None,
               now: datetime | None = None, suggestion: str = "") -> None:
        entry = {
            "topic": " ".join(topic.casefold().split())[:200],
            "suggestion": suggestion[:300],
            "outcome": outcome,
            "useful": useful,
            "at": (now or datetime.now(timezone.utc)).isoformat(),
        }
        with self._lock:
            items = self._load()
            items.append(entry)
            self._save(items[-500:])

    def allows(self, topic: str, *, now: datetime | None = None) -> bool:
        normalized = " ".join(topic.casefold().split())
        related = [item for item in self._load() if item.get("topic") == normalized]
        if not related:
            return True
        current = now or datetime.now(timezone.utc)
        last = related[-1]
        outcome = last.get("outcome")
        rejects = sum(item.get("outcome") == "rejected" for item in related[-5:])
        ignores = sum(item.get("outcome") == "ignored" for item in related[-5:])
        days = 0.5
        if outcome == "ignored":
            days = 5 + 2 * ignores
        elif outcome == "rejected":
            days = 10 + 4 * rejects
        elif outcome in {"accepted", "useful"}:
            days = 0.25
        try:
            then = datetime.fromisoformat(str(last["at"]))
        except (KeyError, TypeError, ValueError):
            return True
        return current - then >= timedelta(days=days)

    def affinity(self, topic: str) -> float:
        normalized = " ".join(topic.casefold().split())
        score = 0.0
        count = 0
        for item in self._load():
            if item.get("topic") != normalized:
                continue
            count += 1
            score += {"accepted": 0.7, "useful": 1.0, "ignored": -0.3,
                      "rejected": -1.0, "failed": -0.5}.get(str(item.get("outcome")), 0)
            if item.get("useful") is True:
                score += 0.3
            elif item.get("useful") is False:
                score -= 0.3
        return max(-1.0, min(1.0, score / max(1, count)))

    def _load(self) -> list[dict[str, Any]]:
        try:
            return list((load_json(self.path, default={}) or {}).get("records") or [])
        except (OSError, ValueError, TypeError):
            return []

    def _save(self, items: list[dict[str, Any]]) -> None:
        atomic_json_write(self.path, {"records": items})


class UserProfileStore:
    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "assistance_profile.json"

    def load(self) -> UserProfile:
        try:
            data = load_json(self.path, default={}) or {}
            return UserProfile(
                AutonomyLevel(data.get("autonomy", AutonomyLevel.ASSISTANT.value)),
                ComputerAssistanceLevel(data.get("assistance", ComputerAssistanceLevel.NORMAL.value)),
                bool(data.get("allow_low_risk_autonomy", True)),
                bool(data.get("proactive_enabled", True)),
            )
        except (OSError, ValueError, TypeError):
            return UserProfile()

    def update(self, *, autonomy: AutonomyLevel | str | None = None,
               assistance: ComputerAssistanceLevel | str | None = None,
               allow_low_risk_autonomy: bool | None = None,
               proactive_enabled: bool | None = None) -> UserProfile:
        profile = self.load()
        if autonomy is not None:
            profile.autonomy = AutonomyLevel(autonomy)
        if assistance is not None:
            profile.assistance = ComputerAssistanceLevel(assistance)
        if allow_low_risk_autonomy is not None:
            profile.allow_low_risk_autonomy = bool(allow_low_risk_autonomy)
        if proactive_enabled is not None:
            profile.proactive_enabled = bool(proactive_enabled)
        payload = asdict(profile)
        payload["autonomy"] = profile.autonomy.value
        payload["assistance"] = profile.assistance.value
        atomic_json_write(self.path, payload)
        return profile


class ProactiveDecisionEngine:
    """Weighted opportunity policy plus non-negotiable risk/evidence guardrails."""

    def __init__(self, memory: ProactiveMemoryStore,
                 attention: AttentionManager | None = None) -> None:
        self.memory = memory
        self.attention = attention or AttentionManager()

    def decide(self, candidate: ProactiveCandidate, attention: AttentionSnapshot, *,
               profile: UserProfile | None = None,
               now: datetime | None = None) -> ProactiveDecision:
        profile = profile or UserProfile()
        evidence = tuple(str(item) for item in candidate.evidence if str(item).strip())
        attention_result = self.attention.assess(attention, urgency=candidate.urgency)
        if not evidence or not profile.proactive_enabled:
            return self._decision(ProactiveAction.SILENT, "", 0, evidence,
                                  "structured evidence is required", attention_result)
        if not self.memory.allows(candidate.topic, now=now):
            return self._decision(ProactiveAction.SILENT, "", 0, evidence,
                                  "adaptive cooldown", attention_result)

        assessed = assess_risk(candidate.opportunity)
        explicit = {"low": 0, "medium": 1, "high": 2, "critical": 3}.get(candidate.risk, 2)
        detected = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1,
                    RiskLevel.HIGH: 2, RiskLevel.CRITICAL: 3}[assessed.level]
        risk = max(explicit, detected)
        affinity = self.memory.affinity(candidate.topic)
        score = max(0.0, min(1.0,
            0.40 * candidate.confidence + 0.25 * candidate.expected_value
            + 0.20 * min(1.0, len(evidence) / 3) + 0.15 * ((affinity + 1) / 2)
            - 0.25 * candidate.ambiguity
        ))

        if candidate.danger and candidate.urgency >= 0.8 and attention_result.can_interrupt:
            return self._decision(
                ProactiveAction.WARN, f"Сэр, обнаружен значимый риск: {candidate.opportunity}.",
                score, evidence, "verified danger evidence", attention_result,
            )
        if candidate.requires_credentials or candidate.external_side_effect or candidate.ambiguity >= 0.65:
            if not attention_result.can_interrupt and candidate.can_prepare and risk == 0:
                return self._decision(ProactiveAction.PREPARE, "", score, evidence,
                                      "prepare while attention is unavailable", attention_result, True)
            if not attention_result.can_interrupt:
                return self._decision(ProactiveAction.SILENT, "", score, evidence,
                                      "required question deferred by attention/risk", attention_result)
            missing = candidate.missing_information or "недостающую информацию"
            return self._decision(ProactiveAction.ASK, f"Сэр, уточните {missing}?", score,
                                  evidence, "one required input", attention_result)
        if risk >= 2:
            return self._decision(ProactiveAction.SILENT, "", score, evidence,
                                  "proactive high-risk action suppressed", attention_result)
        if not attention_result.can_interrupt:
            if candidate.can_prepare and risk == 0:
                return self._decision(ProactiveAction.PREPARE, "", score, evidence,
                                      "safe background preparation", attention_result, True)
            return self._decision(ProactiveAction.SILENT, "", score, evidence,
                                  "attention budget unavailable", attention_result)
        if score < 0.58:
            return self._decision(ProactiveAction.SILENT, "", score, evidence,
                                  "opportunity score below policy threshold", attention_result)
        can_act = (
            profile.autonomy in {AutonomyLevel.PARTNER, AutonomyLevel.AUTONOMOUS}
            and profile.allow_low_risk_autonomy and risk == 0 and candidate.reversible
            and candidate.ambiguity < 0.2 and candidate.confidence >= 0.85
        )
        if can_act:
            return self._decision(ProactiveAction.ACT, "", score, evidence,
                                  "permitted low-risk reversible autonomy", attention_result, True)
        if profile.autonomy is AutonomyLevel.OBSERVER and score < 0.9:
            return self._decision(ProactiveAction.SILENT, "", score, evidence,
                                  "observer profile", attention_result)
        return self._decision(
            ProactiveAction.SUGGEST,
            f"Сэр, эта последовательность повторяется. Автоматизировать {candidate.topic}?",
            score, evidence, "useful opportunity awaiting consent", attention_result,
        )

    @staticmethod
    def _decision(action: ProactiveAction, message: str, score: float,
                  evidence: tuple[str, ...], reason: str,
                  attention: AttentionDecision, background: bool = False) -> ProactiveDecision:
        return ProactiveDecision(action, message, round(score, 3), evidence, reason,
                                 attention.level, background)


class AssistancePolicy:
    def plan(self, request: str, *, assistance: ComputerAssistanceLevel,
             capability_available: bool, requires_user_input: str = "",
             provider_trace: str = "") -> AssistanceResponse:
        if requires_user_input:
            return AssistanceResponse(
                f"{requires_user_input} требуется здесь. Введите, дальше я продолжу.",
                False, True, assistance in {ComputerAssistanceLevel.ADVANCED,
                                            ComputerAssistanceLevel.DEVELOPER},
            )
        if assistance is ComputerAssistanceLevel.BEGINNER:
            if capability_available:
                return AssistanceResponse(
                    "Я сам выполню безопасные шаги. Если понадобится ввод, скажу.",
                    True, False, False,
                )
            return AssistanceResponse("Сейчас разберусь и подготовлю способ.", True, False, False)
        show = assistance in {ComputerAssistanceLevel.ADVANCED, ComputerAssistanceLevel.DEVELOPER}
        message = "Выполняю через проверенную capability."
        if show and provider_trace:
            message += f" Provider trace: {provider_trace}."
        return AssistanceResponse(message, capability_available, False, show)


__all__ = [
    "AssistancePolicy", "AssistanceResponse", "AttentionDecision", "AttentionManager",
    "AttentionSnapshot", "ProactiveCandidate", "ProactiveDecision",
    "ProactiveDecisionEngine", "ProactiveMemoryStore", "UserProfile", "UserProfileStore",
]
