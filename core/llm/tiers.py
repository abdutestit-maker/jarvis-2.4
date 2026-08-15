"""Тиры «совета мудрецов».

Совет устроен так: локальная Qwen 4B (тир ``FAST``) — это лицо Джарвиса.
Она отвечает сама, пока справляется, и эскалирует запрос выше, когда нужна
более сильная модель:

    FAST (Qwen 4B, локально)
      -> ANALYST   (DeepSeek V4 Flash)  — анализ, планирование, рассуждение
      -> CODER     (Kimi K3 / Hy3)      — код, фронтенд, рефакторинг
      -> ARCHITECT (Claude Opus 5)      — архитектура, самые сложные задачи

Конкретные model-id намеренно НЕ зашиты в код: они живут в
``settings.model_tiers`` и правятся пользователем, потому что имена
моделей у провайдеров меняются.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

__all__ = [
    "Tier",
    "ESCALATION_ORDER",
    "resolve_tier",
    "tier_to_backend_key",
    "next_tier",
    "tier_purpose",
]


class Tier(str, Enum):
    """Уровни совета. Значение = ключ в ``settings.model_tiers``."""

    FAST = "fast"
    ANALYST = "analyst"
    CODER = "coder"
    ARCHITECT = "architect"

    def __str__(self) -> str:  # чтобы f-строки давали 'fast', а не 'Tier.FAST'
        return self.value


#: Порядок эскалации снизу вверх.
ESCALATION_ORDER: tuple[Tier, ...] = (Tier.FAST, Tier.ANALYST, Tier.CODER, Tier.ARCHITECT)

#: Человекочитаемое назначение тира — идёт в промпт роутера (Часть 2).
_TIER_PURPOSE: Dict[Tier, str] = {
    Tier.FAST: "быстрые ответы, приветствия, простые команды, факты из памяти",
    Tier.ANALYST: "анализ, планирование, рассуждение, разбор длинных текстов",
    Tier.CODER: "написание и отладка кода, фронтенд, скрипты",
    Tier.ARCHITECT: "архитектура систем, сложные многошаговые задачи, ревью",
}

#: Синонимы, которые может выдать локальная модель или указать пользователь.
_ALIASES: Dict[str, Tier] = {
    # FAST
    "fast": Tier.FAST,
    "local": Tier.FAST,
    "qwen": Tier.FAST,
    "qwen4b": Tier.FAST,
    "qwen-4b": Tier.FAST,
    "self": Tier.FAST,
    "face": Tier.FAST,
    # ANALYST
    "analyst": Tier.ANALYST,
    "analysis": Tier.ANALYST,
    "analyse": Tier.ANALYST,
    "analyze": Tier.ANALYST,
    "planner": Tier.ANALYST,
    "plan": Tier.ANALYST,
    "deepseek": Tier.ANALYST,
    "deepseek-v4-flash": Tier.ANALYST,
    # CODER
    "coder": Tier.CODER,
    "code": Tier.CODER,
    "coding": Tier.CODER,
    "dev": Tier.CODER,
    "frontend": Tier.CODER,
    "kimi": Tier.CODER,
    "hy3": Tier.CODER,
    # ARCHITECT
    "architect": Tier.ARCHITECT,
    "architecture": Tier.ARCHITECT,
    "hard": Tier.ARCHITECT,
    "expert": Tier.ARCHITECT,
    "claude": Tier.ARCHITECT,
    "opus": Tier.ARCHITECT,
}


def resolve_tier(tier_name: Optional[str], default: Tier = Tier.FAST) -> Tier:
    """Приводит произвольную строку к ``Tier``.

    Толерантна к регистру, пробелам, подчёркиваниям и синонимам:
    ``"Tier.CODER"``, ``" kimi "``, ``"code"`` -> ``Tier.CODER``.
    Неизвестное значение -> ``default`` (не исключение: решение роутера не
    должно ломать пайплайн).
    """
    if isinstance(tier_name, Tier):
        return tier_name
    if not tier_name:
        return default

    key = str(tier_name).strip().lower().replace("_", "-").replace(" ", "")
    if key.startswith("tier."):
        key = key.split(".", 1)[1]

    if key in _ALIASES:
        return _ALIASES[key]
    # прямое совпадение со значением enum ('fast', 'analyst', ...)
    for tier in Tier:
        if tier.value == key:
            return tier
    return default


def tier_to_backend_key(tier: Tier) -> str:
    """Ключ тира в ``settings.model_tiers`` / ``settings.tier_providers``."""
    return resolve_tier(tier).value


def next_tier(tier: Tier) -> Optional[Tier]:
    """Следующий тир вверх по цепочке эскалации или ``None`` для вершины."""
    current = resolve_tier(tier)
    index = ESCALATION_ORDER.index(current)
    if index + 1 >= len(ESCALATION_ORDER):
        return None
    return ESCALATION_ORDER[index + 1]


def tier_purpose(tier: Tier) -> str:
    """Описание назначения тира (для промптов и логов)."""
    return _TIER_PURPOSE.get(resolve_tier(tier), "")


def all_tiers() -> List[Tier]:
    """Все тиры в порядке эскалации."""
    return list(ESCALATION_ORDER)
