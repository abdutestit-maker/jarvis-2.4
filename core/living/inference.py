"""Evidence aggregation for goals and friction; no emotion inference."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Iterable

from .models import ContextObservation, FrictionSignal, GoalHypothesis


class GoalTracker:
    """Combines language, metadata, action sequence and mission evidence."""

    def infer(self, observations: Iterable[ContextObservation], *,
              recent_missions: Iterable[str] = (),
              memory_hints: Iterable[str] = ()) -> GoalHypothesis:
        events = list(observations)
        scores: dict[str, float] = defaultdict(float)
        evidence: dict[str, list[str]] = defaultdict(list)
        goal_actions: dict[str, set[str]] = defaultdict(set)

        def add(goal: str, weight: float, source: str) -> None:
            normalized = " ".join(str(goal).strip().split())
            if not normalized:
                return
            scores[normalized] += weight
            if source not in evidence[normalized]:
                evidence[normalized].append(source)

        for index, event in enumerate(events):
            recency = 0.75 + 0.25 * ((index + 1) / max(1, len(events)))
            add(event.user_language, 0.36 * recency, "user language")
            hint = str(event.metadata.get("goal_hint", ""))
            add(hint, 0.22 * recency, "application context")
            if hint and event.action:
                goal_actions[" ".join(hint.strip().split())].add(event.action)
            add(str(event.metadata.get("mission_goal", "")), 0.26 * recency, "recent mission")
        for candidate, actions in goal_actions.items():
            if len(actions) >= 2:
                add(candidate, 0.32, "action sequence")
        for mission in recent_missions:
            add(str(mission), 0.28, "mission history")
        for hint in memory_hints:
            add(str(hint), 0.12, "memory")

        if not scores:
            return GoalHypothesis("", 0.0)
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        goal, raw = ranked[0]
        diversity = len(evidence[goal])
        confidence = min(0.98, raw * (0.72 + 0.14 * min(2, diversity)))
        # One weak source is context, not a claimed goal.
        if diversity < 2 or confidence < 0.5:
            return GoalHypothesis("", round(confidence, 3), tuple(evidence[goal]),
                                  tuple(item[0] for item in ranked[1:3]))
        return GoalHypothesis(goal, round(confidence, 3), tuple(evidence[goal]),
                              tuple(item[0] for item in ranked[1:3]))


class FrictionDetector:
    """Detects observable loops/failures without assigning user emotions."""

    def detect(self, observations: Iterable[ContextObservation]) -> list[FrictionSignal]:
        events = list(observations)
        signals: list[FrictionSignal] = []
        failed: dict[tuple[str, str], list[ContextObservation]] = defaultdict(list)
        for event in events:
            if event.outcome in {"failure", "workaround"}:
                failed[(event.action, event.error_signature)].append(event)
        for (action, signature), group in failed.items():
            failures = sum(item.outcome == "failure" for item in group)
            workaround = any(item.outcome == "workaround" for item in group)
            if failures >= 2:
                confidence = min(0.98, 0.55 + 0.15 * (failures - 1) + (0.2 if workaround else 0))
                evidence = [f"{failures} failed {action} observations"]
                if signature:
                    evidence.append(f"same error signature: {signature}")
                if workaround:
                    evidence.append("manual workaround followed failure")
                signals.append(FrictionSignal(
                    "repeated_failure", round(confidence, 3),
                    f"{action} repeatedly failed", f"prepare a verified workflow for {action}",
                    tuple(evidence),
                ))

        actions = [item.action for item in events if item.action]
        counts = Counter(actions)
        if actions:
            action, count = counts.most_common(1)[0]
            density = count / len(actions)
            if count > 1 and density >= 0.6 and not any(s.type == "repeated_failure" for s in signals):
                confidence = min(0.9, density * (1 - math.exp(-count / 2)))
                signals.append(FrictionSignal(
                    "repeated_operation", round(confidence, 3),
                    f"{action} repeated in the current activity", f"generalize {action} as a workflow",
                    (f"{count} matching semantic actions",),
                ))

        switches = sum(
            1 for left, right in zip(events, events[1:])
            if left.application and right.application and left.application != right.application
            and (right.observed_at - left.observed_at).total_seconds() <= 15
        )
        if switches >= 3:
            signals.append(FrictionSignal(
                "rapid_application_switching", min(0.9, 0.5 + switches * 0.08),
                "rapid semantic context switching", "prepare cross-application workflow",
                (f"{switches} switches within 15-second intervals",),
            ))
        return sorted(signals, key=lambda item: -item.confidence)


__all__ = ["FrictionDetector", "GoalTracker"]
