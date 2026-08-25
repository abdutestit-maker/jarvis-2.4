from __future__ import annotations

import time

from core.platform.browser import DOMSelector
from core.platform.browser_bridge import (
    BrowserBridge,
    ConfirmationGrant,
    canonical_selector_fingerprint,
)


class _Page:
    url = "fixture://local"

    @staticmethod
    def title() -> str:
        return "Bridge Fixture"


class _Engine:
    _page = _Page()


class FakeProvider:
    def __init__(self) -> None:
        self.engine = _Engine()
        self.nodes = [
            {"tag": "input", "role": "textbox", "name": "Profile name", "automation_id": "profile", "value": "", "type": "text", "visible": True},
            {"tag": "button", "role": "button", "name": "Apply settings", "automation_id": "apply", "text": "Apply settings", "type": "button", "visible": True},
            {"tag": "button", "role": "button", "name": "Purchase", "automation_id": "purchase", "text": "Purchase", "type": "submit", "requires_confirmation": True, "visible": True},
            {"tag": "output", "role": "status", "name": "Status", "automation_id": "status", "text": "idle", "value": "idle", "visible": True},
        ]
        self.opened = False

    def open(self, url: str):
        self.opened = True
        self.engine._page.url = url
        return {"ok": True, "url": url, "title": "Bridge Fixture"}

    def navigate(self, url: str):
        self.engine._page.url = url
        return {"ok": True, "url": url, "title": "Bridge Fixture"}

    def inspect_dom(self, max_nodes: int = 500):
        return [dict(node) for node in self.nodes[:max_nodes]]

    def find(self, selector):
        wanted = selector.automation_id or selector.test_id or selector.label or selector.name or selector.text
        matches = []
        for node in self.nodes:
            hay = {
                node.get("automation_id"), node.get("test_id"), node.get("name"),
                node.get("text"), node.get("label"),
            }
            if wanted in hay and (not selector.role or selector.role == node.get("role")):
                matches.append(dict(node))
        return matches

    def click(self, selector, confirm: bool = False):
        matches = self.find(selector) if not isinstance(selector, int) else [self.nodes[selector]]
        if not matches:
            return {"ok": False, "action_taken": False, "error": "missing"}
        node = matches[0]
        if node.get("automation_id") == "apply":
            self.nodes[3]["text"] = "applied:JARVIS"
            self.nodes[3]["value"] = "applied:JARVIS"
        if node.get("automation_id") == "purchase":
            self.nodes[3]["text"] = "purchased"
            self.nodes[3]["value"] = "purchased"
        return {"ok": True, "action_taken": True}

    def type(self, selector, text: str):
        matches = self.find(selector) if not isinstance(selector, int) else [self.nodes[selector]]
        if not matches:
            return {"ok": False, "action_taken": False}
        for node in self.nodes:
            if node.get("automation_id") == matches[0].get("automation_id"):
                node["value"] = text
        return {"ok": True, "action_taken": True}

    def press(self, selector, key: str):
        matches = self.find(selector) if not isinstance(selector, int) else [self.nodes[selector]]
        if not matches:
            return {"ok": False, "action_taken": False}
        if key.casefold() == "enter":
            self.engine._page.url = "fixture://local/search?query=JARVIS"
            self.nodes[3]["text"] = "search:JARVIS"
            self.nodes[3]["value"] = "search:JARVIS"
        return {"ok": True, "action_taken": True}

    def read_page(self):
        return {"ok": True, "text": " ".join(str(node.get("text", "")) for node in self.nodes)}

    def wait(self, target, timeout=10):
        return {"ok": True, "found": True}

    def extract(self, target=None):
        return {"ok": True, "text": "fixture"}

    def download(self, selector, directory, confirm=False):
        return {"ok": True, "action_taken": True, "path": str(directory)}

    def close(self):
        self.opened = False
        return {"ok": True, "closed": True}


def test_selector_fingerprint_is_canonical_and_versioned() -> None:
    first = canonical_selector_fingerprint(
        " Role_Name ", {"name": "  Apply   settings", "role": "button"}, "session-1", "ABC"
    )
    second = canonical_selector_fingerprint(
        "role_name", {"role": "button", "name": "Apply settings"}, "session-1", "abc"
    )
    third = canonical_selector_fingerprint(
        "role_name", {"role": "button", "name": "Apply settings"}, "session-2", "abc"
    )
    assert first == second
    assert first.startswith("sf1:")
    assert third != first


def test_find_result_contains_confidence_summary_hash_and_alternatives() -> None:
    provider = FakeProvider()
    bridge = BrowserBridge(provider, session_id_factory=lambda: "session-1")
    bridge.open("fixture://local")
    result = bridge.find(DOMSelector(role="button", name="Apply settings"))

    assert result.found is True
    assert result.selector_type == "role_name"
    assert result.confidence == 0.98
    assert result.element_summary["automation_id"] == "apply"
    assert result.dom_hash == bridge.session.dom_hash
    assert result.fingerprint_for("session-1").startswith("sf1:")


