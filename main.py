#!/usr/bin/env python
"""Точка входа — Living Jarvis.

Загружает конфигурацию, создаёт Orchestrator, запускает консольный REPL.
Обработка Ctrl+C — graceful shutdown.
"""

from __future__ import annotations

import signal
import sys
import threading
from pathlib import Path
from typing import Optional

from config import load_config
from core.orchestrator import Orchestrator
from core.utils.logger import setup_logging, get_logger

__all__ = ["main"]

log = get_logger(__name__)

# Глобальный оркестратор для signal handler
_orchestrator: Optional[Orchestrator] = None
_shutdown_event = threading.Event()
_shutdown_lock = threading.Lock()
_shutdown_started = False


def _shutdown_once() -> None:
    """Останавливает оркестратор ровно один раз, включая путь через сигнал."""
    global _shutdown_started
    with _shutdown_lock:
        if _shutdown_started:
            return
        _shutdown_started = True
    if _orchestrator:
        _orchestrator.shutdown()


def signal_handler(signum: int, frame) -> None:
    """Обработчик SIGINT/SIGTERM — graceful shutdown."""
    log.info("Получен сигнал %s, завершение...", signum)
    _shutdown_event.set()
    _shutdown_once()


def print_banner() -> None:
    """Печатает баннер запуска."""
    banner = r"""
╔═══════════════════════════════════════════════════════════════════╗
║  ██╗ █████╗ ███████╗████████╗███████╗██████╗  █████╗ ███╗   ██╗  ║
║  ██║██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔══██╗██╔══██╗████╗  ██║  ║
║  ██║███████║███████╗   ██║   █████╗  ██████╔╝███████║██╔██╗ ██║  ║
║  ██║██╔══██║╚════██║   ██║   ██╔══╝  ██╔══██╗██╔══██║██║╚██╗██║  ║
║  ██║██║  ██║███████║   ██║   ███████╗██║  ██║██║  ██║██║ ╚████║  ║
║  ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝  ║
║                                                                    ║
║  Living Jarvis — локальный ИИ-ассистент для Windows               ║
║  Версия: 0.1.0-dev                                                ║
╚═══════════════════════════════════════════════════════════════════╝
"""
    print(banner)
    print("Команды: 'выход' / 'exit' / 'quit' — завершить работу")
    print("         'пауза' / 'pause' — приостановить TTS очередь")
    print("         'продолжить' / 'resume' — возобновить TTS очередь")
    print("         'статус' / 'status' — статус системы")
    print("         'модели' / 'models' — список зарегистрированных моделей/голосов")
    print("         'подтвердить' / 'отклонить' — ответ на запрос подтверждения (HIGH-risk)")
    print("         'модель добавить' — интерактивно зарегистрировать локальную GGUF")
    print("         'голос добавить' — интерактивно зарегистрировать голос Piper")
    print("         'голос тест' — озвучить тестовую фразу (Jarvis/irina)")
    print("-" * 64)


def _cmd_add_model(settings) -> None:
    """Интерактивная регистрация локальной GGUF-модели."""
    from core.utils import ModelManager

    try:
        path = input("  Путь к файлу *.gguf > ").strip().strip('"')
        name = input("  Логическое имя (напр. qwen-coder-local) > ").strip()
        print("  Доступные роли: fast, analyst, coder, architect, embedding")
        role = input("  Роль (тир) > ").strip().lower()
        if role not in ("fast", "analyst", "coder", "architect", "embedding"):
            print("  ⚠ Неизвестная роль, использую 'coder'")
            role = "coder"
        mm = ModelManager(settings)
        mm.register_local_model(name, path, role=role)
        print(f"  ✓ Модель '{name}' зарегистрирована для роли '{role}'")
        print("    Перезагрузите Jarvis, чтобы применить.")
    except Exception as exc:
        print(f"  ⚠ Ошибка: {exc}")


def _cmd_add_voice(settings) -> None:
    """Интерактивная регистрация голоса Piper."""
    from core.utils import ModelManager

    try:
        onnx = input("  Путь к файлу *.onnx голоса > ").strip().strip('"')
        json_path = input("  Путь к *.onnx.json конфигу (пусто = искать рядом) > ").strip().strip('"') or None
        lang = input("  Язык (en/ru, пусто = ru) > ").strip().lower() or "ru"
        name = input("  Имя голоса (напр. jarvis-medium) > ").strip() or Path(onnx).stem
        mm = ModelManager(settings)
        mm.register_voice(name, onnx, json_path, language=lang)
        print(f"  ✓ Голос '{name}' ({lang}) зарегистрирован")
    except Exception as exc:
        print(f"  ⚠ Ошибка: {exc}")


def _cmd_test_voice(settings) -> None:
    """Озвучивает тестовую фразу через PiperTTS (выбор голоса по языку)."""
    from core.voice import PiperTTS

    try:
        text = input("  Фраза для озвучки > ").strip()
        if not text:
            text = "Сэр, системы в норме. Jarvis к вашим услугам."
        tts = PiperTTS(settings)
        if not tts.is_available():
            print("  ⚠ Piper недоступен — проверьте piper.exe и голоса в data/models/piper/")
            return
        print(f"  (озвучка через: {tts._select_voice(text).name})")
        tts.speak(text, blocking=True)
        print("  ✓ Озвучка завершена (если есть колонки — должны были услышать)")
    except Exception as exc:
        print(f"  ⚠ Ошибка: {exc}")


