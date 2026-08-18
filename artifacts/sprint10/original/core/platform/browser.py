"""DOM-first browser adapter over the existing Playwright engine."""
from __future__ import annotations

from typing import Any, Optional

from core.actions.browser_automation import BrowserAutomationEngine


class BrowserAutomationProvider:
    """Stable browser capability vocabulary; screenshots are not the default."""

    def __init__(self, engine: Optional[BrowserAutomationEngine] = None) -> None:
        self.engine = engine or BrowserAutomationEngine(headless=True)

    def open(self, url: str) -> dict[str, Any]: return self.engine.open(url)
    def navigate(self, url: str) -> dict[str, Any]: return self.engine.open(url)
    def inspect(self) -> list[dict[str, Any]]: return self.engine.list_elements()
    def click(self, index: int, *, confirm: bool = False) -> dict[str, Any]:
        return self.engine.click(index, confirm=confirm)
    def type(self, index: int, text: str) -> dict[str, Any]:
        return self.engine.type_text(index, text)
    def read_page(self) -> dict[str, Any]: return self.engine.read()
    def find(self, text: str) -> list[dict[str, Any]]:
        needle = text.lower()
        return [item for item in self.inspect()
                if needle in str(item.get("text", "")).lower()]
    def wait(self, seconds: float) -> dict[str, Any]:
        if getattr(self.engine, "_page", None) is not None:
            self.engine._page.wait_for_timeout(max(0, seconds) * 1000)
        return {"ok": True, "waited": seconds}
    def extract(self, index: Optional[int] = None) -> dict[str, Any]:
        return self.engine.read(index=index)
    def download(self, index: int, *, confirm: bool = False) -> dict[str, Any]:
        # The existing engine performs DOM element classification and risk gating.
        return self.engine.click(index, confirm=confirm)
    def close(self) -> dict[str, Any]: return self.engine.close()
