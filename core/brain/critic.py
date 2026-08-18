"""Evidence-facing critic verdicts without hidden reasoning."""
from __future__ import annotations

from collections.abc import Callable

from .models import CriticResult, CriticVerdict
from .structured import StructuredOutputValidator


class Critic:
    def __init__(self, generator: Callable[[str], str] | None = None) -> None:
        self.generator = generator
        self.validator = StructuredOutputValidator(max_repairs=1)

    def review(self, *, goal: str, plan: tuple[str, ...], evidence: tuple[str, ...],
               risk: str) -> CriticResult:
        if self.generator is not None:
            raw = self.generator(
                f"goal={goal}\nplan={list(plan)}\nevidence={list(evidence)}\nrisk={risk}"
            )
            data = self.validator.validate(raw, dict)
            try:
                verdict = CriticVerdict(str(data.get("verdict", "")))
            except ValueError:
                verdict = CriticVerdict.REVISE
            return CriticResult(
                verdict,
                tuple(str(item) for item in data.get("issues", [])),
                tuple(str(item) for item in data.get("required_evidence", [])),
            )
        if risk.casefold() in {"high", "critical", "dangerous"} and not evidence:
            return CriticResult(
                CriticVerdict.INSUFFICIENT_EVIDENCE,
                ("high-impact plan lacks evidence",), ("verified observation",),
            )
        if not plan:
            return CriticResult(CriticVerdict.REVISE, ("plan has no actionable steps",))
        return CriticResult(CriticVerdict.APPROVE)


__all__ = ["Critic"]

