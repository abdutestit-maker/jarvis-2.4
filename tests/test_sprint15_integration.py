from __future__ import annotations

from collections.abc import Iterator

import pytest

from config.settings import Settings
from core.actions import ToolRegistry
from core.brain import (
    BrainFabric,
    BrainFabricBackend,
    BrainHealthManager,
    BrainPolicy,
    BrainProvider,
    BrainProviderRegistry,
    BrainRequest,
    BrainResult,
    BrainRole,
    HealthSnapshot,
    HealthStatus,
    ModelCapabilityProfile,
    SemanticBrainRouter,
    BrainConfigStore,
    ProviderConfig,
    NoRouteAvailable,
)
from core.cognitive import CognitiveOrchestrator
from core.cognitive.models import CurrentMindState
from core.cognitive.self_model import CapabilitySelfModel
from core.model_router import ModelRouter
from core.shadow import ShadowEngine


class RecordingProvider(BrainProvider):
    def __init__(self, name: str, model: str, roles: frozenset[BrainRole], *, external: bool):
        self.name = name
        self.external = external
        self.profile = ModelCapabilityProfile(model=model, roles=roles, local=not external,
                                              streaming=True, context_window=8192)
        self.systems = []

    def health(self): return HealthSnapshot(HealthStatus.AVAILABLE)
    def models(self): return (self.profile.model,)
    def capabilities(self, model): return self.profile
    def cancel(self, request_id=None): return True
    def generate(self, request, *, model=None):
        self.systems.append(request.system)
        return BrainResult(f"{self.name}:ok", self.name, self.profile.model,
                           request.role, 1.0)
    def stream(self, request, *, model=None) -> Iterator[str]:
        self.systems.append(request.system)
        yield f"{self.name}:"
        yield "ok"


def make_fabric():
    fast = RecordingProvider("local-fast", "qwen", frozenset({
        BrainRole.CHAT, BrainRole.FAST, BrainRole.SUMMARIZER, BrainRole.FALLBACK,
    }), external=False)
    reasoning = RecordingProvider("reasoner", "reason", frozenset({
        BrainRole.REASONING, BrainRole.PLANNER, BrainRole.RESEARCH, BrainRole.CRITIC,
    }), external=False)
    coder = RecordingProvider("coder", "code", frozenset({BrainRole.CODER}), external=False)
    registry = BrainProviderRegistry()
    for provider in (fast, reasoning, coder):
        registry.register(provider)
    health = BrainHealthManager()
    router = SemanticBrainRouter(registry, health, BrainPolicy(prefer_local=True))
    fabric = BrainFabric(
        registry, router=router, health=health,
        identity_contract="Identity: ATLAS; role: personal AI operator; values: accuracy, privacy.",
    )
    return fabric, fast, reasoning, coder


def test_settings_default_brain_policy_preserves_local_behavior():
    policy = Settings().brain_policy
    assert policy.mode == "BALANCED"
    assert policy.prefer_local is True
    assert policy.allow_cloud is False
    assert policy.allow_sensitive_cloud is False


def test_model_router_returns_semantic_provider_model_without_hidden_reasoning():
    fabric, _fast, _reasoning, coder = make_fabric()
    decision = ModelRouter(Settings(), brain_fabric=fabric).route("Исправь Python код, который падает")

    assert decision.role == BrainRole.CODER.value
    assert decision.provider == "coder"
    assert decision.model == "code"
    assert decision.reason_code.startswith("ROLE_MATCH")
    assert "reasoning" not in decision.to_dict()
    assert coder.systems == []


def test_identity_contract_is_consistent_across_models_and_streaming():
    fabric, fast, reasoning, _coder = make_fabric()
    first = fabric.generate(BrainRequest("hello", BrainRole.FAST))
    second = fabric.generate(BrainRequest("analyze", BrainRole.REASONING))
    streamed = "".join(fabric.stream(BrainRequest("again", BrainRole.FAST)))

    assert first.provider == "local-fast"
    assert second.provider == "reasoner"
    assert streamed == "local-fast:ok"
    assert all("Identity: ATLAS" in system for system in fast.systems + reasoning.systems)


