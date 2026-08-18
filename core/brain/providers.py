"""Provider adapters. Compatible HTTP protocols share one implementation."""
from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterator
from typing import Any
from urllib.parse import urlparse

try:  # The project normally provides requests; keep the local demo stdlib-only.
    import requests
except ImportError:  # pragma: no cover - exercised only in minimal runtimes
    import urllib.error
    import urllib.request

    class _FallbackRequestException(Exception):
        pass

    class _FallbackTimeout(_FallbackRequestException):
        pass

    class _FallbackResponse:
        def __init__(self, response):
            self.status_code = int(response.status)
            self._body = response.read()
            self.text = self._body.decode("utf-8", errors="replace")

        @property
        def ok(self):
            return 200 <= self.status_code < 300

        def json(self):
            return json.loads(self._body.decode("utf-8"))

        def raise_for_status(self):
            if not self.ok:
                raise _FallbackRequestException(f"HTTP {self.status_code}")

        def iter_lines(self, decode_unicode=False):
            for line in self._body.splitlines():
                yield line.decode("utf-8", errors="replace") if decode_unicode else line

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class _FallbackSession:
        @staticmethod
        def _request(method, url, *, headers=None, json=None, timeout=None, stream=False):
            data = json_module.dumps(json).encode("utf-8") if json is not None else None
            request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
            try:
                return _FallbackResponse(urllib.request.urlopen(request, timeout=timeout))
            except TimeoutError as exc:
                raise _FallbackTimeout(str(exc)) from exc
            except urllib.error.URLError as exc:
                raise _FallbackRequestException(str(exc)) from exc

        def get(self, url, **kwargs):
            return self._request("GET", url, **kwargs)

        def post(self, url, **kwargs):
            return self._request("POST", url, **kwargs)

        def close(self):
            return None

    json_module = json
    class _RequestsFallback:
        Session = _FallbackSession
        RequestException = _FallbackRequestException
        Timeout = _FallbackTimeout
    requests = _RequestsFallback()

from core.security.redaction import redact_text

from .models import (
    BrainRequest, BrainResult, HealthSnapshot, HealthStatus,
    ModelCapabilityProfile, ProviderConfig, ProviderResponseError,
    ProviderUnavailable,
)
from .provider import BrainProvider
from .secrets import EnvironmentSecretStore, SecretStore


