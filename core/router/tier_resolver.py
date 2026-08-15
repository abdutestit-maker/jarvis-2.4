"""Разрешение тира для эскалации — тонкая обёртка над core/llm/tiers.py.

Здесь НЕ дублируется логика тиров. Модуль лишь использует уже готовые
``ESCALATION_ORDER`` и ``settings.is_tier_available()``, чтобы найти
первый доступный тир не ниже заданного.
"""

from __future__ import annotations

from typing import List, Optional

from config.settings import Settings
from core.llm import ESCALATION_ORDER, resolve_tier, Tier
from core.utils.logger import get_logger

__all__ = ["resolve_next_available_tier", "available_tiers_from"]

log = get_logger(__name__)


def resolve_next_available_tier(settings: Settings, current_tier: Tier) -> Optional[Tier]:
    """Возвращает первый доступный тир не ниже ``current_tier``.

    Идёт по ``ESCALATION_ORDER`` (FAST → ANALYST → CODER → ARCHITECT) от
    позиции ``current_tier`` и возвращает первый, для которого
    ``settings.is_tier_available()`` истинно. Это гарантирует, что мы не
    «понизим» тир и не пропустим доступную промежуточную модель.

    Args:
        settings: конфигурация проекта.
        current_tier: тир, с которого начинаем поиск вверх.

    Returns:
        Доступный тир или ``None``, если выше ``current_tier`` ничего
        доступного нет (включая сам ``current_tier``).
    """
    resolved = resolve_tier(current_tier)
    try:
        start_index = ESCALATION_ORDER.index(resolved)
    except ValueError:
        # Неизвестный тир — начинаем снизу (FAST).
        log.warning("Неизвестный тир %s, начинаю поиск с FAST", resolved)
        start_index = 0

    for tier in ESCALATION_ORDER[start_index:]:
        if settings.is_tier_available(tier):
            return tier
    return None


def available_tiers_from(settings: Settings, current_tier: Tier) -> List[Tier]:
    """Все доступные тиры от ``current_tier`` и выше (в порядке эскалации)."""
    resolved = resolve_tier(current_tier)
    try:
        start_index = ESCALATION_ORDER.index(resolved)
    except ValueError:
        start_index = 0
    return [tier for tier in ESCALATION_ORDER[start_index:] if settings.is_tier_available(tier)]