def test_css_selector_string_is_normalized_to_dom_css() -> None:
    class CSSProvider(FakeProvider):
        def find(self, selector):
            assert selector.css == 'input[type="search"], #searchInput'
            return [dict(self.nodes[0])]

    bridge = BrowserBridge(CSSProvider(), session_id_factory=lambda: "session-1")
    bridge.open("fixture://local")
    result = bridge.find('input[type="search"], #searchInput')

    assert result.found is True
    assert result.selector_type == "css"


def test_stale_dom_blocks_mutation_until_reresolve() -> None:
    provider = FakeProvider()
    bridge = BrowserBridge(provider, session_id_factory=lambda: "session-1")
    bridge.open("fixture://local")
    found = bridge.find(DOMSelector(automation_id="apply"))
    provider.nodes[3]["text"] = "changed externally"

    stale = bridge.click(found, confirm=True)
    assert stale.success is False
    assert stale.ok is False
    assert stale.action_taken is False
    assert stale.blocked_reason == "STALE_DOM"

    refreshed = bridge.find(DOMSelector(automation_id="apply"))
    executed = bridge.click(refreshed, confirm=True)
    assert executed.success is True
    assert executed.ok is True
    assert executed.action_taken is True
    assert executed.verification["ok"] is True


def test_confirmation_grant_is_bound_to_action_session_selector_and_expiry() -> None:
    provider = FakeProvider()
    bridge = BrowserBridge(provider, session_id_factory=lambda: "session-1")
    bridge.open("fixture://local")
    found = bridge.find(DOMSelector(automation_id="purchase"))

    blocked = bridge.click(found, confirm=True)
    assert blocked.success is False
    assert blocked.requires_confirmation is True
    assert blocked.blocked_reason == "CONFIRMATION_REQUIRED"

    fingerprint = found.fingerprint_for("session-1")
    grant = ConfirmationGrant("grant-1", "click", "session-1", fingerprint, time.time() + 30)
    allowed = bridge.click(found, confirm=True, confirmation_grant=grant)
    assert allowed.success is True
    assert allowed.action_taken is True

    expired = ConfirmationGrant("grant-2", "click", "session-1", fingerprint, time.time() - 1)
    found_again = bridge.find(DOMSelector(automation_id="purchase"))
    assert bridge.click(found_again, confirmation_grant=expired).blocked_reason == "POLICY_BLOCKED"


def test_type_requires_verified_value_readback_without_returning_text() -> None:
    provider = FakeProvider()
    bridge = BrowserBridge(provider, session_id_factory=lambda: "session-1")
    bridge.open("fixture://local")
    result = bridge.type(DOMSelector(automation_id="profile"), "JARVIS")
    assert result.success is True
    assert result.verification["method"] == "semantic_value_readback"
    assert "JARVIS" not in result.to_dict()["observed_state"].__repr__()


def test_press_enter_requires_observed_page_change() -> None:
    provider = FakeProvider()
    bridge = BrowserBridge(provider, session_id_factory=lambda: "session-1")
    bridge.open("fixture://local")
    bridge.type(DOMSelector(automation_id="profile"), "JARVIS")

    result = bridge.press(DOMSelector(automation_id="profile"), "Enter")

    assert result.success is True
    assert result.verification["method"] == "post_key_observation"
    assert result.observed_state["url"].endswith("search?query=JARVIS")


def test_tool_press_defaults_to_focused_element() -> None:
    from core.actions.browser_bridge import BrowserBridgeTool
    from core.actions.base import ToolContext

    class FocusProvider(FakeProvider):
        def find(self, selector):
            if selector.css == ":focus":
                return [dict(self.nodes[0])]
            return super().find(selector)

    bridge = BrowserBridge(FocusProvider(), session_id_factory=lambda: "session-1")
    bridge.open("fixture://local")
    tool = BrowserBridgeTool(bridge)
    result = tool.run(
        {"action": "press", "key": "Enter"},
        ToolContext(settings=None, extra={"browser_bridge": bridge}),
    )

    assert result.ok is True
    assert result.output["verification"]["method"] == "post_key_observation"


def test_focus_only_click_uses_semantic_postcondition() -> None:
    class FocusProvider(FakeProvider):
        def click(self, selector, confirm: bool = False):
            return {
                "ok": True,
                "action_taken": True,
                "postcondition": {"focused": True},
            }

    bridge = BrowserBridge(FocusProvider(), session_id_factory=lambda: "session-1")
    bridge.open("fixture://local")
    result = bridge.click(DOMSelector(automation_id="profile"))

    assert result.success is True
    assert result.verification["method"] == "semantic_click_postcondition"


def test_secret_metadata_is_redacted_from_observation_and_find_result() -> None:
    provider = FakeProvider()
    provider.nodes.append({
        "tag": "input", "role": "textbox", "name": "Password",
        "automation_id": "password", "type": "password", "value": "SECRET",
        "visible": True,
    })
    bridge = BrowserBridge(provider, session_id_factory=lambda: "session-1")
    bridge.open("fixture://local")
    found = bridge.find(DOMSelector(automation_id="password"))
    observed = bridge.observe()

    assert "value" not in found.element_summary
    assert found.element_summary["value_present"] is True
    password_node = next(node for node in observed["nodes"] if node.get("automation_id") == "password")
    assert "value" not in password_node
    assert password_node["value_present"] is True
    assert "SECRET" not in repr(found.to_dict())
