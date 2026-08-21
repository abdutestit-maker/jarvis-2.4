"""Understanding Layer — контракты единого понимания пользовательского ввода.

Один модуль — одна точка классификации для консоли, WebSocket и фронта.
Заменяет рассогласованную тройку: ``needsMission()`` на фронте,
``intent_router.resolve_keyword_tool`` и ``_should_run_background`` на беке
(баги A2/A4: «открой блокнот» распознавался как голосовое обращение,
шаблонные ответы вместо действий).

Маршруты (``Route``):
    * ``reflex``       — время/дата/приветствие, ответ без LLM (<100 мс).
    * ``quick_answer`` — вопрос о мире/знаниях → короткий ответ 1-3 сек
                         (поиск → сжатие), без миссий и планирования.
    * ``action``       — 1-3 инструмента синхронно, с верификацией.
    * ``mission``      — многошаговая работа с состоянием (презентации,
                         отчёты) → фон, ACK с ``mission_id``.
    * ``clarify``      — ввод пуст/неясен → живой уточняющий вопрос,
                         НИКОГДА не молчание и не canned-шаблон.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

__all__ = ["Route", "Understanding"]


class Route(str, Enum):
    """Маршрут обработки пользовательского ввода."""

    REFLEX = "reflex"
    QUICK_ANSWER = "quick_answer"
    ACTION = "action"
    MISSION = "mission"
    CLARIFY = "clarify"


@dataclass
class Understanding:
    """Результат классификации одного пользовательского ввода.

    Attributes:
        route: куда направить ввод (см. ``Route``).
        intent: предметная область — ``app`` / ``media`` / ``browser`` /
            ``system`` / ``web`` / ``file`` / ``dialog`` / ``none``.
            Для quick_answer — всегда ``web``; для reflex — ``dialog``.
        confidence: 0.0-1.0. Ниже порога (~0.7) вызывается Tier-1
            LLM-классификатор (Фаза 1 поставляет Tier-0 regex; Tier-1
            подключается в Фазе 2 вместе с провайдером Flash Lite).
        entities: извлечённые параметры — ``app_name``, ``query``,
            ``target_path`` и т.п. (заполняется по мере надобности).
        compound: если команда составная («сделай X и потом Y») —
            список фрагментов; каждый маршрутизируется отдельно (фикс A3).
        privacy: True — содержит приватные данные, в облако НЕ отправлять
            (принудительно локальная модель).
        source: кто классифицировал — ``regex`` (Tier-0), ``llm`` (Tier-1),
            ``fallback``.
        reason: человекочитаемое обоснование маршрута (для логов и clarify).
    """

    route: Route
    intent: str = "none"
    confidence: float = 1.0
    entities: Dict[str, str] = field(default_factory=dict)
    compound: List[str] = field(default_factory=list)
    privacy: bool = False
    source: str = "regex"
    reason: str = ""
