"""Canonical recursive redaction service.

Every persistence/log boundary can use this module.  It intentionally returns
copies and never mutates caller-owned structures.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

REDACTED = "[redacted]"

SECRET_FIELD_RE = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|"
    r"auth(?:orization)?|bearer|password|passwd|secret|private[_-]?key|"
    r"cookie|set-cookie|connection[_-]?string|credential|token|key)"
)
SECRET_VALUE_RE = re.compile(
    r"(?ix)"
    r"(?:-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----)"
    r"|(?:bearer\s+)[A-Za-z0-9._~+/=-]{8,}"
    r"|(?:basic\s+)[A-Za-z0-9+/=]{12,}"
    r"|(?:\b(?:sk|pk|ghp|github_pat|xox[baprs]-|AIza)[-_][A-Za-z0-9._-]{8,})"
    r"|(?:\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd|"
    r"secret|token|private[_-]?key|connection[_-]?string)\s*[:=]\s*[^\s,;]+)"
    r"|(?:\b(?:sid|session|connect\.sid|auth)\s*=\s*[^;\s]+)"
)
CONNECTION_PASSWORD_RE = re.compile(r"(?i)(://[^:/\s]+:)([^@/\s]+)(@)")


def redact_text(value: str) -> str:
    if not isinstance(value, str) or not value:
        return value
    text = SECRET_VALUE_RE.sub(REDACTED, value)
    return CONNECTION_PASSWORD_RE.sub(r"\1" + REDACTED + r"\3", text)


def contains_secret(value: Any, *, field_name: str = "") -> bool:
    if field_name and SECRET_FIELD_RE.search(str(field_name)):
        return value not in (None, "", REDACTED, "[REDACTED]")
    if isinstance(value, str):
        return bool(SECRET_VALUE_RE.search(value) or CONNECTION_PASSWORD_RE.search(value))
    if isinstance(value, Mapping):
        return any(contains_secret(v, field_name=str(k)) for k, v in value.items())
    if isinstance(value, (list, tuple, set)):
        return any(contains_secret(item) for item in value)
    return False


def redact(value: Any, *, field_name: str = "") -> Any:
    """Return a recursively redacted copy of ``value``."""
    if field_name and SECRET_FIELD_RE.search(str(field_name)):
        if value in (None, "", REDACTED, "[REDACTED]"):
            return value
        if isinstance(value, (str, int, float, bool)):
            return REDACTED
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {key: redact(item, field_name=str(key)) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    if isinstance(value, set):
        return {redact(item) for item in value}
    return value


def redact_args(value: Any) -> Any:
    return redact(value)

