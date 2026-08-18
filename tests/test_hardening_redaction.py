from __future__ import annotations

import json

from core.security.redaction import contains_secret, redact, redact_text


def test_canonical_redaction_masks_all_common_secret_forms() -> None:
    secret = "sk-abcdefghijklmnop"
    payload = {
        "api_key": secret,
        "headers": {"Authorization": "Bearer verylongtoken123456", "Cookie": "sid=secret-cookie"},
        "password": "p@ssword-value",
        "private_key": "-----BEGIN PRIVATE KEY-----abc-----END PRIVATE KEY-----",
        "url": "postgres://user:db-password@host/db",
    }
    safe = redact(payload)
    encoded = json.dumps(safe, ensure_ascii=False)
    assert secret not in encoded
    assert "verylongtoken123456" not in encoded
    assert "secret-cookie" not in encoded
    assert contains_secret(payload)


def test_redaction_is_recursive_and_idempotent() -> None:
    value = {"nested": ["token=abc123456789", {"value": "Bearer abcdefghijklmnop"}]}
    once = redact(value)
    assert redact(once) == once
    assert "abc123456789" not in redact_text(json.dumps(value))

