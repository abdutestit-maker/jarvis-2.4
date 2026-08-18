from __future__ import annotations

import time
from collections.abc import Iterator

import pytest

from core.brain import (
    BrainFabric,
    BrainHealthManager,
    BrainPolicy,
    BrainPolicyMode,
    BrainProvider,
    BrainProviderRegistry,
    BrainRequest,
    BrainResult,
    BrainRole,
    HealthSnapshot,
    HealthStatus,
    ModelCapabilityProfile,
    NoRouteAvailable,
    PrivacyClass,
    ProviderUnavailable,
    SemanticBrainRouter,
)


class FakeProvider(BrainProvider):
    def __init__(self, name: str, profiles: tuple[ModelCapabilityProfile, ...], *,
                 external: bool, text: str | None = None, delay: float = 0.0) -> None:
        self.name = name
        self.external = external
        self.profiles = {profile.model: profile for profile in profiles}
        self.text = text
        self.delay = delay
        self.calls = 0
        self.cancelled = False

    def health(self):
        return HealthSnapshot(HealthStatus.AVAILABLE)

    def models(self):
        return tuple(self.profiles)

    def generate(self, request, *, model=None):
        self.calls += 1
        if self.delay:
            time.sleep(self.delay)
        if self.text is None:
            raise ProviderUnavailable(f"{self.name} down")
        selected = model or next(iter(self.profiles))
        return BrainResult(self.text, self.name, selected, request.role, self.delay * 1000)

    def stream(self, request, *, model=None) -> Iterator[str]:
        yield self.generate(request, model=model).text

    def cancel(self, request_id=None):
        self.cancelled = True
        return True

    def capabilities(self, model):
        return self.profiles[model]


def profile(model: str, *roles: BrainRole, local: bool, context: int = 4096,
            tools: bool = False, vision: bool = False, cost: int = 0):
    return ModelCapabilityProfile(
        model=model, roles=frozenset(roles), local=local, context_window=context,
        tool_calling=tools, vision=vision, cost_tier=cost,
    )


def make_router(*providers: FakeProvider, policy: BrainPolicy | None = None):
    registry = BrainProviderRegistry()
    for provider in providers:
        registry.register(provider)
    health = BrainHealthManager(failure_threshold=1, cooldown_seconds=60)
    return registry, health, SemanticBrainRouter(registry, health, policy or BrainPolicy())


def test_semantic_roles_select_fast_reasoning_and_coder():
    local = FakeProvider("local", (
        profile("fast", BrainRole.FAST, BrainRole.CHAT, local=True),
        profile("reason", BrainRole.REASONING, local=True),
    ), external=False, text="local")
    cloud = FakeProvider("cloud", (
        profile("coder", BrainRole.CODER, local=False, tools=True, cost=1),
    ), external=True, text="cloud")
    policy = BrainPolicy(allow_cloud=True, prefer_local=True)
    _registry, _health, router = make_router(local, cloud, policy=policy)

    assert router.route(BrainRequest("привет", BrainRole.FAST)).primary.model == "fast"
    assert router.route(BrainRequest("объясни", BrainRole.REASONING)).primary.model == "reason"
    coding = router.route(BrainRequest(
        "исправь код", BrainRole.CODER, required_capabilities=frozenset({"tool_calling"}),
    ))
    assert (coding.primary.provider, coding.primary.model) == ("cloud", "coder")
    assert coding.reason_code == "ROLE_MATCH_CLOUD_ALLOWED"


