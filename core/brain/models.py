"""Typed, reasoning-free contracts for replaceable cognitive engines."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class BrainRole(str, Enum):
    CHAT = "CHAT"
    FAST = "FAST"
    REASONING = "REASONING"
    CODER = "CODER"
    PLANNER = "PLANNER"
    RESEARCH = "RESEARCH"
    VISION = "VISION"
    CRITIC = "CRITIC"
    SUMMARIZER = "SUMMARIZER"
    FALLBACK = "FALLBACK"


class PrivacyClass(str, Enum):
    PUBLIC = "PUBLIC"
    PERSONAL = "PERSONAL"
    SENSITIVE = "SENSITIVE"
    LOCAL_ONLY = "LOCAL_ONLY"


class BrainPolicyMode(str, Enum):
    LOCAL_ONLY = "LOCAL_ONLY"
    BALANCED = "BALANCED"
    QUALITY = "QUALITY"
    SPEED = "SPEED"
    CUSTOM = "CUSTOM"


class HealthStatus(str, Enum):
    AVAILABLE = "available"
    LOADING = "loading"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    UNHEALTHY = "unhealthy"


class CriticVerdict(str, Enum):
    APPROVE = "APPROVE"
    REVISE = "REVISE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class ModelCapabilityProfile:
    model: str
    roles: frozenset[BrainRole]
    streaming: bool = False
    structured_output: bool = False
    tool_calling: bool = False
    vision: bool = False
    context_window: int = 4096
    local: bool = False
    cost_tier: int = 0
    tested: frozenset[str] = frozenset()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def supports(self, role: BrainRole, required: frozenset[str] = frozenset()) -> bool:
        if role not in self.roles:
            return False
        flags = {
            "streaming": self.streaming,
            "structured_output": self.structured_output,
            "tool_calling": self.tool_calling,
            "vision": self.vision,
        }
        return all(bool(flags.get(item, False)) for item in required)

    def public_dict(self) -> dict[str, Any]:
        from core.security.redaction import redact
        return {
            "model": self.model,
            "roles": sorted(role.value for role in self.roles),
            "streaming": self.streaming,
            "structured_output": self.structured_output,
            "tool_calling": self.tool_calling,
            "vision": self.vision,
            "context_window": self.context_window,
            "local": self.local,
            "cost_tier": self.cost_tier,
            "tested": sorted(self.tested),
            "metadata": redact(dict(self.metadata)),
        }


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    protocol: str
    base_url: str = ""
    api_key_ref: str = ""
    models: tuple[ModelCapabilityProfile, ...] = ()
    external: bool = True
    enabled: bool = True
    timeout_seconds: float = 7.0
    headers: Mapping[str, str] = field(default_factory=dict)

    def public_dict(self) -> dict[str, Any]:
        from core.security.redaction import redact
        return {
            "name": self.name,
            "protocol": self.protocol,
            "base_url": self.base_url,
            "api_key_ref": self.api_key_ref,
            "models": [model.public_dict() for model in self.models],
            "external": self.external,
            "enabled": self.enabled,
            "timeout_seconds": self.timeout_seconds,
            "headers": redact(dict(self.headers)),
        }


@dataclass(frozen=True)
class BrainPolicy:
    mode: BrainPolicyMode = BrainPolicyMode.BALANCED
    prefer_local: bool = True
    allow_cloud: bool = False
    allow_sensitive_cloud: bool = False
    max_fallbacks: int = 2
    failure_timeout_seconds: float = 3.0
    background_allow_cloud: bool = False
    max_cost_tier: int = 3


@dataclass(frozen=True)
class BrainRequest:
    user_request: str
    role: BrainRole = BrainRole.CHAT
    messages: tuple[Mapping[str, Any], ...] = ()
    system: str = ""
    required_capabilities: frozenset[str] = frozenset()
    privacy: PrivacyClass = PrivacyClass.PERSONAL
    context_tokens: int = 0
    latency_requirement_ms: int | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    mission_id: str = ""
    stage: str = ""
    background: bool = False


@dataclass(frozen=True)
class RouteCandidate:
    provider: str
    model: str
    role: BrainRole
    local: bool
    score: float


@dataclass(frozen=True)
class BrainRoute:
    primary: RouteCandidate
    fallback_chain: tuple[RouteCandidate, ...] = ()
    reason_code: str = "ROLE_MATCH"
    policy_generation: int = 0


@dataclass(frozen=True)
class BrainResult:
    text: str
    provider: str
    model: str
    role: BrainRole
    latency_ms: float
    finish_reason: str = "stop"
    usage: Mapping[str, Any] = field(default_factory=dict)
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class HealthSnapshot:
    status: HealthStatus
    latency_ms: float | None = None
    failures: int = 0
    timeouts: int = 0
    recent_success: bool = False
    last_error: str = ""


@dataclass(frozen=True)
class CriticResult:
    verdict: CriticVerdict
    issues: tuple[str, ...] = ()
    required_evidence: tuple[str, ...] = ()


class BrainError(RuntimeError):
    pass


class ProviderUnavailable(BrainError):
    pass


class ProviderResponseError(BrainError):
    pass


class NoRouteAvailable(BrainError):
    pass


__all__ = [name for name in globals() if not name.startswith("_")]
