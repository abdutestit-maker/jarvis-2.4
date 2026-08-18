"""Приветствие при старте сессии (Sprint 5, STEP 3).

Триггер — первый WS-клиент после запуска backend'а (не каждое открытие
окна). Текст — в стиле персоны Sprint 4, с учётом локального времени и
имени из персистентного профиля.
"""

from __future__ import annotations

import datetime
from typing import Optional

from config.settings import Settings
from core.memory.profile import load_profile
from core.utils.logger import get_logger

__all__ = ["build_startup_greeting"]

log = get_logger(__name__)


def build_startup_greeting(settings: Settings,
                           now: Optional[datetime.datetime] = None) -> str:
    """Time-aware приветствие в стиле персоны.

    Утро (6-12): «Доброе утро, [имя]. Я на месте, всё чисто.»
    День (12-18): «Привет, [имя]. Чем займёмся?»
    Вечер (18-23): «Вечер, [имя]. Я тут, если что.»
    Ночь (23-6): «[имя], ты снова ночью? Ладно, я с тобой.»
    Без имени — first-contact: «О, ты вернулся. Как тебя зовут, кстати?»
    """
    name = ""
    try:
        name = (load_profile(settings).get("name") or "").strip()
    except Exception as exc:  # noqa: BLE001 — профиль не обязан существовать
        log.debug("Профиль недоступен для приветствия: %s", exc)

    hour = (now or datetime.datetime.now()).hour
    if 6 <= hour < 12:
        text = "Доброе утро, {who}. Я на месте, всё чисто."
    elif 12 <= hour < 18:
        text = "Привет, {who}. Чем займёмся?"
    elif 18 <= hour < 23:
        text = "Вечер, {who}. Я тут, если что."
    else:
        text = "{who}, ты снова ночью? Ладно, я с тобой."

    if name:
        return text.format(who=name)
    # Имени нет — знакомимся (first contact, Sprint 4).
    if 6 <= hour < 12:
        return "О, доброе утро. Как тебя зовут, кстати?"
    if 18 <= hour < 23:
        return "О, вечер. Как тебя зовут, кстати?"
    if hour >= 23 or hour < 6:
        return "О, ты снова ночью. Как тебя зовут, кстати?"
    return "О, ты вернулся. Как тебя зовут, кстати?"
