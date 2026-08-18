"""Sprint 4 — LIVE SMOKE TEST (STEP 6). Запуск: python tests/_sprint4_smoke.py

Реальные вызовы моделей anymodel + реальная session/persistent memory:
  TEST A — Память: «Меня зовут Абду» -> «Как меня зовут?» знает имя
  TEST B — Session context: «Я люблю пиццу» -> «Что я люблю?»
  TEST C — Persona: «Привет» -> бодрый неформальный тон
  TEST D — Action не сломан: «Какие файлы в documents?» -> list_files
  TEST E — Streaming + memory: длинный разговор, контекст не теряется

Профиль изолируется во временный каталог (не трогаем боевой profile.json).
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import load_config
from core.agent import Agent, AgentConfig

PASS, FAIL = "  [PASS]", "  [FAIL]"
results: list = []


def report(name: str, ok: bool, detail: str) -> None:
    results.append((name, ok))
    print(f"{PASS if ok else FAIL} {name}: {detail}")


def main() -> int:
    settings = load_config()
    tmp = tempfile.mkdtemp(prefix="jarvis-s4-smoke-")
    settings.paths.profile_dir = tmp  # изолируем persistent memory смока

    agent = Agent(settings, config=AgentConfig(enable_skill_forge=False))
    timings: dict = {}

    def talk(label: str, text: str) -> str:
        started = time.perf_counter()
        outcome = agent.execute(text)
        timings[label] = time.perf_counter() - started
        print(f"    [{label}] {timings[label]:.1f} c -> {outcome.text[:90]}")
        return outcome.text

    # ------------------------------------------------------------------ #
    print("\n=== TEST A — Память: имя ===")
    talk("A1", "Меня зовут Абду")
    answer_a = talk("A2", "Как меня зовут?")
    report("A имя вспомнено", "абду" in answer_a.lower(),
           f"ответ содержит имя: {'абду' in answer_a.lower()}")

    # ------------------------------------------------------------------ #
    print("\n=== TEST B — Session context: предпочтение ===")
    talk("B1", "Я люблю пиццу с грибами")
    answer_b = talk("B2", "Что я люблю?")
    report("B предпочтение вспомнено", "пицц" in answer_b.lower(),
           f"ответ содержит 'пицц': {'пицц' in answer_b.lower()}")

    # ------------------------------------------------------------------ #
    print("\n=== TEST C — Persona: бодрый тон ===")
    answer_c = talk("C", "Привет")
    formal = any(m in answer_c.lower() for m in
                 ("готов оказать помощь", "чем могу помочь вам", "как я могу помочь"))
    report("C живой тон (не колл-центр)", len(answer_c) > 3 and not formal,
           f"formal={formal}, len={len(answer_c)}")

    # ------------------------------------------------------------------ #
    print("\n=== TEST D — Action не сломан ===")
    started = time.perf_counter()
    outcome_d = agent.execute("Какие файлы в папке documents?")
    timings["D"] = time.perf_counter() - started
    report("D action path с list_files",
           outcome_d.tool_used == "list_files" and outcome_d.verified,
           f"tool={outcome_d.tool_used}, verified={outcome_d.verified}, "
           f"{timings['D']:.1f} c")

    # ------------------------------------------------------------------ #
    print("\n=== TEST E — Streaming + длинный разговор ===")
    chunks: list = []

    def sink(visible: str) -> None:
        chunks.append(visible)

    agent.install_stream_sink(sink)
    try:
        # Контекст из середины разговора + свежий вопрос (стрим должен идти).
        talk("E1", "Расскажи коротко, чем занимался Тьюринг")
        answer_e = talk("E2", "А что он придумал для теста на интеллект?")
    finally:
        agent.clear_stream_sink()
    streamed = len(chunks) >= 2  # кумулятивный sink зовётся многократно
    report("E1 streaming работает", streamed, f"chunks={len(chunks)}")
    report("E2 контекст разговора держится",
           "тьюринг" in answer_e.lower() or "тест" in answer_e.lower(),
           f"ответ связан с темой: {answer_e[:60]}...")

    # ------------------------------------------------------------------ #
    fast = [v for k, v in timings.items() if k.startswith(("A2", "B2", "C"))]
    report("F fast path не разжался (Sprint 3 скорость)",
           bool(fast) and max(fast) < 20,
           f"макс разговорный: {max(fast):.1f} c" if fast else "нет данных")

    shutil.rmtree(tmp, ignore_errors=True)
    ok = sum(1 for _, o in results if o)
    print(f"\n=== ИТОГ SMOKE: {ok}/{len(results)} PASS ===")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