def _answer_confirm(orchestrator, confirmation_id: str, approved: bool) -> None:
    """Отвечает на ожидающее подтверждение HIGH-risk операции (§21).

    Результат выводится через output_callback оркестратора (там же, где
    и обычные ответы), поэтому здесь только обрабатываем отсутствие
    подтверждения и дополнительные подтверждения.
    """
    try:
        state = orchestrator.answer_confirmation(confirmation_id, approved)
        if state is None:
            print("⚠️ Подтверждение не найдено (возможно, устарело).")
            return
        if state.get("needs_confirmation"):
            print("⏳ Требуется дополнительное подтверждение.")
    except Exception as exc:
        log.error("Ошибка подтверждения: %s", exc)
        print(f"⚠️ Внутренняя ошибка: {exc}")


def main() -> int:
    """Главная функция."""
    global _orchestrator
    global _shutdown_started

    # Настройка логирования
    setup_logging(level="INFO", console=True)
    _shutdown_event.clear()
    with _shutdown_lock:
        _shutdown_started = False

    # Загрузка конфигурации
    settings = load_config()
    try:
        from core.llm.hardware_profile import apply_profile
        apply_profile(settings, logger=log)
    except Exception as exc:
        log.warning("Автопрофиль локальной модели пропущен: %s", exc)
    settings.ensure_directories()

    _confirmation_id: Optional[str] = None
    exit_code = 0
    try:
        # Создание и запуск находятся в одном жизненном цикле с REPL.
        _orchestrator = Orchestrator(settings)

        # Регистрация signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        _orchestrator.start()

        print_banner()

        # REPL цикл
        while not _shutdown_event.is_set():
            try:
                user_input = input("\n🎙  Сёр > ").strip()
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\n[Ctrl+C] Завершение...")
                break

            if not user_input:
                continue

            # Встроенные команды
            cmd = user_input.lower()
            if cmd in ("выход", "exit", "quit", "q"):
                break
            elif cmd in ("пауза", "pause"):
                _orchestrator.tts_queue.pause()
                print("⏸ TTS очередь приостановлена")
                continue
            elif cmd in ("продолжить", "resume"):
                _orchestrator.tts_queue.resume()
                print("▶️ TTS очередь возобновлена")
                continue
            elif cmd in ("статус", "status"):
                from core.actions.system import system_status
                status = system_status()
                for k, v in status.items():
                    print(f"  {k}: {v}")
                continue

            elif cmd in ("модели", "models"):
                from core.utils import ModelManager
                mm = ModelManager(settings)
                models = mm.list_models()
                print("\n📋 Зарегистрированные модели и голоса:")
                if not models:
                    print("  (пусто)")
                for tier, info in models.items():
                    if tier == "voices":
                        print(f"  🎙 Голоса:")
                        for v in info:
                            print(f"    - {v.get('model_path')} [{v.get('language')}]")
                    else:
                        print(f"  🧠 {tier}: {info.get('model_id')} -> {info.get('path')} (provider: {info.get('provider')})")
                continue

            elif cmd in ("модель добавить", "model add"):
                _cmd_add_model(settings)
                continue

            elif cmd in ("голос добавить", "voice add"):
                _cmd_add_voice(settings)
                continue

            elif cmd in ("голос тест", "voice test"):
                _cmd_test_voice(settings)
                continue

            # Подтверждение HIGH-risk операции (§21): ответ из CLI.
            # Слова «да»/«нет» маршрутизируются только при активном
            # подтверждении, чтобы не перехватывать обычный диалог.
            elif cmd in ("подтвердить", "confirm", "да", "yes") and _confirmation_id:
                _answer_confirm(_orchestrator, _confirmation_id, True)
                _confirmation_id = None
                continue
            elif cmd in ("отклонить", "reject", "нет", "no") and _confirmation_id:
                _answer_confirm(_orchestrator, _confirmation_id, False)
                _confirmation_id = None
                continue

            # Обработка через оркестратор
            try:
                state = _orchestrator.handle_input(user_input)
                # Запоминаем активное подтверждение для следующего шага.
                _confirmation_id = state.get("confirmation_id")
                # Ответ уже выведен через output_callback
                if state.get("error"):
                    print(f"⚠️  Ошибка: {state['error']}")
            except Exception as exc:
                log.error("Ошибка обработки ввода: %s", exc)
                print(f"⚠️  Внутренняя ошибка: {exc}")

    except KeyboardInterrupt:
        pass
    except Exception as exc:
        log.exception("Ошибка запуска или работы Jarvis: %s", exc)
        exit_code = 1
    finally:
        print("\n👋 Завершение работы...")
        _shutdown_event.set()
        _shutdown_once()
        print("Готово.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
