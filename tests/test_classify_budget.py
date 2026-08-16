"""P5 §5.8 — бюджет classify() и отсутствие лишней эскалации.

После §5.7 выбор тира делегирован единому ModelRouter (estimate_complexity
по capability, а НЕ по латентности). Этот тест фиксирует, что типовая
простая команда не улетает в лишнюю эскалацию на тяжёлую модель, и что
целевой бюджет локальной модели реалистичен (поднят с нереалистичных 1.5с).
"""

from __future__ import annotations

from config.settings import Settings
from core.model_router import ModelRouter, estimate_complexity
from core.llm.tiers import Tier


def test_simple_command_stays_local():
    """Простая команда -> FAST тир, без эскалации (capability, не latency)."""
    mr = ModelRouter(Settings())
    decision = mr.route("открой браузер")
    assert decision.tier is Tier.FAST, \
        f"простая команда не должна эскалировать, получили {decision.tier}"
    assert decision.complexity.score < mr.LOCAL_THRESHOLD


def test_classify_budget_is_realistic():
    """Целевой бюджет локальной модели поднят до реального (~3.2с)."""
    settings = Settings()
    assert settings.limits.local_latency_target_sec >= 3.0, \
        "local_latency_target_sec должен быть реалистичным (>=3.0с), а не 1.5с"


def test_complexity_ignores_latency():
    """estimate_complexity НЕ штрафует за длину/время как за сложность тира.

    Длинный, но тривиальный текст не должен скакать выше порога эскалации
    только из-за объёма ввода (ТЗ §4: latency != capability).
    """
    trivial = estimate_complexity("привет")
    long_trivial = estimate_complexity("привет " * 500)  # ~2500 символов
    # Даже длинный приветственный текст — не сложная задача.
    assert long_trivial.score < ModelRouter.LOCAL_THRESHOLD, \
        "объём ввода не должен эскалировать тривиальный запрос"
    assert long_trivial.score >= trivial.score  # длина даёт небольшую надбавку
