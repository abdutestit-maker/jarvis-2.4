"""LLM-слой Джарвиса: единый интерфейс к локальной и удалённым моделям.

Публичный контракт для остальных частей проекта::

    from core.llm import (
        LLMBackend, BackendUnavailable, BackendConfigError,
        Tier, resolve_tier, get_llm_backend, get_embedding_backend,
    )
"""

from __future__ import annotations

from core.llm import breaker
from core.llm.backend import (
    BackendConfigError,
    BackendUnavailable,
    LLMBackend,
    LLMError,
    ToolsNotSupportedError,
    messages_to_prompt,
    normalize_messages,
    prepend_system,
    strip_reasoning_blocks,
)
from core.llm.tool_calls import ToolCall, ToolCallResponse, parse_tool_calls
from core.llm.factory import (
    available_backends,
    clear_backend_cache,
    get_embedding_backend,
    get_llm_backend,
    get_offline_backend,
    warm_up_backends,
)
from core.llm.local_qwen import LocalQwenBackend
from core.llm.remote_api import RemoteAPIBackend, RetryableHTTPError
from core.llm.tiers import (
    ESCALATION_ORDER,
    Tier,
    next_tier,
    resolve_tier,
    tier_purpose,
    tier_to_backend_key,
)

__all__ = [
    # исключения
    "LLMError",
    "BackendUnavailable",
    "BackendConfigError",
    "ToolsNotSupportedError",
    "RetryableHTTPError",
    # интерфейс и реализации
    "LLMBackend",
    "LocalQwenBackend",
    "RemoteAPIBackend",
    # тиры
    "Tier",
    "ESCALATION_ORDER",
    "resolve_tier",
    "tier_to_backend_key",
    "next_tier",
    "tier_purpose",
    # фабрика
    "get_llm_backend",
    "get_offline_backend",
    "get_embedding_backend",
    "available_backends",
    "warm_up_backends",
    "clear_backend_cache",
    # circuit breaker (Sprint 3)
    "breaker",
    # утилиты формата сообщений
    "normalize_messages",
    "prepend_system",
    "messages_to_prompt",
    "strip_reasoning_blocks",
    "ToolCall",
    "ToolCallResponse",
    "parse_tool_calls",
]
