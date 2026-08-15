"""Верификация: latency classify НЕ должен вызывать эскалацию на 7B.

Запускает тот же Orchestrator.handle_input, который использует фронтенд
(Tauri) — это и есть реальный путь бага. main.py REPL перехватывает
«голос добавить» как встроенную команду, поэтому здесь вызываем
handle_input напрямую, как это делает UI.

TTS отключён программно (settings.voice.tts_enabled=False) ради чистого
вывода в headless-режиме — это не влияет на роутинг/классификацию.
"""
from __future__ import annotations

import os
import sys
import time

# Репозиторий должен быть на sys.path (запуск из scripts/ кладёт туда scripts/).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import load_config
from core.orchestrator import Orchestrator
from core.utils.logger import setup_logging

setup_logging(level="INFO", console=True)

settings = load_config()
settings.ensure_directories()
settings.voice.tts_enabled = False  # headless: без озвучки

orch = Orchestrator(settings)
orch.start()

TESTS = [
    "голос добавить",  # ТЕСТ 1 из ТЗ: конкретный баг-запрос
    "привет",          # ТЕСТ 2 из ТЗ
    # ТЕСТ 3 из ТЗ: запрос на код -> должен остаться fast (не по latency!)
    "напиши функцию на Python для сортировки списка",
    # ДОП. ТЕСТ: intent=file -> идёт ЧЕРЕЗ LLM-классификатор (classify()),
    # чтобы показать, что content-based эскалация (если модель решит) жива,
    # а latency-эскалация — нет.
    "открой файл с кодом и напиши функцию сортировки списка",
]

try:
    for t in TESTS:
        print("\n" + "=" * 70)
        print(">>> ТЕСТОВЫЙ ЗАПРОС:", repr(t))
        print("=" * 70)
        t0 = time.perf_counter()
        state = orch.handle_input(t)
        dt = time.perf_counter() - t0
        print("--- РЕЗУЛЬТАТ ВИТКА ---")
        print("tier   :", state.get("tier"))
        print("error  :", state.get("error"))
        print("intent :", state.get("intent"), "| время витка %.2fs" % dt)
        print("response head:", (state.get("response") or "")[:160].replace("\n", " "))
finally:
    orch.shutdown()
print("\n=== ВЕРИФИКАЦИЯ ЗАВЕРШЕНА ===")
