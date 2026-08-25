"""Policy-aware semantic browser bridge.

The legacy :mod:`core.actions.browser_automation` module remains available for
backwards compatibility.  ``BrowserBridge`` is the stricter Operator-facing
surface: every mutation is bound to a DOM snapshot, authorized by
``BrowserPolicy`` and followed by observation and verification.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import unicodedata
import uuid
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Mapping

__all__ = [
    "BrowserActionResult",
    "BrowserBridge",
    "BrowserBridgeError",
    "BrowserPolicy",
    "BrowserSession",
    "ConfirmationGrant",
    "FindResult",
    "PolicyDecision",
    "canonical_selector_fingerprint",
    "canonical_selector_value",
]


class BrowserBridgeError(RuntimeError):
    """Expected bridge error that remains safe to expose to the Operator."""


def _normalise_text(value: Any) -> str:
    text = unicodedata.normalize("NFC", str(value or "")).strip()
    return re.sub(r"\s+", " ", text)


def _normalise_key(value: Any) -> str:
    return _normalise_text(value).casefold()


_SECRET_KEYS = frozenset({"password", "passwd", "secret", "token", "credential"})
_SECRET_TYPES = frozenset({"password", "secret", "token", "credential"})


def _is_secret_mapping(value: Mapping[str, Any]) -> bool:
    kind = _normalise_key(value.get("type", ""))
    if kind in _SECRET_TYPES:
        return True
    return any(
        key in _SECRET_KEYS and bool(item)
        for key, item in ((str(k).casefold(), v) for k, v in value.items())
    )


def _redact_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    """Remove secret values while retaining enough metadata for verification."""
    secret = _is_secret_mapping(value)
    result: dict[str, Any] = {}
    for key, item in value.items():
        normalized_key = str(key).casefold()
        if normalized_key in _SECRET_KEYS:
            result[str(key)] = "<redacted>" if item else ""
            continue
        if secret and normalized_key in {"value", "text"}:
            result[f"{normalized_key}_present"] = bool(item)
            continue
        if isinstance(item, Mapping):
            result[str(key)] = _redact_mapping(item)
        elif isinstance(item, list) and all(isinstance(child, Mapping) for child in item):
            result[str(key)] = [_redact_mapping(child) for child in item]
        else:
            result[str(key)] = item
    element = value.get("element")
    if isinstance(element, Mapping) and _is_secret_mapping(element):
        for key in ("text", "value"):
            if key in result:
                result[f"{key}_present"] = bool(result.pop(key))
    return result


def _redact_node(node: Mapping[str, Any]) -> dict[str, Any]:
    return _redact_mapping(node)


def _dom_selector_type():
    from .browser import DOMSelector
    return DOMSelector


def _is_dom_selector(value: Any) -> bool:
    return isinstance(value, _dom_selector_type())


def _new_dom_selector(**values: Any) -> Any:
    return _dom_selector_type()(**values)


_CSS_SELECTOR_RE = re.compile(
    r"^(?:[#.\[]|(?:a|button|input|textarea|select|form|main|nav|article|section)"
    r"(?:[#.\[:]|$))",
    re.IGNORECASE,
)


def _coerce_dom_target(value: Any) -> Any:
    """Interpret unambiguous CSS strings as CSS, ordinary strings as text."""
    if isinstance(value, str):
        clean = value.strip()
        if _CSS_SELECTOR_RE.search(clean) or "," in clean or " > " in clean:
            return {"css": clean}
    return value


def canonical_selector_value(selector: Any) -> dict[str, Any]:
    """Return a deterministic, JSON-safe semantic selector representation."""
    if _is_dom_selector(selector):
        raw = {name: getattr(selector, name) for name in selector.__dataclass_fields__}
    elif isinstance(selector, Mapping):
        raw = dict(selector)
    elif isinstance(selector, int) and not isinstance(selector, bool):
        raw = {"index": selector}
    elif isinstance(selector, str):
        raw = {"text": selector}
    else:
        raise TypeError(f"unsupported selector value: {type(selector).__name__}")

    result: dict[str, Any] = {}
    for key, value in raw.items():
        name = _normalise_key(key)
        if value is None or value == "":
            continue
        if isinstance(value, bool):
            result[name] = value
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            result[name] = value
        else:
            normalised = _normalise_text(value)
            if normalised:
                result[name] = normalised
    return {key: result[key] for key in sorted(result)}


def canonical_selector_fingerprint(
    selector_type: str,
    selector_value: Any,
    session_id: str,
    dom_hash: str,
) -> str:
    """Hash the versioned canonical selector payload used by Risk Gate.

    The same function is used when a grant is issued and when a mutation is
    authorized, so equivalent selectors cannot diverge because of dictionary
    ordering or Playwright object identity.
    """
    payload = {
        "version": 1,
        "selector_type": _normalise_key(selector_type),
        "selector_value": canonical_selector_value(selector_value),
        "session_id": str(session_id),
        "dom_hash": _normalise_text(dom_hash).casefold(),
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sf1:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BrowserSession:
    session_id: str
    url: str = ""
    title: str = ""
    dom_hash: str = ""
    status: str = "open"
    created_at: float = field(default_factory=time.time)
    last_observed_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "url": self.url,
            "title": self.title,
            "dom_hash": self.dom_hash,
            "status": self.status,
            "created_at": self.created_at,
            "last_observed_at": self.last_observed_at,
        }


@dataclass(frozen=True)
class FindResult:
    found: bool
    selector: Any
    selector_type: str
    confidence: float
    element_summary: Mapping[str, Any]
    dom_hash: str
    alternatives: tuple[Mapping[str, Any], ...] = ()

    @property
    def selector_value(self) -> dict[str, Any]:
        return canonical_selector_value(self.selector or {})

    def fingerprint_for(self, session_id: str) -> str:
        if self.selector is None:
            return ""
        return canonical_selector_fingerprint(
            self.selector_type, self.selector_value, session_id, self.dom_hash
        )

    def to_dict(self, *, session_id: str = "") -> dict[str, Any]:
        selector_value = self.selector_value
        return {
            "found": self.found,
            "selector": selector_value,
            "selector_type": self.selector_type,
            "confidence": self.confidence,
            "element_summary": _redact_mapping(self.element_summary),
            "dom_hash": self.dom_hash,
            "alternatives": [_redact_mapping(item) for item in self.alternatives],
            "selector_fingerprint": (
                canonical_selector_fingerprint(
                    self.selector_type, selector_value, session_id, self.dom_hash
                )
                if self.selector is not None and session_id
                else None
            ),
        }


@dataclass(frozen=True)
class ConfirmationGrant:
    grant_id: str
    action: str
    session_id: str
    selector_fingerprint: str
    expires_at: float

    def is_valid(
        self,
        *,
        action: str,
        session_id: str,
        selector_fingerprint: str,
        now: float | None = None,
    ) -> bool:
        return (
            _normalise_key(self.action) == _normalise_key(action)
            and self.session_id == session_id
            and self.selector_fingerprint == selector_fingerprint
            and float(now if now is not None else time.time()) <= self.expires_at
        )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ConfirmationGrant":
        return cls(
            grant_id=str(value.get("grant_id", "")),
            action=str(value.get("action", "")),
            session_id=str(value.get("session_id", "")),
            selector_fingerprint=str(value.get("selector_fingerprint", "")),
            expires_at=float(value.get("expires_at", 0.0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "action": self.action,
            "session_id": self.session_id,
            "selector_fingerprint": self.selector_fingerprint,
            "expires_at": self.expires_at,
        }


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    requires_confirmation: bool = False
    blocked_reason: str | None = None
    risk: str = "low"


class BrowserPolicy:
    """Policy boundary; ``confirm=True`` is never an authorization grant."""

    _risky_words = frozenset({
        "buy", "checkout", "confirm", "login", "order", "pay", "purchase",
        "send", "signin", "submit", "subscribe", "transfer", "delete", "remove",
    })

    def assess(self, action: str, element_summary: Mapping[str, Any] | None = None) -> PolicyDecision:
        summary = {str(key).casefold(): value for key, value in (element_summary or {}).items()}
        haystack = " ".join(str(summary.get(key, "")) for key in (
            "name", "text", "automation_id", "test_id", "href", "type", "role",
        )).casefold()
        risky = (
            _normalise_key(action) in self._risky_words
            or bool(summary.get("requires_confirmation"))
            or str(summary.get("type", "")).casefold() in {"submit", "password", "image"}
            or any(word in haystack for word in self._risky_words)
        )
        return PolicyDecision(
            allowed=not risky,
            requires_confirmation=risky,
            blocked_reason="CONFIRMATION_REQUIRED" if risky else None,
            risk="high" if risky else "low",
        )

    def authorize(
        self,
        *,
        action: str,
        element_summary: Mapping[str, Any] | None,
        session_id: str,
        selector_fingerprint: str,
        grant: ConfirmationGrant | None = None,
        now: float | None = None,
    ) -> PolicyDecision:
        assessed = self.assess(action, element_summary)
        if not assessed.requires_confirmation:
            return assessed
        if grant is None:
            return assessed
        if not grant.is_valid(
            action=action,
            session_id=session_id,
            selector_fingerprint=selector_fingerprint,
            now=now,
        ):
            return PolicyDecision(
                allowed=False,
                requires_confirmation=True,
                blocked_reason="POLICY_BLOCKED",
                risk="high",
            )
        return PolicyDecision(allowed=True, risk="high")


@dataclass(frozen=True)
class BrowserActionResult:
    success: bool
    action_taken: bool
    requires_confirmation: bool = False
    blocked_reason: str | None = None
    observed_state: Mapping[str, Any] | None = None
    verification: Mapping[str, Any] | None = None
    error: str | None = None
    session_id: str = ""

    @property
    def ok(self) -> bool:
        """Compatibility alias; unlike legacy results this means verified success."""
        return self.success

    def __bool__(self) -> bool:
        return self.success

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "ok": self.success,
            "action_taken": self.action_taken,
            "requires_confirmation": self.requires_confirmation,
            "blocked_reason": self.blocked_reason,
            "observed_state": dict(self.observed_state or {}),
            "verification": dict(self.verification or {}),
            "error": self.error,
            "session_id": self.session_id,
        }


class BrowserBridge:
    """Operator-facing semantic browser facade with verified mutations."""

    def __init__(
        self,
        provider: Any | None = None,
        *,
        policy: BrowserPolicy | None = None,
        session_id_factory: Callable[[], str] | None = None,
        clock: Callable[[], float] | None = None,
        max_nodes: int = 500,
    ) -> None:
        if provider is None:
            from .browser import BrowserAutomationProvider
            provider = BrowserAutomationProvider(headless=True)
        self.provider = provider
        self.policy = policy or BrowserPolicy()
        self._session_id_factory = session_id_factory or (lambda: uuid.uuid4().hex)
        self._clock = clock or time.time
        self.max_nodes = max(1, int(max_nodes))
        self._session: BrowserSession | None = None

    @property
    def session(self) -> BrowserSession | None:
        return self._session

    def _require_session(self) -> BrowserSession:
        session = self._session
        if session is None or session.status != "open":
            raise BrowserBridgeError("Browser session is not open")
        return session

    @staticmethod
    def _dom_hash(nodes: list[Mapping[str, Any]]) -> str:
        canonical = json.dumps(
            nodes, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _page_metadata(self) -> tuple[str, str]:
        engine = getattr(self.provider, "engine", None)
        page = getattr(engine, "_page", None)
        title_attr = getattr(page, "title", "")
        title = title_attr() if callable(title_attr) else title_attr
        return str(getattr(page, "url", "") or ""), str(title or "")

    def open(self, url: str) -> dict[str, Any]:
        self.close()
        try:
            opened = self.provider.open(url)
        except Exception as exc:
            raise BrowserBridgeError(str(exc)) from exc
        self._session = BrowserSession(
            session_id=self._session_id_factory(),
            url=str(opened.get("url", url)) if isinstance(opened, Mapping) else str(url),
            title=str(opened.get("title", "")) if isinstance(opened, Mapping) else "",
            created_at=self._clock(),
        )
        observed = self.observe()
        return {
            "ok": True,
            "session_id": self._session.session_id,
            "url": observed["url"],
            "title": observed["title"],
            "dom_hash": observed["dom_hash"],
        }

    def navigate(self, url: str) -> dict[str, Any]:
        self._require_session()
        try:
            self.provider.navigate(url)
        except Exception as exc:
            raise BrowserBridgeError(str(exc)) from exc
        observed = self.observe()
        return {"ok": True, **{key: observed[key] for key in ("session_id", "url", "title", "dom_hash")}}

    def observe(self) -> dict[str, Any]:
        session = self._require_session()
        try:
            nodes = list(self.provider.inspect_dom(max_nodes=self.max_nodes))
        except TypeError:
            # Test doubles and older providers may not expose max_nodes.
            nodes = list(self.provider.inspect_dom())
        except Exception as exc:
            raise BrowserBridgeError(str(exc)) from exc
        url, title = self._page_metadata()
        if not url:
            url = session.url
        if not title:
            title = session.title
        # Hash the provider's complete semantic snapshot for stale detection,
        # but expose only redacted nodes to callers and logs.
        dom_hash = self._dom_hash(nodes)
        safe_nodes = [_redact_node(node) for node in nodes]
        self._session = replace(
            session, url=url, title=title, dom_hash=dom_hash,
            last_observed_at=self._clock(),
        )
        return {
            "ok": True,
            "session_id": session.session_id,
            "url": url,
            "title": title,
            "dom_hash": dom_hash,
            "nodes": safe_nodes,
            "observed_at": self._session.last_observed_at,
        }

    def inspect_dom(self, *, max_nodes: int | None = None) -> list[dict[str, Any]]:
        if max_nodes is not None:
            old = self.max_nodes
            self.max_nodes = max(1, int(max_nodes))
            try:
                return list(self.observe()["nodes"])
            finally:
                self.max_nodes = old
        return list(self.observe()["nodes"])

    @staticmethod
    def _selector_type(selector: Any) -> str:
        if selector.test_id:
            return "test_id"
        if selector.automation_id:
            return "automation_id"
        if selector.role and selector.name:
            return "role_name"
        if selector.role:
            return "role"
        if selector.label:
            return "label"
        if selector.text or selector.name:
            return "text"
        if selector.css:
            return "css"
        return "unknown"

    @staticmethod
    def _confidence(selector_type: str, found: bool) -> float:
        if not found:
            return 0.0
        return {
            "test_id": 0.995,
            "automation_id": 0.99,
            "role_name": 0.98,
            "role": 0.92,
            "label": 0.96,
            "text": 0.85,
            "css": 0.80,
            "index": 0.70,
        }.get(selector_type, 0.50)

    def _find_index(self, index: int, observed: Mapping[str, Any]) -> FindResult:
        nodes = list(observed.get("nodes", []))
        if index < 0 or index >= len(nodes):
            return FindResult(False, None, "index", 0.0, {}, str(observed["dom_hash"]))
        node = dict(nodes[index])
        selector = _new_dom_selector(
            test_id=str(node.get("test_id") or ""),
            automation_id=str(node.get("automation_id") or node.get("id") or ""),
            role=str(node.get("role") or ""),
            name=str(node.get("name") or node.get("text") or ""),
        )
        if not any(canonical_selector_value(selector).values()):
            selector = _new_dom_selector(text=str(node.get("text") or node.get("name") or index))
        return FindResult(True, selector, "index", 0.70, node, (), str(observed["dom_hash"]))

    def find(self, target: Any) -> FindResult:
        session = self._require_session()
        observed = self.observe()
        if isinstance(target, int) and not isinstance(target, bool):
            return self._find_index(target, observed)
        try:
            selector = _dom_selector_type().from_value(_coerce_dom_target(target))
            matches = list(self.provider.find(selector))
        except Exception as exc:
            raise BrowserBridgeError(str(exc)) from exc
        selector_type = self._selector_type(selector)
        summary = _redact_mapping(matches[0]) if matches else {}
        alternatives = tuple(_redact_mapping(item) for item in matches[1:])
        return FindResult(
            bool(matches), selector, selector_type,
            self._confidence(selector_type, bool(matches)), summary,
            str(observed["dom_hash"]), alternatives,
        )

    def _resolve(self, target: Any) -> FindResult:
        if isinstance(target, FindResult):
            return target
        return self.find(target)

    def _stale(self, result: FindResult, current: Mapping[str, Any]) -> BrowserActionResult | None:
        session = self._require_session()
        if not result.found or result.selector is None:
            return BrowserActionResult(
                False, False, False, "ELEMENT_NOT_FOUND", dict(current),
                {"ok": False, "method": "find", "detail": "element not found"},
                "element not found", session.session_id,
            )
        if result.dom_hash != current["dom_hash"]:
            return BrowserActionResult(
                False, False, False, "STALE_DOM", {
                    "dom_hash": current["dom_hash"],
                    "previous_dom_hash": result.dom_hash,
                }, {
                    "ok": False, "method": "dom_hash", "detail": "DOM changed; re-observe and re-resolve",
                }, "DOM snapshot is stale", session.session_id,
            )
        return None

    @staticmethod
    def _compact_observation(observed: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "session_id": observed.get("session_id"),
            "url": observed.get("url"),
            "title": observed.get("title"),
            "dom_hash": observed.get("dom_hash"),
            "node_count": len(observed.get("nodes", [])),
        }

    def _observe_after_action(
        self,
        *,
        timeout: float = 5.0,
        previous: Mapping[str, Any] | None = None,
        require_change: bool = False,
    ) -> dict[str, Any]:
        """Observe a stable post-action state, tolerating navigation races."""
        deadline = time.monotonic() + max(0.1, timeout)
        last_error: Exception | None = None
        latest: dict[str, Any] | None = None
        stable_signature: tuple[Any, ...] | None = None
        stable_count = 0
        before = (
            previous.get("url"), previous.get("title"), previous.get("dom_hash")
        ) if previous is not None else None
        settle = getattr(self.provider, "settle", None)
        if callable(settle):
            try:
                settle(timeout=timeout)
            except Exception as exc:
                last_error = exc
        while time.monotonic() < deadline:
            try:
                observed = self.observe()
            except BrowserBridgeError as exc:
                last_error = exc
                time.sleep(0.1)
                continue
            latest = observed
            signature = (
                observed.get("url"), observed.get("title"), observed.get("dom_hash")
            )
            changed = before is None or signature != before
            if not require_change or changed:
                if signature == stable_signature:
                    stable_count += 1
                else:
                    stable_signature = signature
                    stable_count = 1
                if stable_count >= 2:
                    return observed
            time.sleep(0.1)
        if latest is not None:
            signature = (
                latest.get("url"), latest.get("title"), latest.get("dom_hash")
            )
            if not require_change or before is None or signature != before:
                return latest
            raise BrowserBridgeError("browser action produced no observable page change")
        if last_error is not None:
            raise last_error
        return self.observe()

    @staticmethod
    def _verify(expected: Mapping[str, Any] | None, observed: Mapping[str, Any], *, method: str) -> dict[str, Any]:
        if expected is None:
            return {"ok": True, "method": method, "detail": "post-action observation completed"}

        def matches(wanted: Any, actual: Any) -> bool:
            if isinstance(wanted, Mapping) and isinstance(actual, Mapping):
                return all(key in actual and matches(value, actual[key]) for key, value in wanted.items())
            if isinstance(wanted, (list, tuple)) and isinstance(actual, (list, tuple)):
                return len(wanted) == len(actual) and all(matches(a, b) for a, b in zip(wanted, actual))
            return wanted == actual

        ok = matches(expected, observed)
        return {
            "ok": ok,
            "method": method,
            "detail": "expected state matched" if ok else "expected state mismatch",
            "expected": dict(expected),
        }

    def _authorize(
        self,
        action: str,
        result: FindResult,
        grant: ConfirmationGrant | Mapping[str, Any] | None,
    ) -> PolicyDecision:
        session = self._require_session()
        selector_value = result.selector_value
        fingerprint = canonical_selector_fingerprint(
            result.selector_type, selector_value, session.session_id, result.dom_hash
        )
        if grant is not None and not isinstance(grant, ConfirmationGrant):
            grant = ConfirmationGrant.from_mapping(grant)
        return self.policy.authorize(
            action=action,
            element_summary=result.element_summary,
            session_id=session.session_id,
            selector_fingerprint=fingerprint,
            grant=grant,
            now=self._clock(),
        )

    def _blocked(self, decision: PolicyDecision) -> BrowserActionResult:
        session = self._require_session()
        return BrowserActionResult(
            False, False, decision.requires_confirmation, decision.blocked_reason,
            {"session_id": session.session_id, "dom_hash": session.dom_hash},
            {"ok": False, "method": "policy", "detail": decision.blocked_reason},
            decision.blocked_reason, session.session_id,
        )

    def click(
        self,
        target: FindResult | DOMSelector | Mapping[str, Any] | str | int,
        *,
        confirm: bool = False,
        confirmation_grant: ConfirmationGrant | Mapping[str, Any] | None = None,
        expected_state: Mapping[str, Any] | None = None,
        fresh_resolution: bool = False,
    ) -> BrowserActionResult:
        del confirm  # compatibility hint; policy/grant is authoritative
        session = self._require_session()
        supplied_result = isinstance(target, FindResult)
        resolved = self._resolve(target)
        if supplied_result and not fresh_resolution:
            current = self.observe()
            stale = self._stale(resolved, current)
            if stale is not None:
                return stale
        else:
            current = {
                "session_id": session.session_id,
                "url": self._session.url,
                "title": self._session.title,
                "dom_hash": resolved.dom_hash,
                "nodes": [],
            }
        decision = self._authorize("click", resolved, confirmation_grant)
        if not decision.allowed:
            return self._blocked(decision)
        try:
            if isinstance(target, int) and not isinstance(target, bool):
                raw = self.provider.click(target, confirm=True)
            else:
                raw = self.provider.click(resolved.selector, confirm=True)
        except Exception as exc:
            return BrowserActionResult(
                False, False, decision.requires_confirmation, None,
                self._compact_observation(current), None, str(exc), session.session_id,
            )
        taken = bool(raw.get("action_taken", raw.get("ok", False))) if isinstance(raw, Mapping) else bool(raw)
        if not taken:
            return BrowserActionResult(
                False, False, decision.requires_confirmation, "EXECUTION_FAILED",
                self._compact_observation(current), {"ok": False, "method": "execute"},
                str(raw.get("error", "click was not executed")) if isinstance(raw, Mapping) else "click was not executed",
                session.session_id,
            )
        page_changed = True
        try:
            observed = self._observe_after_action(previous=current, require_change=True)
        except BrowserBridgeError as exc:
            if "no observable page change" not in str(exc):
                raise
            page_changed = False
            observed = self._observe_after_action(previous=current, require_change=False)
        if expected_state is not None:
            verification = self._verify(expected_state, observed, method="post_click_observation")
        else:
            postcondition = raw.get("postcondition", {}) if isinstance(raw, Mapping) else {}
            semantic_change = bool(
                page_changed
                or postcondition.get("focused")
                or postcondition.get("checked_changed")
                or postcondition.get("url_changed")
            )
            verification = {
                "ok": semantic_change,
                "method": "post_click_observation" if page_changed else "semantic_click_postcondition",
                "detail": (
                    "page state changed after click" if page_changed
                    else "clicked element received focus or changed state" if semantic_change
                    else "click was sent but no target postcondition was observed"
                ),
            }
        return BrowserActionResult(
            bool(verification["ok"]), True, decision.requires_confirmation, None,
            self._compact_observation(observed), verification, None, session.session_id,
        )

    def press(
        self,
        target: FindResult | DOMSelector | Mapping[str, Any] | str | int,
        key: str,
        *,
        confirmation_grant: ConfirmationGrant | Mapping[str, Any] | None = None,
        expected_state: Mapping[str, Any] | None = None,
    ) -> BrowserActionResult:
        session = self._require_session()
        resolved = self._resolve(target)
        current = {
            "session_id": session.session_id,
            "url": self._session.url,
            "title": self._session.title,
            "dom_hash": resolved.dom_hash,
            "nodes": [],
        }
        decision = self._authorize("press", resolved, confirmation_grant)
        if not decision.allowed:
            return self._blocked(decision)
        try:
            raw = self.provider.press(
                target if isinstance(target, int) and not isinstance(target, bool) else resolved.selector,
                str(key),
            )
        except Exception as exc:
            return BrowserActionResult(
                False, False, decision.requires_confirmation, None,
                self._compact_observation(current), None, str(exc), session.session_id,
            )
        taken = bool(raw.get("action_taken", raw.get("ok", False))) if isinstance(raw, Mapping) else bool(raw)
        if not taken:
            return BrowserActionResult(
                False, False, decision.requires_confirmation, "EXECUTION_FAILED",
                self._compact_observation(current), {"ok": False, "method": "execute"},
                "key press was not executed", session.session_id,
            )
        try:
            observed = self._observe_after_action(previous=current, require_change=True)
        except BrowserBridgeError as exc:
            return BrowserActionResult(
                False, True, decision.requires_confirmation, None,
                self._compact_observation(current),
                {"ok": False, "method": "post_key_observation", "detail": str(exc)},
                str(exc), session.session_id,
            )
        verification = self._verify(expected_state, observed, method="post_key_observation")
        return BrowserActionResult(
            bool(verification["ok"]), True, decision.requires_confirmation, None,
            self._compact_observation(observed), verification, None, session.session_id,
        )

    def type(
        self,
        target: FindResult | DOMSelector | Mapping[str, Any] | str | int,
        text: str,
        *,
        confirmation_grant: ConfirmationGrant | Mapping[str, Any] | None = None,
        expected_state: Mapping[str, Any] | None = None,
    ) -> BrowserActionResult:
        session = self._require_session()
        supplied_result = isinstance(target, FindResult)
        resolved = self._resolve(target)
        if supplied_result:
            current = self.observe()
            stale = self._stale(resolved, current)
            if stale is not None:
                return stale
        else:
            current = {
                "session_id": session.session_id,
                "url": self._session.url,
                "title": self._session.title,
                "dom_hash": resolved.dom_hash,
                "nodes": [],
            }
        decision = self._authorize("type", resolved, confirmation_grant)
        if not decision.allowed:
            return self._blocked(decision)
        try:
            raw = self.provider.type(
                target if isinstance(target, int) and not isinstance(target, bool) else resolved.selector,
                text,
            )
        except Exception as exc:
            return BrowserActionResult(
                False, False, decision.requires_confirmation, None,
                self._compact_observation(current), None, str(exc), session.session_id,
            )
        taken = bool(raw.get("action_taken", raw.get("ok", False))) if isinstance(raw, Mapping) else bool(raw)
        if not taken:
            return BrowserActionResult(
                False, False, decision.requires_confirmation, "EXECUTION_FAILED",
                self._compact_observation(current), {"ok": False, "method": "execute"},
                "type was not executed", session.session_id,
            )
        observed = self._observe_after_action(previous=current, require_change=True)
        if expected_state is not None:
            verification = self._verify(expected_state, observed, method="post_type_observation")
        else:
            # Read back through semantic metadata.  The value itself never
            # enters the result for password-like controls.
            refreshed = self.find(resolved.selector)
            is_secret = str(resolved.element_summary.get("type", "")).casefold() == "password"
            actual_value = str(refreshed.element_summary.get("value", ""))
            raw_ok = bool(raw.get("ok", True)) if isinstance(raw, Mapping) else bool(raw)
            verification = {
                "ok": raw_ok and (is_secret or actual_value == text),
                "method": "semantic_value_readback",
                "detail": "value readback matched" if is_secret or actual_value == text else "value readback mismatch",
                "value_present": bool(actual_value) if is_secret else None,
            }
        # Do not persist or return typed text. Password-like fields are policy
        # gated and only expose boolean verification metadata.
        return BrowserActionResult(
            bool(verification["ok"]), True, decision.requires_confirmation, None,
            self._compact_observation(observed), verification, None, session.session_id,
        )

    def read(self) -> dict[str, Any]:
        self._require_session()
        try:
            result = self.provider.read_page()
        except Exception as exc:
            raise BrowserBridgeError(str(exc)) from exc
        observed = self._observe_after_action()
        payload = dict(result) if isinstance(result, Mapping) else {"text": result}
        return {**_redact_mapping(payload), **self._compact_observation(observed)}

    def wait(self, target: float | DOMSelector | Mapping[str, Any] | str, *, timeout: float = 10) -> dict[str, Any]:
        self._require_session()
        try:
            result = self.provider.wait(target, timeout=timeout)
        except Exception as exc:
            raise BrowserBridgeError(str(exc)) from exc
        observed = self.observe()
        return {"ok": True, "result": result, **self._compact_observation(observed)}

    def extract(self, target: Any = None) -> dict[str, Any]:
        self._require_session()
        secret_index = False
        if isinstance(target, int) and not isinstance(target, bool):
            observed = self.observe()
            nodes = list(observed.get("nodes", []))
            secret_index = 0 <= target < len(nodes) and _is_secret_mapping(nodes[target])
        try:
            result = self.provider.extract(target)
        except Exception as exc:
            raise BrowserBridgeError(str(exc)) from exc
        if not isinstance(result, Mapping):
            return {"ok": True, "value": "<redacted>" if secret_index else result}
        payload = _redact_mapping(result)
        if secret_index:
            for key in ("text", "value"):
                if key in payload:
                    payload[f"{key}_present"] = bool(payload.pop(key))
        return payload

    def download(
        self,
        target: FindResult | DOMSelector | Mapping[str, Any] | str | int,
        *,
        directory: Path | str,
        confirm: bool = False,
        confirmation_grant: ConfirmationGrant | Mapping[str, Any] | None = None,
        fresh_resolution: bool = False,
    ) -> BrowserActionResult:
        del confirm
        session = self._require_session()
        supplied_result = isinstance(target, FindResult)
        resolved = self._resolve(target)
        if supplied_result and not fresh_resolution:
            current = self.observe()
            stale = self._stale(resolved, current)
            if stale is not None:
                return stale
        else:
            current = {
                "session_id": session.session_id,
                "url": self._session.url,
                "title": self._session.title,
                "dom_hash": resolved.dom_hash,
                "nodes": [],
            }
        decision = self._authorize("download", resolved, confirmation_grant)
        if not decision.allowed:
            return self._blocked(decision)
        try:
            raw = self.provider.download(
                target if isinstance(target, int) and not isinstance(target, bool) else resolved.selector,
                directory=directory,
                confirm=True,
            )
        except Exception as exc:
            return BrowserActionResult(
                False, False, decision.requires_confirmation, None,
                self._compact_observation(current), None, str(exc), session.session_id,
            )
        taken = bool(raw.get("action_taken", raw.get("ok", False))) if isinstance(raw, Mapping) else bool(raw)
        observed = self._observe_after_action()
        verification = {"ok": taken, "method": "download_exists", "detail": "download completed" if taken else "download failed"}
        return BrowserActionResult(
            bool(taken), taken, decision.requires_confirmation, None if taken else "EXECUTION_FAILED",
            self._compact_observation(observed), verification,
            None if taken else "download was not completed", session.session_id,
        )

    def close(self) -> dict[str, Any]:
        previous = self._session
        try:
            result = self.provider.close()
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}
        if previous is not None:
            self._session = replace(previous, status="closed")
        return {
            "ok": bool(result.get("ok", True)) if isinstance(result, Mapping) else True,
            "closed": True,
            "session_id": previous.session_id if previous else None,
            "result": result,
        }
