"""Ручной тест совета мудрецов (без pytest, без сети/ключей/GGUF).

Запуск::

    python scripts/test_router_manual.py

Скрипт создаёт CouncilRouter на реальном config/settings.json и прогоняет
несколько фраз. Поскольку в конфиге нет API-ключей и нет файла GGUF,
модели недоступны — скрипт проверяет, что совет мудрецов КРАСИВО
деградирует (не падает, не бросает исключений), а не ломается.

Что проверяем:
    * "привет"            -> intent=none, деградация до локальной (или сообщение об оффлайне)
    * "открой блокнот"    -> intent=app, scope=self (простая команда)
    * "объясни квантовую физику" -> intent=none/web, escalate -> нет ключей -> оффлайн-фолбэк
"""

from __future__ import annotations

import sys
from pathlib import Path

# Чтобы запускать скрипт из любой папки, добавляем корень проекта в sys.path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config import load_config  # noqa: E402
from core.router import CouncilRouter, resolve_keyword_tool  # noqa: E402
from core.state import new_state  # noqa: E402
from core.utils.logger import setup_logging  # noqa: E402

# Логируем в консоль, но без шума таймингов библиотек.
setup_logging(level="WARNING", console=True)


def run_one(router: CouncilRouter, text: str) -> None:
    """Прогоняет одну фразу и печатает результат маршрутизации."""
    print("\n" + "=" * 72)
    print(f">> ЗАПРОС: {text!r}")
    state = new_state(text)
    router.route(state)

    intent = state.get("intent")
    tier = state.get("tier")
    error = state.get("error")
    response = state.get("response") or ""
    latency = state.get("latency") or {}

    print(f"   intent           : {intent}")
    print(f"   выбранный тир    : {tier}")
    print(f"   ошибка           : {error or '—'}")
    print(f"   время (сек)      : {latency.get('total', '?')}")
    print(f"   ответ (обрезан)  : {response[:200]!r}")


def main() -> None:
    print("Загрузка конфигурации...")
    settings = load_config()

    # Покажем, какие тиры вообще доступны (без ключей — только local, да и то
    # только если есть GGUF-файл).
    available = settings.available_tiers()
    print(f"Доступные тиры: {[t.value for t in available] or 'НЕТ (ни одного)'}")

    router = CouncilRouter(settings)

    # Прямая проверка keyword-роутера.
    for probe in ("привет", "открой блокнот", "объясни квантовую физику",
                  "включи музыку", "найди рецепт борща", "прочитай файл readme"):
        print(f"   intent[{probe!r}] = {resolve_keyword_tool(probe, probe)}")

    # Сквозной прогон через совет мудрецов.
    for phrase in ("привет", "открой блокнот", "объясни квантовую физику"):
        run_one(router, phrase)

    print("\n" + "=" * 72)
    print("ТЕСТ ЗАВЕРШЁН: совет мудрецов не упал ни на одном запросе.")


if __name__ == "__main__":
    main()
