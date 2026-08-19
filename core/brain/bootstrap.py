"""Build one BrainFabric from current Settings without loading model weights."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import BrainConfigStore
from .fabric import BrainFabric
from .health import BrainHealthManager
from .models import (
    BrainPolicy, BrainPolicyMode, BrainRole, ModelCapabilityProfile, ProviderConfig,
)
from .providers import (
    AnthropicProvider, BackendProviderAdapter, LocalGGUFProvider,
    OpenAICompatibleProvider, OpenAIProvider, OpenRouterProvider,
)
from .registry import BrainProviderRegistry
from .routing import SemanticBrainRouter
from .secrets import (
    CompositeSecretStore, DPAPISecretStore, EnvironmentSecretStore,
    MemorySecretStore, SecretStore,
)


def provider_from_config(config: ProviderConfig, *, secret_store: SecretStore):
    protocol = config.protocol.casefold()
    if protocol in {"openai", "openai_api"}:
        return OpenAIProvider(config, secret_store=secret_store)
    if protocol == "openrouter":
        return OpenRouterProvider(config, secret_store=secret_store)
    if protocol in {"anthropic", "anthropic_messages"}:
        return AnthropicProvider(config, secret_store=secret_store)
    if protocol in {"openai_compatible", "custom"}:
        return OpenAICompatibleProvider(config, secret_store=secret_store)
    raise ValueError(f"unsupported provider protocol: {config.protocol}")


def _policy(settings: Any) -> BrainPolicy:
    value = settings.brain_policy
    return BrainPolicy(
        mode=BrainPolicyMode(str(value.mode).upper()),
        prefer_local=bool(value.prefer_local), allow_cloud=bool(value.allow_cloud),
        allow_sensitive_cloud=bool(value.allow_sensitive_cloud),
        max_fallbacks=int(value.max_fallbacks),
        failure_timeout_seconds=float(value.failure_timeout_seconds),
        background_allow_cloud=bool(value.background_allow_cloud),
        max_cost_tier=int(value.max_cost_tier),
    )


def _identity_contract() -> str:
    try:
        from core.personality import PersonalityEngine
        identity = PersonalityEngine().identity
        values = ", ".join(identity.values)
        return f"Identity: {identity.name}; role: {identity.role}; mission: {identity.mission}; values: {values}."
    except Exception:
        return "Identity: ATLAS; role: personal AI operator; values: accuracy, privacy, initiative, reliability."


def build_brain_fabric(settings: Any, *, secret_store: SecretStore | None = None) -> BrainFabric:
    registry = BrainProviderRegistry()
    health = BrainHealthManager(failure_threshold=2, cooldown_seconds=10.0)
    policy = _policy(settings)
    secret_path = Path(settings.data_dir) / "brain" / "provider-secrets.dpapi"
    secrets = secret_store or CompositeSecretStore(
        EnvironmentSecretStore(), DPAPISecretStore(secret_path), MemorySecretStore(),
    )

    # One physical local backend serves semantic roles. Construction is lazy:
    # LocalQwenBackend does not load GGUF weights until generation/warm-up.
    # Resolve it through the public FAST factory instead of bypassing that
    # boundary with get_offline_backend().  This keeps Brain Fabric and the
    # legacy router on one cache key, and lets injected/local test backends use
    # the same path as production.
    try:
        from core.llm import Tier, get_llm_backend
        local_backend = get_llm_backend(settings, Tier.FAST)
        local_profile = ModelCapabilityProfile(
            model=str(local_backend.model),
            roles=frozenset({
                BrainRole.CHAT, BrainRole.FAST, BrainRole.REASONING, BrainRole.CODER,
                BrainRole.PLANNER, BrainRole.RESEARCH, BrainRole.CRITIC,
                BrainRole.SUMMARIZER, BrainRole.FALLBACK,
            }),
            streaming=True, structured_output=False,
            tool_calling=bool(getattr(local_backend, "supports_tools", False)),
            vision=False, context_window=int(settings.local_model.n_ctx),
            local=True, cost_tier=0, tested=frozenset({"chat", "streaming"}),
            metadata={"source": "existing_local_runtime"},
        )
        registry.register(LocalGGUFProvider("local", local_backend, (local_profile,)), priority=20)
    except Exception:
        pass

    # Existing remote tiers remain usable through their proven backend code.
    if policy.allow_cloud:
        try:
            from core.llm import Tier, get_llm_backend
            role_map = {
                Tier.FAST: frozenset({BrainRole.CHAT, BrainRole.FAST, BrainRole.SUMMARIZER}),
                Tier.ANALYST: frozenset({BrainRole.REASONING, BrainRole.RESEARCH, BrainRole.CRITIC}),
                Tier.CODER: frozenset({BrainRole.CODER}),
                Tier.ARCHITECT: frozenset({BrainRole.PLANNER, BrainRole.REASONING, BrainRole.CRITIC}),
            }
            for tier, roles in role_map.items():
                if settings.get_provider(tier) == "local" or not settings.is_tier_available(tier):
                    continue
                backend = get_llm_backend(settings, tier)
                provider_name = f"{settings.get_provider(tier)}:{tier.value}"
                profile = ModelCapabilityProfile(
                    model=str(backend.model), roles=roles,
                    streaming=True, structured_output=False,
                    tool_calling=bool(getattr(backend, "supports_tools", False)),
                    vision=False, context_window=32768, local=False, cost_tier=2,
                    metadata={"source": "existing_tier", "tier": tier.value},
                )
                registry.register(BackendProviderAdapter(
                    provider_name, backend, (profile,), external=True,
                ))
        except Exception:
            pass

    router = SemanticBrainRouter(registry, health, policy)
    fabric = BrainFabric(
        registry, router=router, health=health, identity_contract=_identity_contract(),
    )
    fabric.secret_store = secrets
    configured_path = getattr(settings.brain_policy, "resolved_providers_path", None)
    path = configured_path or (Path(settings.data_dir) / "brain" / "providers.json")
    store = BrainConfigStore(path)
    fabric.attach_config(store, lambda config: provider_from_config(config, secret_store=secrets))
    fabric.reload_provider_config()
    return fabric


__all__ = ["build_brain_fabric", "provider_from_config"]