class OpenAICompatibleProvider(BrainProvider):
    def __init__(self, config: ProviderConfig, *, secret_store: SecretStore | None = None,
                 timeout: float | None = None, session: requests.Session | None = None) -> None:
        self.config = config
        self.name = config.name
        host = (urlparse(config.base_url).hostname or "").casefold()
        self.external = bool(config.external or host not in {"127.0.0.1", "localhost", "::1"})
        self._secret_store = secret_store or EnvironmentSecretStore()
        self._timeout = float(timeout if timeout is not None else config.timeout_seconds)
        self._session = session or requests.Session()
        self._cancelled = threading.Event()

    def _headers(self) -> dict[str, str]:
        headers = {"accept": "application/json", "content-type": "application/json"}
        headers.update(self.config.headers)
        if self.config.api_key_ref:
            key = self._secret_store.get(self.config.api_key_ref)
            if not key:
                raise ProviderUnavailable(f"provider {self.name} credential is unavailable")
            headers["authorization"] = f"Bearer {key}"
        return headers

    def health(self) -> HealthSnapshot:
        started = time.perf_counter()
        try:
            response = self._session.get(
                f"{self.config.base_url}/models", headers=self._headers(),
                timeout=min(self._timeout, 1.0),
            )
            status = HealthStatus.AVAILABLE if response.ok else HealthStatus.DEGRADED
            return HealthSnapshot(status=status, latency_ms=(time.perf_counter() - started) * 1000,
                                  recent_success=response.ok)
        except requests.RequestException as exc:
            return HealthSnapshot(status=HealthStatus.OFFLINE,
                                  latency_ms=(time.perf_counter() - started) * 1000,
                                  failures=1, last_error=redact_text(str(exc))[:240])

    def models(self) -> tuple[str, ...]:
        configured = tuple(model.model for model in self.config.models)
        # A declared profile is authoritative for routing and avoids a network
        # round-trip on every user request. Discovery is still available when
        # the provider has no configured model metadata.
        if configured:
            return configured
        try:
            response = self._session.get(
                f"{self.config.base_url}/models", headers=self._headers(), timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data", []) if isinstance(payload, dict) else []
            names = tuple(str(item.get("id")) for item in data
                          if isinstance(item, dict) and item.get("id"))
            return names
        except (requests.RequestException, ValueError, TypeError):
            return tuple(model.model for model in self.config.models)

    def _select_model(self, request: BrainRequest, model: str | None) -> str:
        if model:
            return model
        for profile in self.config.models:
            if profile.supports(request.role, request.required_capabilities):
                return profile.model
        raise ProviderUnavailable(f"provider {self.name} has no model for role {request.role.value}")

    def generate(self, request: BrainRequest, *, model: str | None = None) -> BrainResult:
        selected = self._select_model(request, model)
        self._cancelled.clear()
        messages = [dict(item) for item in request.messages]
        if not messages:
            messages = [{"role": "user", "content": request.user_request}]
        if request.system:
            messages.insert(0, {"role": "system", "content": request.system})
        payload: dict[str, Any] = {"model": selected, "messages": messages, "stream": False}
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        started = time.perf_counter()
        try:
            response = self._session.post(
                f"{self.config.base_url}/chat/completions", headers=self._headers(),
                json=payload, timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.Timeout as exc:
            raise ProviderUnavailable(f"provider {self.name} timed out") from exc
        except requests.RequestException as exc:
            raise ProviderUnavailable(redact_text(f"provider {self.name} unavailable: {exc}")) from exc
        except ValueError as exc:
            raise ProviderResponseError(f"provider {self.name} returned malformed JSON") from exc
        if self._cancelled.is_set():
            raise ProviderUnavailable(f"provider {self.name} request cancelled")
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderResponseError(f"provider {self.name} returned an invalid response shape") from exc
        if not isinstance(content, str) or not content.strip():
            raise ProviderResponseError(f"provider {self.name} returned empty content")
        return BrainResult(
            text=content.strip(), provider=self.name, model=selected, role=request.role,
            latency_ms=(time.perf_counter() - started) * 1000,
            finish_reason=str(choice.get("finish_reason", "stop")),
            usage=dict(data.get("usage", {})) if isinstance(data, dict) else {},
            raw=data,
        )

    def stream(self, request: BrainRequest, *, model: str | None = None) -> Iterator[str]:
        profile = self.capabilities(self._select_model(request, model))
        if not profile.streaming:
            yield self.generate(request, model=profile.model).text
            return
        selected = profile.model
        messages = [dict(item) for item in request.messages] or [
            {"role": "user", "content": request.user_request},
        ]
        if request.system:
            messages.insert(0, {"role": "system", "content": request.system})
        self._cancelled.clear()
        try:
            with self._session.post(
                f"{self.config.base_url}/chat/completions", headers=self._headers(),
                json={"model": selected, "messages": messages, "stream": True},
                timeout=self._timeout, stream=True,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines(decode_unicode=True):
                    if self._cancelled.is_set():
                        break
                    if not line or not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        payload = json.loads(raw)
                        chunk = payload["choices"][0]["delta"].get("content", "")
                    except (ValueError, KeyError, IndexError, TypeError) as exc:
                        raise ProviderResponseError("malformed streaming response") from exc
                    if chunk:
                        yield str(chunk)
        except requests.RequestException as exc:
            raise ProviderUnavailable(redact_text(f"provider {self.name} stream unavailable: {exc}")) from exc

    def cancel(self, request_id: str | None = None) -> bool:
        self._cancelled.set()
        return True

    def capabilities(self, model: str) -> ModelCapabilityProfile:
        for profile in self.config.models:
            if profile.model == model:
                return profile
        raise KeyError(model)

    def close(self) -> None:
        self._session.close()


class OpenAIProvider(OpenAICompatibleProvider):
    def __init__(self, config: ProviderConfig, **kwargs) -> None:
        super().__init__(config, **kwargs)
        self.external = True


class OpenRouterProvider(OpenAICompatibleProvider):
    def __init__(self, config: ProviderConfig, **kwargs) -> None:
        super().__init__(config, **kwargs)
        self.external = True


class AnthropicProvider(OpenAICompatibleProvider):
    """Anthropic Messages API adapter with the shared cancellation/error contract."""

    def __init__(self, config: ProviderConfig, **kwargs) -> None:
        super().__init__(config, **kwargs)
        self.external = True

    def _headers(self) -> dict[str, str]:
        headers = {"accept": "application/json", "content-type": "application/json",
                   "anthropic-version": "2023-06-01"}
        headers.update(self.config.headers)
        if self.config.api_key_ref:
            key = self._secret_store.get(self.config.api_key_ref)
            if not key:
                raise ProviderUnavailable(f"provider {self.name} credential is unavailable")
            headers["x-api-key"] = key
        return headers

    def generate(self, request: BrainRequest, *, model: str | None = None) -> BrainResult:
        selected = self._select_model(request, model)
        messages = [dict(item) for item in request.messages
                    if str(item.get("role", "")) in {"user", "assistant"}]
        if not messages:
            messages = [{"role": "user", "content": request.user_request}]
        payload: dict[str, Any] = {
            "model": selected, "messages": messages,
            "max_tokens": request.max_tokens or 1024,
        }
        if request.system:
            payload["system"] = request.system
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        started = time.perf_counter()
        try:
            response = self._session.post(
                f"{self.config.base_url}/messages", headers=self._headers(),
                json=payload, timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.Timeout as exc:
            raise ProviderUnavailable(f"provider {self.name} timed out") from exc
        except requests.RequestException as exc:
            raise ProviderUnavailable(redact_text(f"provider {self.name} unavailable: {exc}")) from exc
        except ValueError as exc:
            raise ProviderResponseError(f"provider {self.name} returned malformed JSON") from exc
        blocks = data.get("content", []) if isinstance(data, dict) else []
        text = "".join(
            str(block.get("text", "")) for block in blocks
            if isinstance(block, dict) and block.get("type") == "text"
        ).strip()
        if not text:
            raise ProviderResponseError(f"provider {self.name} returned an invalid response shape")
        return BrainResult(
            text, self.name, selected, request.role,
            (time.perf_counter() - started) * 1000,
            finish_reason=str(data.get("stop_reason", "stop")),
            usage=dict(data.get("usage", {})), raw=data,
        )

    def stream(self, request: BrainRequest, *, model: str | None = None) -> Iterator[str]:
        """Consume Anthropic's Messages SSE format without routing it through
        the OpenAI-compatible `/chat/completions` endpoint.
        """
        profile = self.capabilities(self._select_model(request, model))
        if not profile.streaming:
            yield self.generate(request, model=profile.model).text
            return
        selected = profile.model
        messages = [dict(item) for item in request.messages
                    if str(item.get("role", "")) in {"user", "assistant"}]
        if not messages:
            messages = [{"role": "user", "content": request.user_request}]
        payload: dict[str, Any] = {
            "model": selected, "messages": messages,
            "max_tokens": request.max_tokens or 1024, "stream": True,
        }
        if request.system:
            payload["system"] = request.system
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        self._cancelled.clear()
        try:
            with self._session.post(
                f"{self.config.base_url}/messages", headers=self._headers(),
                json=payload, timeout=self._timeout, stream=True,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines(decode_unicode=True):
                    if self._cancelled.is_set():
                        break
                    if not line or not line.startswith("data:"):
                        continue
                    try:
                        event = json.loads(line[5:].strip())
                    except (ValueError, TypeError) as exc:
                        raise ProviderResponseError("malformed Anthropic streaming response") from exc
                    if event.get("type") == "message_stop":
                        break
                    delta = event.get("delta", {})
                    chunk = delta.get("text", "") if isinstance(delta, dict) else ""
                    if chunk:
                        yield str(chunk)
        except requests.Timeout as exc:
            raise ProviderUnavailable(f"provider {self.name} timed out") from exc
        except requests.RequestException as exc:
            raise ProviderUnavailable(redact_text(f"provider {self.name} stream unavailable: {exc}")) from exc


class BackendProviderAdapter(BrainProvider):
    """Adapts an existing `LLMBackend` without duplicating its transport."""

    def __init__(self, name: str, backend: Any,
                 profiles: tuple[ModelCapabilityProfile, ...], *, external: bool) -> None:
        self.name = name
        self.backend = backend
        self.external = external
        self._profiles = {profile.model: profile for profile in profiles}

    def health(self) -> HealthSnapshot:
        started = time.perf_counter()
        try:
            available = bool(self.backend.is_available())
        except Exception:
            available = False
        return HealthSnapshot(
            HealthStatus.AVAILABLE if available else HealthStatus.OFFLINE,
            latency_ms=(time.perf_counter() - started) * 1000,
            recent_success=available,
        )

    def models(self) -> tuple[str, ...]:
        return tuple(self._profiles)

    def generate(self, request: BrainRequest, *, model: str | None = None) -> BrainResult:
        selected = model or next(iter(self._profiles))
        messages = [dict(item) for item in request.messages] or [
            {"role": "user", "content": request.user_request},
        ]
        started = time.perf_counter()
        try:
            text = self.backend.chat(
                messages, system=request.system or None,
                max_tokens=request.max_tokens, temperature=request.temperature,
            )
        except Exception as exc:
            raise ProviderUnavailable(redact_text(f"provider {self.name} unavailable: {exc}")) from exc
        return BrainResult(
            str(text).strip(), self.name, selected, request.role,
            (time.perf_counter() - started) * 1000,
        )

    def stream(self, request: BrainRequest, *, model: str | None = None) -> Iterator[str]:
        messages = [dict(item) for item in request.messages] or [
            {"role": "user", "content": request.user_request},
        ]
        try:
            yield from self.backend.streaming(messages, system=request.system or None)
        except Exception as exc:
            raise ProviderUnavailable(redact_text(f"provider {self.name} stream unavailable: {exc}")) from exc

    def cancel(self, request_id: str | None = None) -> bool:
        cancel = getattr(self.backend, "cancel", None)
        return bool(cancel() if callable(cancel) else False)

    def capabilities(self, model: str) -> ModelCapabilityProfile:
        return self._profiles[model]

    def close(self) -> None:
        self.backend.close()


class LocalGGUFProvider(BackendProviderAdapter):
    def __init__(self, name: str, backend: Any,
                 profiles: tuple[ModelCapabilityProfile, ...]) -> None:
        super().__init__(name, backend, profiles, external=False)


__all__ = [
    "OpenAICompatibleProvider", "OpenAIProvider", "OpenRouterProvider", "AnthropicProvider",
    "BackendProviderAdapter", "LocalGGUFProvider",
]
