"""Semantic role, capability, privacy, latency and cost routing."""
from __future__ import annotations

from .health import BrainHealthManager
from .models import (
    BrainPolicy, BrainPolicyMode, BrainRequest, BrainRoute, HealthStatus,
    NoRouteAvailable, PrivacyClass, RouteCandidate,
)
from .registry import BrainProviderRegistry


class SemanticBrainRouter:
    def __init__(self, registry: BrainProviderRegistry, health: BrainHealthManager,
                 policy: BrainPolicy | None = None) -> None:
        self.registry = registry
        self.health = health
        self.policy = policy or BrainPolicy()

    def update_policy(self, policy: BrainPolicy) -> None:
        self.policy = policy

    def route(self, request: BrainRequest) -> BrainRoute:
        candidates: list[RouteCandidate] = []
        policy = self.policy
        for entry in self.registry.providers():
            provider = entry.provider
            if not self._provider_allowed(provider.external, request):
                continue
            try:
                model_names = provider.models()
            except Exception:
                continue
            for model_name in model_names:
                key = f"{provider.name}:{model_name}"
                if not self.health.allow(key):
                    continue
                try:
                    profile = provider.capabilities(model_name)
                except (KeyError, ValueError, TypeError):
                    continue
                if request.context_tokens > profile.context_window:
                    continue
                if profile.cost_tier > policy.max_cost_tier:
                    continue
                if not profile.supports(request.role, request.required_capabilities):
                    continue
                snapshot = self.health.snapshot(key)
                score = 100.0 + float(entry.priority)
                if profile.local:
                    score += 20.0 if policy.prefer_local else 0.0
                elif policy.mode is BrainPolicyMode.QUALITY:
                    score += 8.0
                if policy.mode is BrainPolicyMode.SPEED:
                    score -= float(snapshot.latency_ms or 0.0) / 100.0
                score -= profile.cost_tier * (8.0 if policy.mode is not BrainPolicyMode.QUALITY else 2.0)
                if snapshot.status is HealthStatus.DEGRADED:
                    score -= 30.0
                candidates.append(RouteCandidate(
                    provider=provider.name, model=model_name, role=request.role,
                    local=profile.local, score=round(score, 4),
                ))
        if not candidates:
            raise NoRouteAvailable(
                f"no healthy provider satisfies role={request.role.value}, privacy={request.privacy.value}"
            )
        candidates.sort(key=lambda item: item.score, reverse=True)
        primary = candidates[0]
        fallbacks = tuple(candidates[1:1 + max(0, policy.max_fallbacks)])
        if primary.local:
            reason = "ROLE_MATCH_LOCAL_FIRST" if policy.prefer_local else "ROLE_MATCH_LOCAL_AVAILABLE"
        else:
            reason = "ROLE_MATCH_CLOUD_ALLOWED"
        if request.privacy is PrivacyClass.LOCAL_ONLY or policy.mode is BrainPolicyMode.LOCAL_ONLY:
            reason = "PRIVACY_LOCAL_ONLY"
        return BrainRoute(primary, fallbacks, reason, self.registry.generation)

    def _provider_allowed(self, external: bool, request: BrainRequest) -> bool:
        policy = self.policy
        if not external:
            return True
        if policy.mode is BrainPolicyMode.LOCAL_ONLY or request.privacy is PrivacyClass.LOCAL_ONLY:
            return False
        if not policy.allow_cloud:
            return False
        if request.privacy is PrivacyClass.SENSITIVE and not policy.allow_sensitive_cloud:
            return False
        if request.background and not policy.background_allow_cloud:
            return False
        return True


__all__ = ["SemanticBrainRouter"]

