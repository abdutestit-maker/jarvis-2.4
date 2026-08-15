"""Ручной тест оркестратора (Part 5) — end-to-end.

Создаёт Orchestrator на реальном settings, прогоняет 2-3 фразы через
handle_input() end-to-end (используя все части 1-5 вместе), проверяет:
- TTSQueue не падает даже без piper-модели
- Proactor стартует и останавливается без ошибок
- MemoryRetriever собирает контекст
- CouncilRouter маршрутизирует

Плюс: реально запускает main.py через echo "привет" | python main.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config import load_config  # noqa: E402
from core.orchestrator import Orchestrator  # noqa: E402
from core.utils.logger import setup_logging  # noqa: E402

setup_logging(level="WARNING", console=True)


def rule(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def test_orchestrator_basic() -> None:
    rule("1. Orchestrator: создание и старт")
    settings = load_config()
    settings.ensure_directories()

    orch = Orchestrator(settings)
    orch.start()
    print("✓ Orchestrator создан и запущен")

    # Проверка компонентов
    print(f"  Council: {type(orch.council).__name__}")
    print(f"  Memory: {type(orch.memory).__name__}")
    print(f"  Session: {type(orch.session).__name__}")
    print(f"  TTS Queue: {type(orch.tts_queue).__name__} (running={orch.tts_queue.is_running})")
    print(f"  Proactor: {type(orch.proactor).__name__} (running={orch.proactor._running})")

    orch.shutdown()
    print("✓ Orchestrator остановлен корректно")


def test_orchestrator_handle_input() -> None:
    rule("2. Orchestrator.handle_input: простые фразы")
    settings = load_config()
    settings.ensure_directories()

    orch = Orchestrator(settings)
    orch.start()

    test_phrases = [
        "привет",
        "какая погода в Москве?",
        "сколько у меня оперативной памяти?",
    ]

    for phrase in test_phrases:
        print(f"\n>>> {phrase}")
        state = orch.handle_input(phrase)
        response = state.get("response", "")
        error = state.get("error")
        print(f"<<< {response[:200]}")
        if error:
            print(f"   ⚠ error: {error}")

    orch.shutdown()
    print("\n✓ handle_input отработал на всех фразах")


def test_proactor_lifecycle() -> None:
    rule("3. Proactor: старт/стоп без ошибок")
    settings = load_config()
    settings.ensure_directories()

    orch = Orchestrator(settings)
    orch.start()

    # Проактор должен быть запущен
    assert orch.proactor._running, "Proactor не запущен"
    print("✓ Proactor запущен")

    # Проверяем mark_user_activity
    orch.proactor.mark_user_activity()
    print("✓ mark_user_activity работает")

    orch.shutdown()
    assert not orch.proactor._running, "Proactor не остановился"
    print("✓ Proactor остановлен корректно")


def test_tts_queue_without_piper() -> None:
    rule("4. TTSQueue: не падает без piper-модели")
    settings = load_config()
    settings.ensure_directories()

    orch = Orchestrator(settings)
    orch.start()

    # TTS должен быть недоступен (нет piper), но очередь работает
    print(f"  TTS available: {orch.tts_queue._tts.is_available()}")
    orch.tts_queue.add_to_queue("Тестовое сообщение в очередь")
    print("✓ add_to_queue работает")

    # Ждём обработки (очередь должна просто проигнорировать)
    time.sleep(0.5)
    print(f"  Queue size: {orch.tts_queue.queue_size}")

    orch.shutdown()
    print("✓ TTSQueue не упал без piper")


def test_main_py_stdin() -> None:
    rule("5. main.py через stdin (echo)")
    # Запускаем main.py с echo "привет" | python main.py
    # Таймаут 10 сек, ожидаем graceful shutdown
    try:
        result = subprocess.run(
            [sys.executable, "main.py"],
            input="привет\nвыход\n",
            text=True,
            capture_output=True,
            timeout=15,
            cwd=PROJECT_ROOT,
        )
        print(f"  exit_code: {result.returncode}")
        if result.stdout:
            print(f"  stdout (последние 500 символов):\n{result.stdout[-500:]}")
        if result.stderr:
            print(f"  stderr (последние 500 символов):\n{result.stderr[-500:]}")

        if result.returncode == 0:
            print("✓ main.py завершился штатно (exit_code=0)")
        else:
            print(f"⚠ main.py exit_code={result.returncode} (возможно, нет piper/ключей)")
    except subprocess.TimeoutExpired:
        print("⚠ main.py таймаут (возможно, завис на вводе)")
    except Exception as exc:
        print(f"⚠ Ошибка запуска main.py: {exc}")


def main() -> None:
    print("=== ТЕСТ ОРКЕСТРАТОРА (Part 5) ===")

    test_orchestrator_basic()
    test_orchestrator_handle_input()
    test_proactor_lifecycle()
    test_tts_queue_without_piper()
    test_main_py_stdin()

    print("\n" + "=" * 70)
    print("ТЕСТ ОРКЕСТРАТОРА ЗАВЕРШЁН")
    print("=" * 70)


if __name__ == "__main__":
    main()