"""Sprint 15 safe live demo using real loopback OpenAI-compatible HTTP endpoints."""
from __future__ import annotations

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.brain import (  # noqa: E402
    BrainBenchmark, BrainConfigStore, BrainFabric, BrainHealthManager,
    BrainPolicy, BrainProviderConfigurator, BrainProviderRegistry, BrainRequest,
    BrainRole, MemorySecretStore, ModelCapabilityProfile, NoRouteAvailable,
    OpenAICompatibleProvider, OpenAIProvider, PrivacyClass, ProviderConfig,
    SemanticBrainRouter, provider_from_config,
)
from core.security.atomic import atomic_json_write  # noqa: E402


class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self.server.request_count += 1  # type: ignore[attr-defined]
        if self.path == "/v1/models":
            self._send(200, {"data": [{"id": item} for item in self.server.models]})  # type: ignore[attr-defined]
        else:
            self._send(404, {"error": "not_found"})

    def do_POST(self):  # noqa: N802
        self.server.request_count += 1  # type: ignore[attr-defined]
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        if self.path != "/v1/chat/completions" or payload.get("model") not in self.server.models:  # type: ignore[attr-defined]
            self._send(404, {"error": "model_not_found"})
            return
        messages = payload.get("messages", [])
        systems = [str(item.get("content", "")) for item in messages if item.get("role") == "system"]
        self.server.system_contracts.extend(systems)  # type: ignore[attr-defined]
        model = payload["model"]
        text = f"ATLAS/{self.server.label}/{model}: verified response"  # type: ignore[attr-defined]
        self._send(200, {
            "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 8, "completion_tokens": 4},
        })

    def _send(self, status: int, value: dict[str, Any]) -> None:
        body = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args) -> None:
        return


class Endpoint:
    def __init__(self, label: str, models: tuple[str, ...]) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), DemoHandler)
        self.server.label = label
        self.server.models = models
        self.server.request_count = 0
        self.server.system_contracts = []
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}/v1"

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def profile(model: str, *roles: BrainRole, local: bool = True) -> ModelCapabilityProfile:
    return ModelCapabilityProfile(
        model=model, roles=frozenset(roles), local=local, streaming=False,
        structured_output=True, tool_calling=BrainRole.CODER in roles,
        context_window=8192, tested=frozenset({"chat", "structured_output"}),
    )


def timed_generate(fabric: BrainFabric, request: BrainRequest, *, route=None):
    started = time.perf_counter()
    result = fabric.generate(request, route=route)
    return result, round((time.perf_counter() - started) * 1000, 3)


