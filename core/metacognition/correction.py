"""Bounded PLAN→EXPECT→ACT→OBSERVE→COMPARE correction loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from core.metacognition.expectation import Expectation, ExpectationComparator, Surprise
from core.metacognition.failures import (
    FailureEpisode, FailureEpisodeStore, fingerprint_environment,
)


@dataclass(frozen=True)
class Strategy:
    name: str
    action: Callable[[], Any]


@dataclass
class CorrectionAttempt:
    strategy: str
    reported_success: bool
    observed: dict[str, Any]
    verified: bool
    mismatch: dict[str, Any] = field(default_factory=dict)


@dataclass
class CorrectionReport:
    verified: bool
    state: str
    attempts: list[CorrectionAttempt] = field(default_factory=list)
    surprises: list[Surprise] = field(default_factory=list)
    selected_strategy: str = ""
    skipped_strategies: list[str] = field(default_factory=list)
    failure_episodes: list[FailureEpisode] = field(default_factory=list)
    strategy_confidence: dict[str, float] = field(default_factory=dict)
    needs_confirmation: bool = False


class SelfCorrectionEngine:
    def __init__(self, failures: FailureEpisodeStore, *, max_attempts: int = 3,
                 risk_policy: Any = None, audit: Any = None) -> None:
        self.failures = failures
        self.max_attempts = max(1, min(5, int(max_attempts)))
        self.risk_policy = risk_policy
        self.audit = audit
        self.comparator = ExpectationComparator()

    def run(self, *, goal: str, task_class: str, strategies: list[Strategy],
            expectation: Expectation, observer: Callable[[], dict[str, Any]],
            environment: dict[str, Any], evidence_provider: Callable[[], list[str]] | None = None,
            risk: str = "low") -> CorrectionReport:
        if self.risk_policy is not None:
            decision = self.risk_policy.decide(confidence=0.95, risk=risk)
            if getattr(decision, "action", "") == "confirm":
                return CorrectionReport(False, "waiting_for_user", needs_confirmation=True)

        fingerprint = fingerprint_environment(environment)
        avoided = self.failures.avoid_strategies(task_class, fingerprint)
        report = CorrectionReport(False, "executing")
        report.strategy_confidence = {item.name: 1.0 for item in strategies}
        attempted: set[str] = set()
        new_failure_ids: list[str] = []
        for strategy in strategies:
            if len(report.attempts) >= self.max_attempts:
                break
            if strategy.name in avoided or strategy.name in attempted:
                if strategy.name not in report.skipped_strategies:
                    report.skipped_strategies.append(strategy.name)
                continue
            attempted.add(strategy.name)
            current_expectation = Expectation(
                expectation.action_id, expectation.goal, strategy.name,
                dict(expectation.expected_effect), expectation.verification_method,
                list(expectation.failure_indicators), expectation.created_at,
            )
            self._audit("expectation", current_expectation.to_dict())
            try:
                action_result = strategy.action()
                reported_success = bool(getattr(action_result, "ok", action_result is not False))
            except Exception:
                action_result = None
                reported_success = False
            self._audit("action", {"strategy": strategy.name,
                                   "reported_success": reported_success})
            try:
                observed = dict(observer() or {})
            except Exception:
                observed = {}
            refs = list(evidence_provider() if evidence_provider else ())
            comparison = self.comparator.compare(
                current_expectation, observed, evidence_refs=refs,
            )
            attempt = CorrectionAttempt(
                strategy.name, reported_success, observed, comparison.verified,
                comparison.surprise.mismatch if comparison.surprise else {},
            )
            report.attempts.append(attempt)
            self._audit("observation", {"strategy": strategy.name, "observed": observed,
                                        "evidence_refs": refs})
            if comparison.verified:
                report.verified = True
                report.state = "completed"
                report.selected_strategy = strategy.name
                if new_failure_ids:
                    report.failure_episodes = self.failures.mark_repair(
                        new_failure_ids, strategy.name,
                    )
                self._audit("verification", {"verified": True,
                                             "strategy": strategy.name})
                return report

            surprise = comparison.surprise
            if surprise is not None:
                report.surprises.append(surprise)
                self._audit("surprise", surprise.to_dict())
                episode = self.failures.record(FailureEpisode(
                    goal=goal, task_class=task_class, strategy=strategy.name,
                    failure_category="expectation_mismatch",
                    observed_mismatch=surprise.mismatch,
                    environment_fingerprint=fingerprint, confidence=0.9,
                    evidence_refs=refs,
                ))
                report.failure_episodes.append(episode)
                new_failure_ids.append(episode.episode_id)
            report.strategy_confidence[strategy.name] = round(
                max(0.0, report.strategy_confidence.get(strategy.name, 1.0) - 0.3), 3,
            )
            self._audit("strategy_change", {
                "failed_strategy": strategy.name,
                "remaining_attempts": self.max_attempts - len(report.attempts),
            })

        report.state = "research_required"
        self._audit("verification", {"verified": False, "state": report.state})
        return report

    def _audit(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.audit is not None:
            self.audit.record(event_type, payload)


__all__ = [
    "CorrectionAttempt", "CorrectionReport", "SelfCorrectionEngine", "Strategy",
]