def test_brain_backend_bridge_preserves_existing_llm_contract():
    fabric, _fast, _reasoning, _coder = make_fabric()
    request = BrainRequest("hello", BrainRole.CHAT)
    route = fabric.select_route(request)
    backend = BrainFabricBackend(fabric, route, template=request)

    assert backend.chat([{"role": "user", "content": "hello"}], system="persona") == "local-fast:ok"
    assert "".join(backend.streaming([{"role": "user", "content": "hello"}], system="persona")) == "local-fast:ok"
    assert backend.model == "qwen"
    assert backend.is_available() is True


def test_cognitive_core_owns_brain_fabric_and_self_model_reports_fact(tmp_path):
    fabric, _fast, _reasoning, _coder = make_fabric()
    cognitive = CognitiveOrchestrator(
        tmp_path / "cognitive", registry=ToolRegistry(), brain_fabric=fabric,
    )
    route = cognitive.select_brain(BrainRequest("analyze", BrainRole.REASONING))
    assert route.primary.provider == "reasoner"

    self_model = CapabilitySelfModel(ToolRegistry(), brain_fabric=fabric)
    answer = self_model.answer("Какой мозг сейчас работает?", CurrentMindState())
    assert answer.known is True
    assert "локаль" in answer.text.casefold()
    assert "reasoner:reason" in answer.evidence


def test_shadow_background_brain_obeys_local_cost_privacy_policy(tmp_path):
    fabric, _fast, _reasoning, coder = make_fabric()
    shadow = ShadowEngine(data_dir=tmp_path, registry=ToolRegistry(), enabled=False,
                          brain_fabric=fabric)

    route = shadow.select_background_brain(BrainRole.CODER)

    assert route.primary.provider == "coder"
    assert route.primary.local is True
    assert coder.systems == []


def test_provider_hot_reload_keeps_bound_step_then_removes_for_new_routes(tmp_path):
    fabric, _fast, _reasoning, _coder = make_fabric()
    store = BrainConfigStore(tmp_path / "providers.json")

    def factory(config):
        roles = config.models[0].roles
        provider = RecordingProvider(
            config.name, config.models[0].model, roles, external=config.external,
        )
        provider.profile = config.models[0]
        return provider

    fabric.attach_config(store, factory)
    vision_profile = ModelCapabilityProfile(
        model="vision-model", roles=frozenset({BrainRole.VISION}), local=True, vision=True,
    )
    store.save((ProviderConfig(
        name="vision", protocol="openai_compatible", base_url="http://127.0.0.1:1/v1",
        models=(vision_profile,), external=False,
    ),))
    assert fabric.reload_provider_config() == ("vision",)
    bound_request = BrainRequest(
        "inspect", BrainRole.VISION, mission_id="mission", stage="reference",
        required_capabilities=frozenset({"vision"}),
    )
    bound = fabric.select_route(bound_request)

    store.save(())
    assert fabric.reload_provider_config() == ()
    assert fabric.generate(bound_request, route=bound).provider == "vision"
    with pytest.raises(NoRouteAvailable):
        fabric.select_route(BrainRequest(
            "inspect", BrainRole.VISION, mission_id="new", stage="reference",
            required_capabilities=frozenset({"vision"}),
        ))


def test_provider_uncertainty_does_not_become_truth_confidence(tmp_path):
    fabric, _fast, _reasoning, _coder = make_fabric()
    cognitive = CognitiveOrchestrator(tmp_path, registry=ToolRegistry(), brain_fabric=fabric)
    original_truth_confidence = cognitive.state.confidence

    cognitive.record_brain_signal(
        provider="reasoner", model="reason", status="degraded",
        latency_ms=900.0, model_confidence=0.99,
    )

    assert cognitive.state.confidence == original_truth_confidence
    assert any("reasoner:reason" in item for item in cognitive.state.uncertainties)