def main() -> int:
    artifact_dir = ROOT / "artifacts" / "sprint15" / "live"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    config_path = artifact_dir / "providers.json"
    if config_path.exists():
        config_path.unlink()

    primary_endpoint = Endpoint("primary", ("fast-a", "reason-a", "coder-a"))
    fallback_endpoint = Endpoint("fallback", ("fast-b", "reason-b", "coder-b", "custom-b"))
    external_endpoint = Endpoint("external", ("external-chat",))
    for endpoint in (primary_endpoint, fallback_endpoint, external_endpoint):
        endpoint.start()

    secrets = MemorySecretStore()
    primary = OpenAICompatibleProvider(ProviderConfig(
        name="primary", protocol="openai_compatible", base_url=primary_endpoint.url,
        external=False, timeout_seconds=0.35,
        models=(
            profile("fast-a", BrainRole.FAST, BrainRole.CHAT),
            profile("reason-a", BrainRole.REASONING, BrainRole.PLANNER, BrainRole.RESEARCH),
            profile("coder-a", BrainRole.CODER),
        ),
    ), secret_store=secrets, timeout=0.35)
    fallback = OpenAICompatibleProvider(ProviderConfig(
        name="fallback", protocol="openai_compatible", base_url=fallback_endpoint.url,
        external=False, timeout_seconds=0.35,
        models=(
            profile("fast-b", BrainRole.FAST, BrainRole.CHAT),
            profile("reason-b", BrainRole.REASONING, BrainRole.PLANNER, BrainRole.RESEARCH),
            profile("coder-b", BrainRole.CODER),
        ),
    ), secret_store=secrets, timeout=0.35)
    external = OpenAIProvider(ProviderConfig(
        name="external", protocol="openai", base_url=external_endpoint.url,
        external=True, timeout_seconds=0.35,
        models=(profile("external-chat", BrainRole.CHAT, local=False),),
    ), secret_store=secrets, timeout=0.35)

    registry = BrainProviderRegistry()
    registry.register(primary, priority=50)
    registry.register(fallback, priority=10)
    registry.register(external, priority=-50)
    health = BrainHealthManager(failure_threshold=1, cooldown_seconds=60)
    policy = BrainPolicy(allow_cloud=True, prefer_local=True, max_fallbacks=2)
    router = SemanticBrainRouter(registry, health, policy)
    identity = "Identity: ATLAS; role: personal AI operator; values: accuracy, privacy, initiative, reliability."
    fabric = BrainFabric(registry, router=router, health=health, identity_contract=identity)

    report: dict[str, Any] = {"success": False, "routes": {}, "latency_ms": {}}
    try:
        for label, role, prompt in (
            ("simple_chat", BrainRole.FAST, "Атлас, привет."),
            ("reasoning", BrainRole.REASONING, "Сравни два проверенных варианта."),
            ("coding", BrainRole.CODER, "Исправь функцию."),
        ):
            request = BrainRequest(prompt, role, mission_id=label, stage="answer")
            result, latency = timed_generate(fabric, request)
            report["routes"][label] = {"provider": result.provider, "model": result.model,
                                               "role": result.role.value, "text": result.text}
            report["latency_ms"][label] = latency

        fail_request = BrainRequest(
            "Составь проверяемый план.", BrainRole.REASONING,
            mission_id="failover", stage="plan",
        )
        bound_route = fabric.select_route(fail_request)
        primary_endpoint.stop()
        fail_result, fail_latency = timed_generate(fabric, fail_request, route=bound_route)
        report["failover"] = {
            "selected_primary": bound_route.primary.provider,
            "result_provider": fail_result.provider,
            "result_text": fail_result.text,
            "latency_ms": fail_latency,
            "primary_health": health.snapshot("primary:reason-a").status.value,
        }

        before_external = external_endpoint.server.request_count
        local_result, local_latency = timed_generate(fabric, BrainRequest(
            "Локальная персональная задача", BrainRole.CHAT,
            privacy=PrivacyClass.LOCAL_ONLY, mission_id="privacy", stage="answer",
        ))
        after_external = external_endpoint.server.request_count
        report["local_only"] = {
            "provider": local_result.provider,
            "external_http_delta": after_external - before_external,
            "latency_ms": local_latency,
        }

        store = BrainConfigStore(config_path)
        configurator = BrainProviderConfigurator(store, secrets)
        fabric.attach_config(store, lambda cfg: provider_from_config(cfg, secret_store=secrets))
        configurator.upsert_openai_compatible(
            name="custom_loopback", base_url=fallback_endpoint.url, api_key="",
            model="custom-b", roles=(BrainRole.SUMMARIZER,), external=False,
            structured_output=True,
        )
        added = fabric.reload_provider_config()
        custom_result, custom_latency = timed_generate(fabric, BrainRequest(
            "Суммируй", BrainRole.SUMMARIZER, mission_id="custom", stage="summary",
        ))
        configurator.remove("custom_loopback")
        removed = fabric.reload_provider_config()
        no_route_after_remove = False
        try:
            fabric.select_route(BrainRequest(
                "Суммируй", BrainRole.SUMMARIZER, mission_id="custom-new", stage="summary",
            ))
        except NoRouteAvailable:
            no_route_after_remove = True
        continuation, continuation_latency = timed_generate(fabric, BrainRequest(
            "Продолжи анализ", BrainRole.REASONING, mission_id="continuation", stage="plan",
        ))
        report["custom_provider"] = {
            "added": list(added), "result_provider": custom_result.provider,
            "latency_ms": custom_latency, "after_remove": list(removed),
            "new_route_absent": no_route_after_remove,
            "runtime_continued_with": continuation.provider,
            "continuation_latency_ms": continuation_latency,
        }

        benchmark = BrainBenchmark().run_stream(
            fallback, "fast-b", BrainRequest("Короткий тест", BrainRole.FAST),
            schema_check=lambda text: text.startswith("ATLAS/"),
        )
        report["benchmark"] = benchmark.to_dict()
        systems = (primary_endpoint.server.system_contracts
                   + fallback_endpoint.server.system_contracts
                   + external_endpoint.server.system_contracts)
        report["identity"] = {
            "contract": identity,
            "requests_checked": len(systems),
            "consistent": bool(systems) and all("Identity: ATLAS" in item for item in systems),
        }
        report["success"] = all((
            report["routes"]["simple_chat"]["provider"] == "primary",
            report["routes"]["reasoning"]["provider"] == "primary",
            report["routes"]["coding"]["provider"] == "primary",
            report["failover"]["result_provider"] == "fallback",
            report["local_only"]["external_http_delta"] == 0,
            report["custom_provider"]["result_provider"] == "custom_loopback",
            report["custom_provider"]["new_route_absent"],
            report["identity"]["consistent"],
            report["benchmark"]["success"],
        ))
    finally:
        for endpoint in (fallback_endpoint, external_endpoint):
            endpoint.stop()
        fabric.close()

    output = artifact_dir / "live_demo_report.json"
    atomic_json_write(output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"REPORT={output}")
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

