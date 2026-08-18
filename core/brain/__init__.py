"""Provider-independent model orchestration for ATLAS."""
from .config import BrainConfigStore, BrainProviderConfigurator
from .benchmark import AutoRoleSuggester, BenchmarkReport, BrainBenchmark
from .bootstrap import build_brain_fabric, provider_from_config
from .context import ComposedContext, ContextBudgetError, ContextComposer
from .critic import Critic
from .health import BrainHealthManager
from .local_models import GGUFModelInfo, LocalModelLifecycle, LocalModelManager
from .models import *
from .provider import BrainProvider
from .providers import (
    AnthropicProvider, BackendProviderAdapter, LocalGGUFProvider,
    OpenAICompatibleProvider, OpenAIProvider, OpenRouterProvider,
)
from .registry import BrainProviderRegistry, ProviderEntry
from .routing import SemanticBrainRouter
from .fabric import BrainFabric, BrainFabricBackend
from .secrets import (
    CompositeSecretStore, DPAPISecretStore, EnvironmentSecretStore,
    MemorySecretStore, SecretStore,
)
from .structured import StructuredOutputError, StructuredOutputValidator

__all__ = [name for name in globals() if not name.startswith("_")]
