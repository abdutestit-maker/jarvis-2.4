"""Playwright DOM-first browser provider with semantic selectors."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from core.actions.browser_automation import BrowserAutomationEngine, BrowserAutomationError


@dataclass(frozen=True)
class DOMSelector:
    """Serializable selector ordered from stable attributes to visible text."""

    automation_id: str = ""
    role: str = ""
    name: str = ""
    label: str = ""
    text: str = ""
    test_id: str = ""
    css: str = ""

    @classmethod
    def from_value(cls, value: "DOMSelector | dict[str, Any] | str") -> "DOMSelector":
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls(text=value)
        if not isinstance(value, dict):
            raise TypeError("DOM selector must be DOMSelector, dict, or text")
        return cls(**{key: str(value.get(key, "") or "") for key in cls.__dataclass_fields__})


class BrowserAutomationProvider:
    """Stable browser vocabulary; DOM locators precede any visual fallback."""

    _risky_words = {
        "buy", "checkout", "confirm", "login", "order", "pay", "purchase",
        "send", "signin", "submit", "subscribe", "transfer",
    }

    def __init__(self, engine: Optional[BrowserAutomationEngine] = None,
                 *, headless: bool = True) -> None:
        self.engine = engine or BrowserAutomationEngine(headless=headless)

    @property
    def evidence_scope(self) -> str:
        return "internal" if bool(getattr(self.engine, "_headless", True)) else "user_visible"

    @property
    def _page(self) -> Any:
        page = getattr(self.engine, "_page", None)
        if page is None:
            raise BrowserAutomationError("Browser page is not open")
        return page

    def open(self, url: str) -> dict[str, Any]:
        return self.engine.open(url)

    def navigate(self, url: str) -> dict[str, Any]:
        page = getattr(self.engine, "_page", None)
        if page is None:
            return self.open(url)
        from core.network_guard import assert_safe_url
        safe_url = assert_safe_url(str(url))
        page.goto(safe_url, wait_until="load")
        return {
            "ok": True,
            "url": page.url,
            "title": page.title(),
            "evidence_scope": self.evidence_scope,
        }

    def inspect(self) -> list[dict[str, Any]]:
        return self.engine.list_elements()

    def inspect_dom(self, *, max_nodes: int = 500) -> list[dict[str, Any]]:
        if getattr(self.engine, "_page", None) is None:
            return self.inspect()
        return list(self._page.evaluate(
            """(limit) => {
              const roleOf = (el) => el.getAttribute('role') || ({
                A:'link', BUTTON:'button', INPUT:(el.type === 'checkbox' ? 'checkbox' : 'textbox'),
                SELECT:'combobox', TEXTAREA:'textbox', OUTPUT:'status', H1:'heading', H2:'heading',
                H3:'heading'
              }[el.tagName] || el.tagName.toLowerCase());
              const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
              return Array.from(document.body.querySelectorAll('*')).filter(visible).slice(0, limit).map(el => ({
                tag: el.tagName.toLowerCase(),
                role: roleOf(el),
                name: (el.getAttribute('aria-label') || el.innerText || el.value || '').trim().slice(0, 300),
                automation_id: el.id || '',
                test_id: el.getAttribute('data-testid') || '',
                label: el.labels && el.labels.length ? el.labels[0].innerText.trim() : '',
                value: 'value' in el ? el.value : null,
                disabled: !!el.disabled,
                visible: true
              }));
            }""", max(1, int(max_nodes)),
        ))

    def _locator(self, target: DOMSelector | dict[str, Any] | str) -> Any:
        selector = DOMSelector.from_value(target)
        page = self._page
        if selector.test_id:
            locator = page.get_by_test_id(selector.test_id)
        elif selector.automation_id:
            escaped = selector.automation_id.replace("\\", "\\\\").replace('"', '\\"')
            locator = page.locator(f'[id="{escaped}"]')
        elif selector.role:
            locator = page.get_by_role(selector.role, name=selector.name or None, exact=bool(selector.name))
        elif selector.label:
            locator = page.get_by_label(selector.label, exact=True)
        elif selector.css:
            locator = page.locator(selector.css)
        elif selector.text or selector.name:
            locator = page.get_by_text(selector.text or selector.name, exact=True)
        else:
            raise ValueError("empty DOM selector")
        if locator.count() < 1:
            raise LookupError(f"DOM element not found: {selector}")
        return locator

    @staticmethod
    def _metadata(locator: Any, index: int = 0) -> dict[str, Any]:
        return dict(locator.nth(index).evaluate("""el => {
          const role = el.getAttribute('role') || ({A:'link',BUTTON:'button',INPUT:(el.type === 'checkbox' ? 'checkbox' : 'textbox'),SELECT:'combobox',TEXTAREA:'textbox'}[el.tagName] || el.tagName.toLowerCase());
          return {
            tag: el.tagName.toLowerCase(), role,
            name: (el.getAttribute('aria-label') || el.innerText || el.value || '').trim(),
            automation_id: el.id || '', test_id: el.getAttribute('data-testid') || '',
            type: el.getAttribute('type') || '', value: 'value' in el ? el.value : null,
            href: el.getAttribute('href') || '', disabled: !!el.disabled,
            requires_confirmation: false
          };
        }"""))

    def find(self, target: DOMSelector | dict[str, Any] | str) -> list[dict[str, Any]]:
        if getattr(self.engine, "_page", None) is None and isinstance(target, str):
            needle = target.casefold()
            return [item for item in self.inspect()
                    if needle in str(item.get("text", "")).casefold()]
        locator = self._locator(target)
        return [self._metadata(locator, index) for index in range(locator.count())]

    def _requires_confirmation(self, metadata: dict[str, Any]) -> bool:
        if str(metadata.get("type", "")).casefold() in {"submit", "image"}:
            return True
        haystack = " ".join(str(metadata.get(key, "")) for key in (
            "name", "automation_id", "test_id", "href",
        )).casefold()
        return any(word in haystack for word in self._risky_words)

    def click(self, target: int | DOMSelector | dict[str, Any] | str,
              *, confirm: bool = False) -> dict[str, Any]:
        if isinstance(target, int):
            return self.engine.click(target, confirm=confirm)
        locator = self._locator(target)
        metadata = self._metadata(locator)
        requires = self._requires_confirmation(metadata)
        if requires and not confirm:
            return {"ok": True, "requires_confirmation": True,
                    "action_taken": False, "element": metadata}
        before_url = str(self._page.url or "")
        before_checked = locator.first.evaluate("el => 'checked' in el ? !!el.checked : null")
        locator.first.click(no_wait_after=True)
        focused = bool(locator.first.evaluate("el => document.activeElement === el"))
        after_checked = locator.first.evaluate("el => 'checked' in el ? !!el.checked : null")
        return {"ok": True, "requires_confirmation": requires,
                "action_taken": True, "element": metadata,
                "postcondition": {
                    "focused": focused,
                    "checked_changed": before_checked != after_checked,
                    "url_changed": before_url != str(self._page.url or ""),
                }}

    def type(self, target: int | DOMSelector | dict[str, Any] | str, text: str) -> dict[str, Any]:
        if isinstance(target, int):
            return self.engine.type_text(target, text)
        locator = self._locator(target)
        locator.first.fill(text)
        return {"ok": True, "action_taken": True, "value": locator.first.input_value()}

    def press(self, target: int | DOMSelector | dict[str, Any] | str, key: str) -> dict[str, Any]:
        if isinstance(target, int):
            elements = self.engine.list_elements()
            if target < 0 or target >= len(elements):
                raise IndexError(f"element index out of range: {target}")
            automation_id = str(elements[target].get("automation_id") or "")
            if not automation_id:
                raise LookupError("indexed element has no stable automation_id")
            target = DOMSelector(automation_id=automation_id)
        locator = self._locator(target).first
        before_url = str(self._page.url or "")
        locator.press(str(key))
        self.settle()
        return {
            "ok": True,
            "action_taken": True,
            "key": str(key),
            "postcondition": {"url_changed": before_url != str(self._page.url or "")},
        }

    def read_page(self) -> dict[str, Any]:
        return self.engine.read()

    def wait(self, target: float | DOMSelector | dict[str, Any] | str,
             *, timeout: float = 10) -> dict[str, Any]:
        if isinstance(target, (int, float)):
            self._page.wait_for_timeout(max(0, float(target)) * 1000)
            return {"ok": True, "waited": float(target)}
        locator = self._locator(target)
        locator.first.wait_for(state="visible", timeout=max(0, float(timeout)) * 1000)
        return {"ok": True, "found": True, "element": self._metadata(locator)}

    def settle(self, *, timeout: float = 5.0) -> None:
        """Let a click-triggered navigation reach a readable DOM boundary."""
        page = self._page
        page.wait_for_timeout(150)
        try:
            page.wait_for_load_state(
                "domcontentloaded",
                timeout=max(100, int(float(timeout) * 1000)),
            )
        except Exception:
            # Observation below remains authoritative and reports a real
            # navigation failure if the page never becomes readable.
            pass
        page.wait_for_timeout(100)

    def extract(self, target: int | DOMSelector | dict[str, Any] | str | None = None) -> dict[str, Any]:
        if target is None or isinstance(target, int):
            return self.engine.read(index=target)
        locator = self._locator(target).first
        tag = locator.evaluate("el => el.tagName.toLowerCase()")
        text = locator.input_value() if tag in {"input", "textarea", "select"} else locator.inner_text()
        return {"ok": True, "text": text, "element": self._metadata(locator)}

    def download(self, target: int | DOMSelector | dict[str, Any] | str, *,
                 directory: Path | str | None = None, confirm: bool = False) -> dict[str, Any]:
        if isinstance(target, int):
            return self.engine.click(target, confirm=confirm)
        locator = self._locator(target)
        metadata = self._metadata(locator)
        requires = self._requires_confirmation(metadata)
        if requires and not confirm:
            return {"ok": True, "requires_confirmation": True, "action_taken": False}
        with self._page.expect_download() as download_info:
            locator.first.click()
        download = download_info.value
        target_dir = Path(directory or Path.cwd() / "downloads").resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = Path(str(download.suggested_filename or "download")).name
        if not filename or filename in {".", ".."}:
            filename = "download"
        destination = (target_dir / filename).resolve()
        if destination.parent != target_dir:
            raise BrowserAutomationError("download filename escapes destination directory")
        download.save_as(str(destination))
        return {"ok": destination.is_file(), "path": str(destination),
                "suggested_filename": download.suggested_filename,
                "action_taken": True, "requires_confirmation": requires}

    def close(self) -> dict[str, Any]:
        return self.engine.close()
