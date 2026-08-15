"""Model Router — выбор модели по СЛОЖНОСТИ задачи (§15, §17).

Критерии выбора (§15):
    complexity, reasoning requirement, context size, confidence,
    privacy, speed, cost, availability.

КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО (§4, §15):
    "если ответ дольше N секунд -> плохая модель"
Латентность НЕ является критерием качества и НЕ используется здесь ни как
вход, ни как причина отказа. Долгий ответ — нормальный ответ.

Политика (§17):
    простая задача            -> LOCAL FIRST (Qwen3-4B, FAST)
    сложная / глубокая        -> внешняя модель (analyst / coder / architect)
    внешняя недоступна        -> graceful fallback обратно на локальную
    приватные данные          -> принудительно локально

Модуль работает поверх существующих ``core.llm`` (Tier, factory,
tier_resolver) — не заменяет их, а добавляет осознанное решение «какой
тир нужен этой задаче».
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from config.settings import Settings
from core.llm.tiers import ESCALATION_ORDER, Tier
from core.utils.logger import get_logger

__all__ = [
    "TaskComplexity",
    "RoutingDecision",
    "ModelRouter",
    "estimate_complexity",
]

log = get_logger(__name__)


# --------------------------------------------------------------------------- #
#  Оценка сложности
# --------------------------------------------------------------------------- #

@dataclass
class TaskComplexity:
    """Профиль сложности задачи (§15). Латентность здесь отсутствует намеренно."""

    score: float                       # 0.0 (тривиально) .. 1.0 (максимум)
    reasoning_required: bool = False
    context_tokens: int = 0
    code_related: bool = False
    architectural: bool = False
    private: bool = False
    multi_step: bool = False
    signals: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 3),
            "reasoning_required": self.reasoning_required,
            "context_tokens": self.context_tokens,
            "code_related": self.code_related,
            "architectural": self.architectural,
            "private": self.private,
            "multi_step": self.multi_step,
            "signals": list(self.signals),
        }


_TRIVIAL_RE = re.compile(
    r"^\s*(привет|здравствуй|хай|hi|hello|спасибо|пока|как дела|ок|окей|да|нет|"
    r"доброе утро|добрый день|добрый вечер|спокойной ночи)\b",
    re.IGNORECASE,
)

_SIMPLE_COMMAND_RE = re.compile(
    r"\b(открой|запусти|закрой|включи|выключи|сделай (тише|громче)|громкость|"
    r"напомни|погода|статус|open|launch|close|volume)\b",
    re.IGNORECASE,
)

_REASONING_RE = re.compile(
    r"\b(проанализируй|анализ|сравни|сравнение|объясни|почему|обоснуй|"
    r"исследуй|изучи|разбери|оцени|выбери лучш|плюсы и минусы|стратег|"
    r"analyze|compare|explain|research|evaluate|investigate)\b",
    re.IGNORECASE,
)

_CODE_RE = re.compile(
    r"\b(код|скрипт|функци|класс|рефактор|дебаг|отлад|баг|исключени|traceback|"
    r"python|javascript|typescript|react|sql|api|компилир|тест[ыу]?|"
    r"code|script|function|refactor|debug|bug|compile)\b",
    re.IGNORECASE,
)

_ARCH_RE = re.compile(
    r"\b(архитектур|спроектируй|проектирован|схем[аыу] системы|микросервис|"
    r"масштабир|ревью|review|architecture|design (a |the )?system|migrate)\b",
    re.IGNORECASE,
)

_PRIVATE_RE = re.compile(
    r"\b(пароль|паспорт|карт[аыу] (банк|кредит)|снилс|инн|секрет|приватн|"
    r"личн[ыа]|конфиденциальн|password|secret|private|confidential|ssn)\b",
    re.IGNORECASE,
)

_MULTISTEP_RE = re.compile(
    r"\b(затем|потом|после этого|сначала|шаг \d|этап|и потом|"
    r"then|after that|step \d)\b",
    re.IGNORECASE,
)


def estimate_complexity(goal: str, context_tokens: int = 0,
                        multi_step_hint: bool = False) -> TaskComplexity:
    """Оценивает сложность задачи детерминированно и офлайн (§15).

    Args:
        goal: цель пользователя.
        context_tokens: оценка размера контекста (из ingest, §7).
        multi_step_hint: планировщик уже знает, что шагов несколько.

    Returns:
        ``TaskComplexity``. Время выполнения НЕ учитывается (§4).
    """
    text = (goal or "").strip()
    signals: List[str] = []
    score = 0.15  # база: даже простая команда — не нулевая работа

    if _TRIVIAL_RE.match(text):
        signals.append("тривиальное обращение")
        score = 0.02
    elif _SIMPLE_COMMAND_RE.search(text):
        signals.append("простая детерминированная команда")
        score = 0.1

    reasoning = bool(_REASONING_RE.search(text))
    if reasoning:
        signals.append("требуется рассуждение/анализ")
        score += 0.35

    code = bool(_CODE_RE.search(text))
    if code:
        signals.append("связано с кодом")
        score += 0.25

    arch = bool(_ARCH_RE.search(text))
    if arch:
        signals.append("архитектурная задача")
        score += 0.4

    private = bool(_PRIVATE_RE.search(text))
    if private:
        signals.append("приватные данные — только локально")

    multi = multi_step_hint or bool(_MULTISTEP_RE.search(text))
    if multi:
        signals.append("многошаговая задача")
        score += 0.2

    # Длина запроса как признак объёма работы (НЕ времени).
    length = len(text)
    if length > 2000:
        signals.append(f"очень большой ввод ({length} символов)")
        score += 0.25
    elif length > 500:
        signals.append(f"объёмный ввод ({length} символов)")
        score += 0.1

    if context_tokens > 6000:
        signals.append(f"большой контекст (~{context_tokens} токенов)")
        score += 0.2
    elif context_tokens > 2000:
        score += 0.1

    return TaskComplexity(
        score=max(0.0, min(1.0, score)),
        reasoning_required=reasoning,
        context_tokens=context_tokens,
        code_related=code,
        architectural=arch,
        private=private,
        multi_step=multi,
        signals=signals,
    )


# --------------------------------------------------------------------------- #
#  Решение о маршрутизации
# --------------------------------------------------------------------------- #

@dataclass
class RoutingDecision:
    """Куда отправить задачу (§15, §17)."""

    tier: Tier
    complexity: TaskComplexity
    reason: str = ""
    fallback_chain: List[Tier] = field(default_factory=list)
    forced_local: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier.value,
            "reason": self.reason,
            "fallback_chain": [t.value for t in self.fallback_chain],
            "forced_local": self.forced_local,
            "complexity": self.complexity.to_dict(),
        }


class ModelRouter:
    """Выбирает тир модели по сложности задачи и доступности (§15, §17)."""

    #: Порог, ниже которого локальная модель обязана справиться сама.
    LOCAL_THRESHOLD = 0.35
    #: Порог, выше которого нужен самый сильный тир.
    ARCHITECT_THRESHOLD = 0.75

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # ------------------------------------------------------------------ #
    def route(self, goal: str, context_tokens: int = 0,
              multi_step_hint: bool = False,
              local_confidence: Optional[float] = None) -> RoutingDecision:
        """Возвращает тир для задачи.

        Args:
            goal: цель пользователя.
            context_tokens: размер контекста.
            multi_step_hint: известно, что шагов несколько.
            local_confidence: уверенность локальной модели (0..1), если её
                уже спрашивали. Низкая уверенность повышает шанс эскалации.

        Returns:
            ``RoutingDecision`` с основным тиром и цепочкой fallback.
        """
        cx = estimate_complexity(goal, context_tokens, multi_step_hint)

        # 1) Приватность (§15) — жёстко локально, без внешних API.
        if cx.private:
            return RoutingDecision(
                tier=Tier.FAST,
                complexity=cx,
                reason="приватные данные: обработка только локальной моделью",
                fallback_chain=[],
                forced_local=True,
            )

        # 2) Низкая уверенность локальной модели повышает сложность.
        score = cx.score
        if local_confidence is not None and local_confidence < 0.5:
            score = min(1.0, score + 0.25)
            cx.signals.append(f"низкая уверенность локальной модели ({local_confidence:.2f})")

        # 3) Выбор целевого тира по сложности (НЕ по времени §4).
        if score < self.LOCAL_THRESHOLD:
            target = Tier.FAST
            reason = f"простая задача (score={score:.2f}) — local first"
        elif cx.architectural or score >= self.ARCHITECT_THRESHOLD:
            target = Tier.ARCHITECT
            reason = f"архитектурная/очень сложная задача (score={score:.2f})"
        elif cx.code_related:
            target = Tier.CODER
            reason = f"задача по коду (score={score:.2f})"
        else:
            target = Tier.ANALYST
            reason = f"нужен анализ/рассуждение (score={score:.2f})"

        chain = self._build_chain(target)
        if not chain:
            # Ни один внешний тир не настроен — честная деградация (§17).
            return RoutingDecision(
                tier=Tier.FAST,
                complexity=cx,
                reason=f"{reason}; внешние модели недоступны — graceful fallback на локальную",
                fallback_chain=[],
                forced_local=True,
            )

        return RoutingDecision(
            tier=chain[0],
            complexity=cx,
            reason=reason if chain[0] is target else f"{reason}; тир '{target.value}' недоступен",
            fallback_chain=chain[1:],
        )

    # ------------------------------------------------------------------ #
    def _build_chain(self, target: Tier) -> List[Tier]:
        """Цепочка доступных тиров: целевой, затем соседние, затем локальный."""
        candidates: List[Tier] = [target]
        # Сначала пробуем более сильные, затем более слабые внешние.
        idx = ESCALATION_ORDER.index(target)
        candidates += [t for t in ESCALATION_ORDER[idx + 1:]]
        candidates += [t for t in reversed(ESCALATION_ORDER[:idx]) if t is not Tier.FAST]
        candidates.append(Tier.FAST)

        chain: List[Tier] = []
        for tier in candidates:
            if tier in chain:
                continue
            if self._is_available(tier):
                chain.append(tier)
        return chain

    def _is_available(self, tier: Tier) -> bool:
        """Реальная доступность тира по конфигурации (ключ / путь к модели)."""
        try:
            return bool(self._settings.is_tier_available(tier))
        except Exception as exc:
            log.debug("Проверка доступности тира %s не удалась: %s", tier, exc)
            return tier is Tier.FAST
