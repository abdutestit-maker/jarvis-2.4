"""Deterministic local Playwright proof for BrowserBridge v2.1."""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from core.platform.browser import DOMSelector
from core.platform.browser_bridge import BrowserBridge, ConfirmationGrant


HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Browser Bridge Fixture</title></head>
<body>
  <label for="profile">Profile name</label>
  <input id="profile" aria-label="Profile name">
  <button id="apply" type="button" onclick="document.getElementById('status').textContent='applied:'+document.getElementById('profile').value">Apply settings</button>
  <button id="purchase" type="submit" onclick="document.getElementById('status').textContent='purchased'">Purchase</button>
  <output id="status">idle</output>
</body></html>"""


def main() -> int:
    artifact = Path("artifacts/browser_bridge/live")
    artifact.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {"success": False}
    with tempfile.TemporaryDirectory(prefix="browser-bridge-") as temp:
        page = Path(temp) / "fixture.html"
        page.write_text(HTML, encoding="utf-8")
        bridge = BrowserBridge(session_id_factory=lambda: "live-session")
        try:
            opened = bridge.open(page.as_uri())
            input_result = bridge.type(DOMSelector(label="Profile name"), "SAMPLE")
            apply_target = bridge.find(DOMSelector(automation_id="apply"))
            applied = bridge.click(apply_target)
            observed_text = bridge.extract(DOMSelector(css="#status"))

            purchase_target = bridge.find(DOMSelector(automation_id="purchase"))
            blocked = bridge.click(purchase_target, confirm=True)
            grant = ConfirmationGrant(
                grant_id="live-grant",
                action="click",
                session_id="live-session",
                selector_fingerprint=purchase_target.fingerprint_for("live-session"),
                expires_at=time.time() + 30,
            )
            authorized = bridge.click(purchase_target, confirmation_grant=grant)
            report = {
                "success": bool(
                    opened["ok"]
                    and input_result.success
                    and applied.success
                    and observed_text.get("text") == "applied:SAMPLE"
                    and blocked.blocked_reason == "CONFIRMATION_REQUIRED"
                    and not blocked.action_taken
                    and authorized.success
                ),
                "session_id": bridge.session.session_id if bridge.session else None,
                "dom_hash": bridge.session.dom_hash if bridge.session else None,
                "input": input_result.to_dict(),
                "apply": applied.to_dict(),
                "observed_status": observed_text,
                "risky_blocked": blocked.to_dict(),
                "risky_authorized": authorized.to_dict(),
                "coordinates_present": any(
                    "coordinates" in node for node in bridge.inspect_dom()
                ),
            }
        finally:
            bridge.close()
    (artifact / "live_demo_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"REPORT={artifact / 'live_demo_report.json'}")
    return 0 if report.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
