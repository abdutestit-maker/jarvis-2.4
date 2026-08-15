"""Проверка логики решений совета мудрецов с ПОДДЕЛЬНЫМИ бэкендами.

Цель: доказать, что выбор тира корректен, когда модели ДОСТУПНЫ,
не полагаясь на реальный GGUF/ключи (которых нет в dev-окружении).

Прогоняем 4 сценария:
  1) scope=self  -> используется FAST (локальная)
  2) escalate/analyst, analyst доступен -> используется analyst
  3) escalate/analyst, analyst НЕТ, coder есть -> используется coder (подъём)
  4) escalate, НИ ОДНОГО тира нет -> деградация до локальной + оффлайн-фолбэк
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config import load_config  # noqa: E402
from core.llm import Tier  # noqa: E402
from core.router import CouncilRouter  # noqa: E402
from core.router.local_face import LocalFace  # noqa: E402
from core.state import new_state  # noqa: E402

# Подменяем реальный фабричный вызов, чтобы не трогать настоящие модели.
import core.llm.factory as factory  # noqa: E402
import core.router.council as council  # noqa: E402
from core.llm.backend import LLMBackend  # noqa: E402


class FakeBackend(LLMBackend):
    """Счётчик вызовов: просто возвращает имя тира как ответ."""
    supports_tools = False

    def __init__(self, name: str) -> None:
        self.name = name
        self.model = name
        self._calls = 0

    def direct(self, prompt, system=None, max_tokens=None, temperature=None):
        self._calls += 1
        return f"[ответ от {self.name}]"

    def chat(self, messages, system=None, max_tokens=None, temperature=None):
        self._calls += 1
        return f"[ответ от {self.name}]"

    def streaming(self, messages, system=None, max_tokens=None, temperature=None):
        yield f"[ответ от {self.name}]"

    def list_models(self):
        return [self.model]

    def warm_up(self):
        pass

    def is_available(self):
        return True


class FakeFace(LocalFace):
    """Лицо, возвращающее заранее заданное решение классификации."""
    def __init__(self, backend, settings, decision):
        super().__init__(backend, settings)
        self._decision = decision

    def classify(self, system, user_input, intent):
        from core.router.local_face import ClassifyDecision
        return ClassifyDecision(self._decision)

    def respond(self, system, messages):
        # Локальный ответ идёт через локальный бэкенд.
        return self._backend.chat(messages, system=system)


def make_router(settings, decision, available_tiers):
    """Собирает роутер с подменёнными бэкендами и лицом."""
    backends = {t.value: FakeBackend(t.value) for t in Tier}
    router = CouncilRouter(settings)
    router._local_backend = backends["fast"]
    router._local_face = FakeFace(backends["fast"], settings, decision)
    # Подменяем фабрику: всегда отдаём нужный fake по тиру.
    def fake_get(settings_, tier):
        return backends.get(Tier(resolve_tier_safe(tier)).value, backends["fast"])
    import core.llm.tiers as tiers
    def resolve_tier_safe(t):
        from core.llm import resolve_tier
        return resolve_tier(t)
    council.get_llm_backend = fake_get
    factory.get_llm_backend = fake_get
    # Помечаем тиры доступными согласно сценарию.
    orig_available = settings.is_tier_available
    settings.is_tier_available = lambda t: Tier(resolve_tier_safe(t)) in available_tiers
    return router, backends


def run_scenario(label, decision, available_tiers, phrase="тестовый запрос"):
    settings = load_config()
    router, backends = make_router(settings, decision, available_tiers)
    state = new_state(phrase)
    router.route(state)
    print(f"\n[{label}]")
    print(f"  intent={state.get('intent')} chosen_tier={state.get('tier')}")
    print(f"  ответ={state.get('response')!r}")
    # Какой fake был вызван?
    called = [name for name, b in backends.items() if b._calls > 0]
    print(f"  задействованные бэкенды: {called}")
    return state


def main():
    # 1) self -> FAST
    run_scenario("1. scope=self", {"scope": "self", "tier": None, "reason": "x"},
                 {Tier.FAST, Tier.ANALYST, Tier.CODER, Tier.ARCHITECT})
    # 2) escalate/analyst, analyst доступен
    run_scenario("2. escalate->analyst (analyst доступен)",
                 {"scope": "escalate", "tier": "analyst", "reason": "x"},
                 {Tier.FAST, Tier.ANALYST, Tier.CODER, Tier.ARCHITECT})
    # 3) escalate/analyst, НО analyst недоступен, coder доступен -> подъём
    run_scenario("3. escalate->analyst (analyst НЕТ, coder ЕСТЬ)",
                 {"scope": "escalate", "tier": "analyst", "reason": "x"},
                 {Tier.FAST, Tier.CODER, Tier.ARCHITECT})
    # 4) escalate, ничего не доступно -> деградация до FAST
    run_scenario("4. escalate (НИ ОДНОГО тира нет) -> деградация",
                 {"scope": "escalate", "tier": "analyst", "reason": "x"},
                 set())
    print("\n=== ПРОВЕРКА ЛОГИКИ ЗАВЕРШЕНА ===")


if __name__ == "__main__":
    main()
