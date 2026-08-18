from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from core.brain import (
    BrainHealthManager,
    BrainRequest,
    BrainRole,
    HealthStatus,
    MemorySecretStore,
    ModelCapabilityProfile,
    OpenAICompatibleProvider,
    ProviderConfig,
    ProviderResponseError,
)


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path == "/v1/models":
            self._json(200, {"data": [{"id": "loop-model"}]})
            return
        self._json(404, {"error": "missing"})

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/v1/chat/completions" and payload.get("model") == "loop-model":
            self.server.last_authorization = self.headers.get("authorization")  # type: ignore[attr-defined]
            self._json(200, {"choices": [{"message": {"content": "ATLAS: loopback ok"}}]})
            return
        if self.path == "/v1/chat/completions":
            self._json(200, {"unexpected": True})
            return
        if self.path == "/v1/messages" and payload.get("model") == "claude-loop":
            self.server.last_anthropic_key = self.headers.get("x-api-key")  # type: ignore[attr-defined]
            self._json(200, {"content": [{"type": "text", "text": "ATLAS: anthropic ok"}],
                             "stop_reason": "end_turn", "usage": {"output_tokens": 3}})
            return
        self._json(404, {"error": "missing"})

    def _json(self, status: int, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


@pytest.fixture()
def endpoint():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.last_authorization = None
    server.last_anthropic_key = None
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, f"http://127.0.0.1:{server.server_port}/v1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _profile() -> ModelCapabilityProfile:
    return ModelCapabilityProfile(
        model="loop-model",
        roles=frozenset({BrainRole.CHAT, BrainRole.FAST}),
        streaming=False,
        structured_output=False,
        tool_calling=False,
        vision=False,
        context_window=4096,
        local=True,
    )


def test_openai_compatible_custom_endpoint_uses_provider_contract(endpoint):
    server, base_url = endpoint
    secrets = MemorySecretStore({"loop-key": "test-secret-value"})
    config = ProviderConfig(
        name="my_server", protocol="openai_compatible", base_url=base_url,
        api_key_ref="loop-key", models=(_profile(),), external=False,
    )
    provider = OpenAICompatibleProvider(config, secret_store=secrets, timeout=1.0)

    assert provider.health().status is HealthStatus.AVAILABLE
    assert provider.models() == ("loop-model",)
    result = provider.generate(BrainRequest(user_request="hello", role=BrainRole.FAST))

    assert result.text == "ATLAS: loopback ok"
    assert result.provider == "my_server"
    assert result.model == "loop-model"
    assert provider.capabilities("loop-model") == _profile()
    assert server.last_authorization == "Bearer test-secret-value"


def test_malformed_provider_response_is_inert_error(endpoint):
    _server, base_url = endpoint
    config = ProviderConfig(
        name="malformed", protocol="openai_compatible", base_url=base_url,
        models=(ModelCapabilityProfile(model="bad", roles=frozenset({BrainRole.CHAT}), local=True),),
        external=False,
    )
    provider = OpenAICompatibleProvider(config, secret_store=MemorySecretStore(), timeout=1.0)

    with pytest.raises(ProviderResponseError):
        provider.generate(BrainRequest(user_request="hello", role=BrainRole.CHAT), model="bad")


def test_health_manager_opens_and_recovers_bounded_circuit():
    health = BrainHealthManager(failure_threshold=2, cooldown_seconds=0.01)
    health.record_failure("provider:model", latency_ms=4.0, timeout=True)
    assert health.snapshot("provider:model").status is HealthStatus.DEGRADED
    health.record_failure("provider:model", latency_ms=5.0)
    assert health.snapshot("provider:model").status is HealthStatus.UNHEALTHY
    assert health.allow("provider:model") is False

    health.force_retry("provider:model")
    assert health.allow("provider:model") is True
    health.record_success("provider:model", latency_ms=3.0)
    snapshot = health.snapshot("provider:model")
    assert snapshot.status is HealthStatus.AVAILABLE
    assert snapshot.failures == 2
    assert snapshot.timeouts == 1
    assert snapshot.recent_success is True


def test_anthropic_adapter_uses_messages_protocol(endpoint):
    from core.brain import AnthropicProvider

    server, base_url = endpoint
    profile = ModelCapabilityProfile(
        model="claude-loop", roles=frozenset({BrainRole.REASONING}), local=False,
    )
    config = ProviderConfig(
        name="anthropic", protocol="anthropic", base_url=base_url,
        api_key_ref="anthropic-key", models=(profile,), external=True,
    )
    provider = AnthropicProvider(
        config, secret_store=MemorySecretStore({"anthropic-key": "anthropic-secret"}),
        timeout=1.0,
    )

    result = provider.generate(BrainRequest("analyze", BrainRole.REASONING))

    assert result.text == "ATLAS: anthropic ok"
    assert server.last_anthropic_key == "anthropic-secret"
