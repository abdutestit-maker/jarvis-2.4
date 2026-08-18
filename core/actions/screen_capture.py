from __future__ import annotations
from typing import Any, Dict
from core.actions.base import ActionResult, Tool, ToolContext
from core.actions.registry import DEFAULT_REGISTRY
from core.vision.screen import ScreenCapture

class ScreenCaptureTool(Tool):
    @property
    def name(self) -> str: return "screen_capture"
    @property
    def description(self) -> str: return "Capture the screen for local OCR. Requires explicit user permission; never uploads the image."
    @property
    def input_schema(self) -> Dict[str, Any]: return {"type": "object", "properties": {"permission": {"type": "boolean"}}, "required": ["permission"], "additionalProperties": False}
    def run(self, args: Dict[str, Any], context: ToolContext) -> ActionResult:
        try:
            result = ScreenCapture().capture(permission=bool(args.get("permission")))
            return ActionResult(self.name, args, True, {"text": result.text, "active_window": result.active_window, "url": result.url})
        except Exception as exc:
            return ActionResult(self.name, args, False, error=str(exc))

DEFAULT_REGISTRY.register(ScreenCaptureTool())
