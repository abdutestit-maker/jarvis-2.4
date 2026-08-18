"""Application exploration built on the semantic Windows provider contract."""

from __future__ import annotations

from typing import Any

from .knowledge import AppKnowledge
from .semantic import SemanticControl, SemanticSelector, flatten_controls

__all__ = ["AppExplorer", "SemanticControl", "SemanticSelector"]


class AppExplorer:
    """Maps an unknown application without recording click coordinates."""

    _setting_types = {"checkbox", "combobox", "edit", "radiobutton", "slider", "spinner"}
    _menu_types = {"menu", "menuitem"}

    def __init__(self, windows: Any) -> None:
        self.windows = windows

    def explore(self, application: str, *, process_id: int | None = None) -> AppKnowledge:
        result = self.windows.ui_tree(window_title=application, process_id=process_id)
        if not result.ok or not isinstance(result.value, dict):
            raise RuntimeError(result.error or f"UI tree unavailable for {application}")
        tree = SemanticControl.from_dict(result.value)
        controls = flatten_controls(tree)
        serialised = [item.to_dict() for item in controls]
        return AppKnowledge(
            application=application,
            windows=[item.to_dict() for item in controls
                     if item.control_type.casefold() == "window"] or [tree.to_dict()],
            menus=[item.to_dict() for item in controls
                   if item.control_type.casefold() in self._menu_types],
            settings=[item.to_dict() for item in controls
                      if item.control_type.casefold() in self._setting_types],
            controls=serialised,
            best_execution_method=getattr(result, "provider", "") or "uia",
            discovery_steps=1,
        )
