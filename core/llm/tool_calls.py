"""Provider-neutral native tool-call contracts.

The planner used to depend on a text marker (``TOOL_CALL:{...}``).  This
module keeps the provider response typed at the boundary while allowing the
existing JSON planner to remain a fallback for older local model builds.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Sequence

__all__ = ["ToolCall", "ToolCallResponse", "parse_tool_calls"]


def _arguments(value: Any) -> Mapping[str, Any]:
    if value is None or value == "":
        return MappingProxyType({})
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"tool arguments are not valid JSON: {exc}") from exc
    if not isinstance(value, Mapping):
        raise ValueError("tool arguments must be a JSON object")
    return MappingProxyType(dict(value))


@dataclass(frozen=True)
class ToolCall:
    """One validated provider tool call.

    ``arguments`` is immutable after parsing so a provider response cannot be
    changed between Risk Gate validation and execution.
    """

    call_id: str
    name: str
    arguments: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "call_id", str(self.call_id or ""))
        name = str(self.name or "").strip()
        if not name:
            raise ValueError("native tool call has no function name")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "arguments", _arguments(self.arguments))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.call_id,
            "type": "function",
            "function": {"name": self.name, "arguments": dict(self.arguments)},
        }


@dataclass(frozen=True)
class ToolCallResponse:
    """Text plus zero or more native calls from one model turn."""

    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "content", str(self.content or ""))
        object.__setattr__(self, "tool_calls", tuple(self.tool_calls or ()))

    @property
    def first_tool_call(self) -> ToolCall | None:
        return self.tool_calls[0] if self.tool_calls else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "tool_calls": [call.to_dict() for call in self.tool_calls],
        }


def _message_from_response(response: Mapping[str, Any]) -> Mapping[str, Any]:
    choices = response.get("choices") or []
    if not choices or not isinstance(choices[0], Mapping):
        return {}
    message = choices[0].get("message") or choices[0].get("delta") or {}
    return message if isinstance(message, Mapping) else {}


def parse_tool_calls(response: Mapping[str, Any]) -> ToolCallResponse:
    """Normalize OpenAI-compatible native tool-call responses.

    Both modern ``tool_calls`` and legacy single ``function_call`` payloads
    are accepted.  Malformed arguments fail closed instead of becoming a
    guessed mutation.
    """

    if not isinstance(response, Mapping):
        raise ValueError("native tool response must be an object")
    message = _message_from_response(response)
    anthropic_blocks = response.get("content") if not message else None
    if isinstance(anthropic_blocks, Sequence) and not isinstance(anthropic_blocks, (str, bytes)):
        text_parts: list[str] = []
        raw_calls: list[dict[str, Any]] = []
        for index, block in enumerate(anthropic_blocks):
            if not isinstance(block, Mapping):
                continue
            if block.get("type") == "text":
                text_parts.append(str(block.get("text") or ""))
            elif block.get("type") == "tool_use":
                raw_calls.append({
                    "id": str(block.get("id") or f"toolu-{index}"),
                    "type": "function",
                    "function": {
                        "name": block.get("name"),
                        "arguments": block.get("input") or {},
                    },
                })
        return ToolCallResponse(
            content="".join(text_parts),
            tool_calls=tuple(
                ToolCall(
                    call_id=str(item["id"]),
                    name=str(item["function"].get("name") or ""),
                    arguments=item["function"].get("arguments"),
                )
                for item in raw_calls
            ),
            raw=response,
        )

    content = message.get("content") or ""
    raw_calls = message.get("tool_calls")
    if raw_calls is None and message.get("function_call") is not None:
        raw_calls = [{
            "id": "legacy-call",
            "type": "function",
            "function": message.get("function_call"),
        }]
    if raw_calls is None:
        raw_calls = []
    if not isinstance(raw_calls, Sequence) or isinstance(raw_calls, (str, bytes)):
        raise ValueError("native tool_calls must be an array")

    parsed: list[ToolCall] = []
    for index, item in enumerate(raw_calls):
        if not isinstance(item, Mapping):
            raise ValueError("native tool call must be an object")
        function = item.get("function") or {}
        if not isinstance(function, Mapping):
            raise ValueError("native tool function must be an object")
        parsed.append(ToolCall(
            call_id=str(item.get("id") or f"call-{index}"),
            name=str(function.get("name") or ""),
            arguments=_arguments(function.get("arguments")),
        ))
    return ToolCallResponse(content=str(content), tool_calls=tuple(parsed), raw=response)
