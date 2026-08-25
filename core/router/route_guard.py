"""Transport boundary for selected tools.

Semantic tool selection belongs to the reasoning brain plus capability
discovery. This guard deliberately does not map user phrases to a tiny set
of tools: that would turn safety into a capability whitelist. It validates
only invariants independent of a particular user goal; the Risk Gate
evaluates the concrete selected action immediately before execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from .intent_router import resolve_keyword_tool

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


def validate_tool_selection(goal: str, tool: str,
                            args: Dict[str, Any] | None = None) -> RouteGuardResult:
    """Validate a selected action without shrinking the capability surface.

    Registered-tool membership and JSON schema are checked by the structured
    planner before this function. This final guard catches malformed direct
    execution calls; it never chooses or suppresses a capability from words
    such as music, time or browser.
    """
    intent = resolve_keyword_tool(goal or "", goal or "")
    name = str(tool or "").strip()
    if not name:
        return RouteGuardResult(False, intent, reason="tool id is empty")
    if args is not None and not isinstance(args, dict):
        return RouteGuardResult(False, intent, reason="tool arguments must be an object")
    return RouteGuardResult(True, intent)
