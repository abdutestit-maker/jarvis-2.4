"""Контекстный бюджет по тирам (Sprint 4, STEP 2.3).

Правило: system prompt неприкосновенен (персона/факты — ядро поведения),
история диалога усекается СНАЧАЛА (старые сообщения вытесняются), текущий
user-вопрос не режется никогда. Оценка токенов офлайн: для русского текста
~3 символа на токен (консервативно — лучше недосчитать контекст, чем
перелить окно модели).

Бюджеты (Sprint 4):
    TIER 1 fast chat      — 2000 токенов (история + факты + промпт)
    TIER 2 action planner — 4000 токенов
    TIER 3 deep           — 8000 токенов
"""

from __future__ import annotations

from typing import Dict, List

from core.state import Message

__all__ = ["estimate_tokens", "fit_messages_to_budget", "CHARS_PER_TOKEN"]

#: Консервативная оценка: 3 символа ~= 1 токен (рус/англ смесь).
CHARS_PER_TOKEN = 3


def estimate_tokens(text: str) -> int:
    """Офлайн-оценка числа токенов в строке."""
    if not text:
        return 0
    return max(1, len(text) // CHARS_PER_TOKEN)


def messages_tokens(messages: List[Message]) -> int:
    """Суммарная оценка токенов списка сообщений (+ служебные ~4 на сообщение)."""
    return sum(estimate_tokens(m.get("content", "")) + 4 for m in messages)


def fit_messages_to_budget(
    system: str,
    history: List[Message],
    user: str,
    budget_tokens: int,
) -> List[Message]:
    """Собирает ``messages`` под бюджет: system + урезанная история + user.

    Args:
        system: системный промпт (не режется — считается целиком).
        history: накопленная история диалога (хронологический порядок).
        user: текущий вопрос пользователя (не режется).
        budget_tokens: общий бюджет в токенах.

    Returns:
        Готовый список сообщений для LLM: урезанная история + user.
        Если system+user сами не влезают в бюджет — возвращается только
        ``[user]`` (ответ без истории лучше, чем никакого).
    """
    user_msg: Message = {"role": "user", "content": user}
    fixed = estimate_tokens(system) + estimate_tokens(user) + 8

    remaining = budget_tokens - fixed
    if remaining < 0:
        # Даже пара system+user не влезает — отдаём голый вопрос.
        return [user_msg]

    # Идём с конца (свежие важнее), пока влезает.
    kept_reversed: List[Message] = []
    for message in reversed(history):
        cost = estimate_tokens(message.get("content", "")) + 4
        if remaining - cost < 0:
            break
        remaining -= cost
        kept_reversed.append(message)

    kept = list(reversed(kept_reversed))
    kept.append(user_msg)
    return kept
