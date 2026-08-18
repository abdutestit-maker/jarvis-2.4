"""Relevance-first prompt composition with explicit role budgets."""
from __future__ import annotations

import math
from dataclasses import dataclass

from .models import BrainRole


class ContextBudgetError(ValueError):
    pass


@dataclass(frozen=True)
class ComposedContext:
    text: str
    estimated_tokens: int
    included_sections: tuple[str, ...]
    omitted_sections: tuple[str, ...]


class ContextComposer:
    DEFAULT_BUDGETS = {
        BrainRole.FAST: 2048,
        BrainRole.CHAT: 4096,
        BrainRole.SUMMARIZER: 4096,
        BrainRole.REASONING: 8192,
        BrainRole.CODER: 8192,
        BrainRole.PLANNER: 8192,
        BrainRole.RESEARCH: 12288,
        BrainRole.VISION: 8192,
        BrainRole.CRITIC: 6144,
        BrainRole.FALLBACK: 2048,
    }

    def __init__(self, *, role_budgets: dict[BrainRole, int] | None = None) -> None:
        self.role_budgets = dict(self.DEFAULT_BUDGETS)
        self.role_budgets.update(role_budgets or {})

    @staticmethod
    def estimate_tokens(text: str) -> int:
        return 0 if not text else max(1, math.ceil(len(text) / 4))

    @staticmethod
    def _render(name: str, values: tuple[str, ...]) -> str:
        return f"[{name}]\n" + "\n".join(value.strip() for value in values if value.strip())

    def compose(self, *, role: BrainRole, identity: str, user_request: str,
                mission: str = "", current_mind_state: str = "",
                verified_memory: tuple[str, ...] = (), recent_messages: tuple[str, ...] = (),
                relationship_memory: tuple[str, ...] = (), app_context: tuple[str, ...] = (),
                capability_info: tuple[str, ...] = (), epistemic_state: tuple[str, ...] = (),
                unverified_memory: tuple[str, ...] = (), budget_tokens: int | None = None) -> ComposedContext:
        budget = max(1, int(budget_tokens or self.role_budgets[role]))
        critical = (
            ("identity", (identity,)),
            ("user_request", (user_request,)),
            ("mission", (mission,) if mission else ()),
        )
        optional = (
            ("current_mind_state", (current_mind_state,) if current_mind_state else ()),
            ("verified_memory", verified_memory),
            ("relationship_memory", relationship_memory),
            ("app_context", app_context),
            ("capability_info", capability_info),
            ("epistemic_state", epistemic_state),
            ("recent_messages", recent_messages),
            ("unverified_memory", unverified_memory),
        )
        parts: list[str] = []
        included: list[str] = []
        omitted: list[str] = []
        used = 0
        for name, values in critical:
            if not values:
                continue
            rendered = self._render(name, values)
            cost = self.estimate_tokens(rendered)
            if used + cost > budget:
                raise ContextBudgetError(
                    f"critical context exceeds role budget ({used + cost}>{budget}); refusing silent drop"
                )
            parts.append(rendered)
            included.append(name)
            used += cost
        for name, values in optional:
            if not values:
                continue
            rendered = self._render(name, values)
            cost = self.estimate_tokens(rendered)
            if used + cost <= budget:
                parts.append(rendered)
                included.append(name)
                used += cost
            else:
                omitted.append(name)
        return ComposedContext("\n\n".join(parts), used, tuple(included), tuple(omitted))


__all__ = ["ContextComposer", "ComposedContext", "ContextBudgetError"]

