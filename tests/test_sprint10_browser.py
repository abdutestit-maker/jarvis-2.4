"""Real DOM-first browser provider tests for Sprint 10."""

from __future__ import annotations

from pathlib import Path

from core.platform.browser import BrowserAutomationProvider, DOMSelector


_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Operator Fixture</title></head>
<body>
  <h1>Reference settings</h1>
  <label for="profile">Profile name</label>
  <input id="profile" aria-label="Profile name" />
  <button id="apply" type="button"
    onclick="document.querySelector('#status').textContent='applied:'+document.querySelector('#profile').value">
    Apply settings
  </button>
  <a id="download" download="fixture.txt" href="data:text/plain,verified">Download fixture</a>
  <output id="status">idle</output>
</body></html>"""


def test_browser_provider_uses_semantic_dom_selectors_and_extracts_state(tmp_path: Path) -> None:
    page = tmp_path / "fixture.html"
    page.write_text(_HTML, encoding="utf-8")
    browser = BrowserAutomationProvider(headless=True)
    try:
        opened = browser.open(page.as_uri())
        dom = browser.inspect_dom()
        found = browser.find(DOMSelector(role="button", name="Apply settings"))
        typed = browser.type(DOMSelector(label="Profile name"), "JARVIS")
        clicked = browser.click(DOMSelector(automation_id="apply"))
        observed = browser.extract(DOMSelector(css="#status"))
    finally:
        browser.close()

    assert opened["ok"] is True
    assert any(node["role"] == "button" and node["name"] == "Apply settings" for node in dom)
    assert found and found[0]["automation_id"] == "apply"
    assert typed["action_taken"] is True
    assert clicked["action_taken"] is True
    assert observed["text"] == "applied:JARVIS"
    assert all("coordinates" not in node for node in dom)


def test_browser_download_waits_for_real_dom_download(tmp_path: Path) -> None:
    page = tmp_path / "fixture.html"
    page.write_text(_HTML, encoding="utf-8")
    browser = BrowserAutomationProvider(headless=True)
    try:
        browser.open(page.as_uri())
        result = browser.download(DOMSelector(css="#download"), directory=tmp_path / "downloads")
    finally:
        browser.close()

    downloaded = Path(result["path"])
    assert result["ok"] is True
    assert downloaded.is_file()
    assert downloaded.read_text(encoding="utf-8") == "verified"


def test_browser_provider_blocks_semantic_submit_without_confirmation(tmp_path: Path) -> None:
    page = tmp_path / "submit.html"
    page.write_text(
        "<button id='purchase' type='submit' onclick=\"this.textContent='done'\">Purchase</button>",
        encoding="utf-8",
    )
    browser = BrowserAutomationProvider(headless=True)
    try:
        browser.open(page.as_uri())
        blocked = browser.click(DOMSelector(automation_id="purchase"))
        allowed = browser.click(DOMSelector(automation_id="purchase"), confirm=True)
    finally:
        browser.close()

    assert blocked["requires_confirmation"] is True
    assert blocked["action_taken"] is False
    assert allowed["action_taken"] is True

