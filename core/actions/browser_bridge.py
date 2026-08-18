"""ToolRegistry adapter for the policy-aware BrowserBridge."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

from core.actions.base import ActionResult, Tool, ToolContext
from core.actions.registry import DEFAULT_REGISTRY
from core.platform.browser_bridge import (
    BrowserActionResult,
    BrowserBridge,
    BrowserBridgeError,
    ConfirmationGrant,
)

__all__ = ["BrowserBridgeTool"]


class BrowserBridgeTool(Tool):
    """Operator-facing browser tool with verified mutation semantics."""

    def __init__(self, bridge: BrowserBridge | None = None) -> None:
        self._bridge = bridge

    def _get_bridge(self) -> BrowserBridge:
        if self._bridge is None:
            self._bridge = BrowserBridge()
        return self._bridge

    @property
    def name(self) -> str:
        return "browser_bridge"

    @property
    def description(self) -> str:
        return (
            "DOM-first BrowserBridge: semantic find, stale-DOM protection, policy-gated "
            "click/type/download and execute-observe-verify results. confirm=true alone "
            "never authorizes a risky action."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "open", "navigate", "inspect_dom", "find", "click", "type",
                        "read", "wait", "extract", "download", "observe", "close",
                    ],
                },
                "url": {"type": "string"},
                "selector": {"type": ["string", "object", "integer"]},
                "index": {"type": "integer"},
                "text": {"type": "string"},
                "timeout": {"type": "number", "minimum": 0},
                "directory": {"type": "string"},
                "confirm": {"type": "boolean"},
                "expected_state": {"type": "object"},
                "max_nodes": {"type": "integer", "minimum": 1},
            },
            "required": ["action"],
            "additionalProperties": False,
        }

    @staticmethod
    def _target(args: Mapping[str, Any]) -> Any:
        if "selector" in args:
            return args["selector"]
        if "index" in args:
            return int(args["index"])
        raise ValueError("browser mutation requires selector or index")

    @staticmethod
    def _grant(context: ToolContext) -> ConfirmationGrant | None:
        value = context.extra.get("confirmation_grant") if isinstance(context.extra, dict) else None
        if value is None:
            return None
        if isinstance(value, ConfirmationGrant):
            return value
        if isinstance(value, Mapping):
            return ConfirmationGrant.from_mapping(value)
        return None

    @staticmethod
    def _result(args: Dict[str, Any], result: BrowserActionResult) -> ActionResult:
        return ActionResult(
            tool="browser_bridge",
            args=args,
            ok=result.success,
            output=result.to_dict(),
            error=result.error,
        )

    def run(self, args: Dict[str, Any], context: ToolContext) -> ActionResult:
        bridge = context.extra.get("browser_bridge") if isinstance(context.extra, dict) else None
        if not isinstance(bridge, BrowserBridge):
            bridge = self._get_bridge()
        action = str(args.get("action", "")).casefold()
        try:
            if action == "open":
                if not args.get("url"):
                    return ActionResult(self.name, args, False, error="open requires url")
                output = bridge.open(str(args["url"]))
                return ActionResult(self.name, args, True, output=output)
            if action == "navigate":
                output = bridge.navigate(str(args["url"]))
                return ActionResult(self.name, args, True, output=output)
            if action == "inspect_dom":
                output = {"ok": True, "nodes": bridge.inspect_dom(max_nodes=args.get("max_nodes"))}
                return ActionResult(self.name, args, True, output=output)
            if action == "observe":
                return ActionResult(self.name, args, True, output=bridge.observe())
            if action == "find":
                result = bridge.find(self._target(args))
                session_id = bridge.session.session_id if bridge.session else ""
                return ActionResult(self.name, args, result.found, output=result.to_dict(session_id=session_id))
            if action == "click":
                result = bridge.click(
                    self._target(args),
                    confirm=bool(args.get("confirm", False)),
                    confirmation_grant=self._grant(context),
                    expected_state=args.get("expected_state"),
                )
                return self._result(args, result)
            if action == "type":
                if "text" not in args:
                    return ActionResult(self.name, args, False, error="type requires text")
                result = bridge.type(
                    self._target(args),
                    str(args["text"]),
                    confirmation_grant=self._grant(context),
                    expected_state=args.get("expected_state"),
                )
                return self._result(args, result)
            if action == "read":
                return ActionResult(self.name, args, True, output=bridge.read())
            if action == "wait":
                target = args.get("selector", args.get("index", args.get("timeout", 0)))
                return ActionResult(self.name, args, True, output=bridge.wait(target, timeout=float(args.get("timeout", 10))))
            if action == "extract":
                return ActionResult(self.name, args, True, output=bridge.extract(args.get("selector")))
            if action == "download":
                if "directory" not in args:
                    return ActionResult(self.name, args, False, error="download requires directory")
                result = bridge.download(
                    self._target(args),
                    directory=Path(str(args["directory"])),
                    confirm=bool(args.get("confirm", False)),
                    confirmation_grant=self._grant(context),
                )
                return self._result(args, result)
            if action == "close":
                return ActionResult(self.name, args, True, output=bridge.close())
            return ActionResult(self.name, args, False, error=f"unknown browser action: {action}")
        except (BrowserBridgeError, ValueError, TypeError) as exc:
            return ActionResult(self.name, args, False, error=str(exc))
        except Exception as exc:  # boundary converts provider failures to a result
            return ActionResult(self.name, args, False, error=f"{type(exc).__name__}: {exc}")


DEFAULT_REGISTRY.register(BrowserBridgeTool())