def test_local_only_and_sensitive_privacy_filter_cloud():
    local = FakeProvider("local", (profile("fast", BrainRole.CHAT, local=True),),
                         external=False, text="local")
    cloud = FakeProvider("cloud", (profile("best", BrainRole.CHAT, local=False),),
                         external=True, text="cloud")
    policy = BrainPolicy(allow_cloud=True, allow_sensitive_cloud=False, prefer_local=False)
    _registry, _health, router = make_router(local, cloud, policy=policy)

    assert router.route(BrainRequest("private", privacy=PrivacyClass.LOCAL_ONLY)).primary.provider == "local"
    assert router.route(BrainRequest("secret", privacy=PrivacyClass.SENSITIVE)).primary.provider == "local"
    with pytest.raises(NoRouteAvailable):
        router.route(BrainRequest(
            "vision", role=BrainRole.VISION, privacy=PrivacyClass.LOCAL_ONLY,
            required_capabilities=frozenset({"vision"}),
        ))


def test_context_window_health_and_background_policy_are_hard_filters():
    small = FakeProvider("small", (profile("small", BrainRole.RESEARCH, local=True, context=1024),),
                         external=False, text="small")
    large = FakeProvider("large", (profile("large", BrainRole.RESEARCH, local=True, context=8192),),
                         external=False, text="large")
    cloud = FakeProvider("cloud", (profile("cloud", BrainRole.RESEARCH, local=False, context=65536),),
                         external=True, text="cloud")
    registry, health, router = make_router(
        small, large, cloud,
        policy=BrainPolicy(allow_cloud=True, background_allow_cloud=False),
    )
    health.record_failure("large:large", error="down")

    with pytest.raises(NoRouteAvailable):
        router.route(BrainRequest(
            "background research", BrainRole.RESEARCH, context_tokens=5000, background=True,
        ))
    health.force_retry("large:large")
    route = router.route(BrainRequest(
        "background research", BrainRole.RESEARCH, context_tokens=5000, background=True,
    ))
    assert route.primary.provider == "large"
    assert all(item.provider != "cloud" for item in route.fallback_chain)


def test_fabric_fails_over_quickly_and_circuit_skips_primary():
    primary = FakeProvider("primary", (profile("reason-a", BrainRole.REASONING, local=True),),
                           external=False, text=None)
    fallback = FakeProvider("fallback", (profile("reason-b", BrainRole.REASONING, local=True),),
                            external=False, text="verified fallback")
    registry, health, router = make_router(primary, fallback)
    fabric = BrainFabric(registry, router=router, health=health)

    started = time.perf_counter()
    result = fabric.generate(BrainRequest("reason", BrainRole.REASONING, mission_id="m1", stage="plan"))
    elapsed = time.perf_counter() - started

    assert result.text == "verified fallback"
    assert result.provider == "fallback"
    assert primary.calls == 1 and fallback.calls == 1
    assert elapsed < 0.5
    assert health.allow("primary:reason-a") is False

    second = fabric.generate(BrainRequest("again", BrainRole.REASONING, mission_id="m2", stage="plan"))
    assert second.provider == "fallback"
    assert primary.calls == 1


def test_mission_stage_binding_survives_better_provider_registration():
    first = FakeProvider("first", (profile("chat-a", BrainRole.CHAT, local=True),),
                         external=False, text="first")
    registry, health, router = make_router(first)
    fabric = BrainFabric(registry, router=router, health=health)
    request = BrainRequest("hello", BrainRole.CHAT, mission_id="bound", stage="answer")
    original = fabric.select_route(request)

    better = FakeProvider("better", (profile("chat-b", BrainRole.CHAT, local=True),),
                          external=False, text="better")
    registry.register(better, priority=100)

    assert fabric.select_route(request) == original
    assert fabric.select_route(BrainRequest(
        "hello", BrainRole.CHAT, mission_id="new", stage="answer",
    )).primary.provider == "better"


def test_local_only_policy_mode_blocks_external_even_for_public_data():
    cloud = FakeProvider("cloud", (profile("chat", BrainRole.CHAT, local=False),),
                         external=True, text="cloud")
    _registry, _health, router = make_router(
        cloud, policy=BrainPolicy(mode=BrainPolicyMode.LOCAL_ONLY, allow_cloud=True),
    )
    with pytest.raises(NoRouteAvailable):
        router.route(BrainRequest("public", privacy=PrivacyClass.PUBLIC))

