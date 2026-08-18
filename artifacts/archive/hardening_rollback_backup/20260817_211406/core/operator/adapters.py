"""High-reliability configuration adapters for real application missions."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from core.actions.base import ActionResult
from core.operator.software import Checkpoint, CheckpointManager
from core.security.atomic import atomic_write_bytes


@dataclass(frozen=True)
class XmlSetting:
    xpath: str
    kind: str = "text"
    attribute: str = ""
    value_type: str = "str"
    true_value: str = "yes"
    false_value: str = "no"


class XmlConfigAdapter:
    """Observe and change explicit XML fields without GUI coordinates.

    This adapter occupies the config-file rung ahead of UI Automation.  The
    application can still be inspected through UIA before the adapter is used.
    """

    foreground_required = False
    execution_method = "config"

    def __init__(
        self,
        *,
        config_path: Path | str,
        settings: Mapping[str, XmlSetting],
        checkpoints: CheckpointManager,
        close_application: Callable[[], Any] | None = None,
        launch_application: Callable[[], Any] | None = None,
        window_title: str = "",
    ) -> None:
        self.config_path = Path(config_path).expanduser().resolve()
        self.settings = dict(settings)
        self.checkpoints = checkpoints
        self.close_application = close_application
        self.launch_application = launch_application
        self.window_title = window_title
        self.semantic_selectors = {
            key: {"provider": "config", "path": str(self.config_path),
                  "xpath": spec.xpath, "attribute": spec.attribute}
            for key, spec in self.settings.items()
        }
        self._changed_since_launch = False

    def observe(self) -> dict[str, Any]:
        if self._changed_since_launch and self.launch_application is not None:
            self.launch_application()
            self._changed_since_launch = False
        if not self.config_path.is_file() and self.close_application is not None:
            # Some Windows applications create their per-user config only on
            # the first clean exit. UIA discovery already happened by here.
            self.close_application()
        if not self.config_path.is_file():
            raise FileNotFoundError(self.config_path)
        root = ET.parse(self.config_path).getroot()
        result: dict[str, Any] = {}
        for path, spec in self.settings.items():
            node = root.find(spec.xpath)
            if node is None:
                result[path] = None
                continue
            raw = node.get(spec.attribute) if spec.kind == "attribute" else node.text
            result[path] = self._decode(raw, spec)
        return result

    def checkpoint(self, _paths: list[str]) -> Checkpoint:
        if self.close_application is not None:
            self.close_application()
        return self.checkpoints.backup_file(self.config_path)

    def apply_setting(self, path: str, value: Any) -> ActionResult:
        spec = self.settings.get(path)
        if spec is None:
            return ActionResult(
                "config.xml.set", {"path": path}, False,
                error=f"unknown setting: {path}",
            )
        try:
            tree = ET.parse(self.config_path)
            node = tree.getroot().find(spec.xpath)
            if node is None:
                return ActionResult(
                    "config.xml.set", {"path": path}, False,
                    error=f"XML node not found: {spec.xpath}",
                )
            encoded = self._encode(value, spec)
            if spec.kind == "attribute":
                if not spec.attribute:
                    raise ValueError("attribute name is required")
                node.set(spec.attribute, encoded)
            elif spec.kind == "text":
                node.text = encoded
            else:
                raise ValueError(f"unsupported XML setting kind: {spec.kind}")
            payload = ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True)
            atomic_write_bytes(self.config_path, payload)
            self._changed_since_launch = True
            return ActionResult(
                "config.xml.set", {"path": path}, True,
                output={"path": path, "desired": value, "provider": "config"},
            )
        except (OSError, ET.ParseError, TypeError, ValueError) as exc:
            return ActionResult("config.xml.set", {"path": path}, False, error=str(exc))

    def rollback(self, checkpoint: Checkpoint) -> dict[str, Any]:
        result = self.checkpoints.rollback(checkpoint)
        self._changed_since_launch = bool(result.get("restored"))
        return result

    @staticmethod
    def _decode(raw: str | None, spec: XmlSetting) -> Any:
        text = "" if raw is None else raw.strip()
        if spec.value_type == "bool":
            return text.casefold() == spec.true_value.casefold()
        if spec.value_type == "int":
            return int(text)
        if spec.value_type == "float":
            return float(text)
        return text

    @staticmethod
    def _encode(value: Any, spec: XmlSetting) -> str:
        if spec.value_type == "bool":
            return spec.true_value if bool(value) else spec.false_value
        if spec.value_type == "int":
            return str(int(value))
        if spec.value_type == "float":
            return str(float(value))
        return str(value)


__all__ = ["XmlConfigAdapter", "XmlSetting"]
