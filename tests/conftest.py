"""Фикстуры для интеграционных тестов спринта P0.

Главная идея: подменяем ``get_llm_backend`` фейковым бэкендом, чтобы
прогнать ВСЮ реальную цепочку Джарвиса (intent -> risk -> MODEL SELECTION
-> tool retrieval -> plan -> execute -> verify -> repair -> confirmation
-> memory) без живых моделей и сети. Это и есть честный integration test:
мы не мокаем сам Agent/Orchestrator, а только самый нижний слой LLM.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from typing import Any, Dict, List, Optional

# Гарантируем воспроизводимость pytest отовсюду: корень проекта в sys.path,
# иначе `pytest` (без `python -m`) не видит пакеты `config`/`core`.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pytest

from config.settings import Settings
from core.llm import Tier
from core.llm.backend import BackendUnavailable, LLMBackend, normalize_messages


class FakeBackend(LLMBackend):
    """Детерминированный бэкенд: возвращает заданный JSON-план.

    Управляется через ``responses`` — список строк для chat().
    По умолчанию реализует два сценария:
      * "plan"  — решение использовать инструмент;
      * "answer" — обычный ответ без инструмента.
    Тесты могут переопределить через ``set_plan`` / ``set_answer``.
    """

    name = "fake:test"
    model = "fake-test"

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings
        self._plan = self._default_plan()
        self._answer = "Сэр, я вас понял. Это тестовый ответ Джарвиса."
        self._calls: List[Dict[str, Any]] = []
        self._requested_tiers: List[Any] = []
        self._lock = threading.Lock()

    # --- запись запрошенных тиров (для TEST6: propagation роутинга) ---
    def record_tier(self, tier: Any) -> None:
        with self._lock:
            self._requested_tiers.append(tier)

    @property
    def requested_tiers(self) -> List[Any]:
        with self._lock:
            return list(self._requested_tiers)

    # --- управление поведением ---
    def set_plan(self, tool: str, arguments: Dict[str, Any], reason: str = "test") -> None:
        self._plan = json.dumps({
            "tool": tool,
            "arguments": arguments,
            "reason": reason,
            "risk": "low",
            "verification": "проверка выполнения",
            "answer": "",
        }, ensure_ascii=False)

    def set_answer(self, text: str) -> None:
        self._answer = text

    def record(self, messages: List[Dict[str, Any]], system: Optional[str]) -> None:
        with self._lock:
            self._calls.append({"messages": list(messages), "system": system})

    @property
    def calls(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._calls)

    def _last_user_text(self, messages: List[Dict[str, Any]]) -> str:
        for m in reversed(messages):
            if m.get("role") == "user":
                return m.get("content", "")
        return ""

    def _is_plan_request(self, messages: List[Dict[str, Any]]) -> bool:
        text = self._last_user_text(messages)
        # _decide_with_model шлёт инструменты + "Цель пользователя: ..."
        return "Цель пользователя:" in text

    @staticmethod
    def _default_plan() -> str:
        # по умолчанию — простой ответ, чтобы TEST 1 не лез в инструменты
        return json.dumps({
            "tool": None,
            "arguments": {},
            "reason": "простой диалог",
            "risk": "low",
            "verification": "",
            "answer": "Сэр, я вас понял. Это тестовый ответ Джарвиса.",
        }, ensure_ascii=False)

    # --- LLMBackend API ---
    def direct(self, prompt: str, system=None, max_tokens=None, temperature=None) -> str:
        return self._answer

    def chat(self, messages, system=None, max_tokens=None, temperature=None) -> str:
        self.record(messages, system)
        if self._is_plan_request(messages):
            return self._plan
        return self._answer

    def streaming(self, messages, system=None, max_tokens=None, temperature=None):
        yield self.chat(messages, system=system)

    def list_models(self) -> List[str]:
        return ["fake-test"]

    def warm_up(self) -> None:
        return None

    def is_available(self) -> bool:
        return True

    def close(self) -> None:
        return None


@pytest.fixture
def fake_backend(monkeypatch):
    """Подменяет get_llm_backend фейковим бэкендом для Tier.FAST.

    Возвращает сам FakeBackend, чтобы тесты могли настроить plan/answer.
    Все тиры (fast/analyst/coder/architect) отдают один и тот же фейк —
    это достаточно, чтобы проверить propagation роутинга и execution path.
    """
    from core import llm as llm_mod

    backend = FakeBackend()

    original = llm_mod.get_llm_backend

    def _fake_get(settings, tier=Tier.FAST):
        # записываем, какой тир реально запрошен у бэкенда — это и есть
        # проверка propagation роутинга (TEST6): решение ModelRouter должно
        # дойти до вызова get_llm_backend с ЭТИМ тиром.
        backend.record_tier(tier)
        return backend

    monkeypatch.setattr(llm_mod, "get_llm_backend", _fake_get)
    # Некоторые пути импортируют get_llm_backend напрямую в модули —
    # подменим и в agent (он импортирует из core.llm).
    import core.agent as agent_mod
    monkeypatch.setattr(agent_mod, "get_llm_backend", _fake_get)
    # Тесты офлайн: заставляем все тиры считаться доступными, чтобы
    # _backend_for_routing реально доходил до get_llm_backend (фейка),
    # а не пропускал его по is_tier_available и не сваливался в unknown.
    monkeypatch.setattr(Settings, "is_tier_available", lambda self, tier: True)
    return backend


@pytest.fixture
def settings():
    """Настройки с отключёнными внешними ключами (всё локально)."""
    s = Settings()
    # Гарантируем офлайн-режим: без ключей внешние тиры недоступны.
    s.api_keys.deepseek = ""
    s.api_keys.kimi = ""
    s.api_keys.claude = ""
    return s
