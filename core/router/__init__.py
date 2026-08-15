"""Совет мудрецов — публичный контракт маршрутизации.

Импорт из других частей проекта::

    from core.router import (
        CouncilRouter,
        LocalFace,
        resolve_keyword_tool,
        resolve_next_available_tier,
    )
"""

from __future__ import annotations

from core.router.council import CouncilRouter
from core.router.intent_router import (
    INTENT_APP,
    INTENT_BROWSER,
    INTENT_FILE,
    INTENT_MEDIA,
    INTENT_NONE,
    INTENT_SYSTEM,
    INTENT_WEB,
    resolve_keyword_tool,
)
from core.router.local_face import ClassifyDecision, LocalFace
from core.router.tier_resolver import available_tiers_from, resolve_next_available_tier

__all__ = [
    "CouncilRouter",
    "LocalFace",
    "ClassifyDecision",
    "resolve_keyword_tool",
    "resolve_next_available_tier",
    "available_tiers_from",
    # константы категорий намерений
    "INTENT_APP",
    "INTENT_MEDIA",
    "INTENT_BROWSER",
    "INTENT_SYSTEM",
    "INTENT_WEB",
    "INTENT_FILE",
    "INTENT_NONE",
]
