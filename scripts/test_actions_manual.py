"""Ручной тест движка действий (Part 4).

Проверяет через DEFAULT_REGISTRY:
- system_status (реальный)
- web_search на тестовый запрос (реальный, требует интернет)
- filesystem write+read+delete тестового файла в documents_dir
- list_reminders на пустом менеджере
- resolve_app на 2-3 известных программах
- volume (проверка доступности pycaw/pyautogui)
- weather (реальный, требует интернет)

Сетевые ошибки логируются и не считаются провалом теста.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config import load_config  # noqa: E402
from core.actions import (  # noqa: E402
    DEFAULT_REGISTRY,
    ToolContext,
    execute_tool,
    get_tools_schema,
    list_available_tools,
)
from core.utils.logger import setup_logging  # noqa: E402

setup_logging(level="INFO", console=True)


def rule(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def make_context() -> ToolContext:
    settings = load_config()
    settings.ensure_directories()
    return ToolContext(settings=settings, user_id="test_user")


def test_system_status(ctx: ToolContext) -> None:
    rule("1. system_status")
    result = execute_tool(DEFAULT_REGISTRY, "system_status", {}, ctx)
    print(f"ok={result.ok}, duration={result.duration_sec:.3f}s")
    print(f"output: {result.output}")
    if result.error:
        print(f"error: {result.error}")


def test_web_search(ctx: ToolContext) -> None:
    rule("2. web_search (DuckDuckGo)")
    result = execute_tool(DEFAULT_REGISTRY, "web_search", {"query": "Python 3.11 new features", "max_results": 3}, ctx)
    print(f"ok={result.ok}, duration={result.duration_sec:.3f}s")
    if result.ok:
        print(f"output:\n{result.output[:500]}...")
    else:
        print(f"error (network ok): {result.error}")


def test_filesystem(ctx: ToolContext) -> None:
    rule("3. filesystem (write -> read -> delete)")

    # write
    test_content = "Тестовый файл для проверки filesystem tool.\nВторая строка.\n"
    result = execute_tool(DEFAULT_REGISTRY, "write_file", {"path": "test_actions.txt", "content": test_content}, ctx)
    print(f"write: ok={result.ok}")
    if result.error:
        print(f"  error: {result.error}")
        return

    # read
    result = execute_tool(DEFAULT_REGISTRY, "read_file", {"path": "test_actions.txt"}, ctx)
    print(f"read: ok={result.ok}")
    if result.ok:
        print(f"  output: {result.output[:200]}...")

    # list
    result = execute_tool(DEFAULT_REGISTRY, "list_files", {"dir_path": "", "recursive": False}, ctx)
    print(f"list: ok={result.ok}, files={len(result.output.split('📄')) - 1 if result.ok else 0}")

    # search
    result = execute_tool(DEFAULT_REGISTRY, "search_files", {"query": "Тестовый", "max_results": 10}, ctx)
    print(f"search: ok={result.ok}")

    # delete (через write пустого + удаление файла вручную)
    import os
    from config.settings import Settings
    settings = ctx.settings
    docs_dir = settings.paths.resolved("documents_dir")
    test_file = docs_dir / "test_actions.txt"
    try:
        test_file.unlink()
        print("  test file deleted")
    except Exception as exc:
        print(f"  cleanup error: {exc}")


def test_reminders(ctx: ToolContext) -> None:
    rule("4. reminders (list on empty manager)")
    result = execute_tool(DEFAULT_REGISTRY, "list_reminders", {}, ctx)
    print(f"ok={result.ok}")
    print(f"output: {result.output}")


def test_resolve_app(ctx: ToolContext) -> None:
    rule("5. app_control (resolve_app)")
    from core.actions.app_control import resolve_app

    test_names = ["блокнот", "chrome", "word", "несуществующее_приложение_123"]
    for name in test_names:
        cmd = resolve_app(name, ctx.settings)
        status = "✓" if cmd else "✗"
        print(f"  {status} {name:30s} -> {cmd or 'NOT FOUND'}")


def test_volume(ctx: ToolContext) -> None:
    rule("6. volume (check availability)")
    from core.actions.system import increase_volume, decrease_volume, mute_volume

    result = increase_volume(5)
    print(f"  up: ok={result.ok}, output={result.output or result.error}")
    result = decrease_volume(5)
    print(f"  down: ok={result.ok}, output={result.output or result.error}")
    result = mute_volume()
    print(f"  mute: ok={result.ok}, output={result.output or result.error}")


def test_weather(ctx: ToolContext) -> None:
    rule("7. weather (open-meteo)")
    result = execute_tool(DEFAULT_REGISTRY, "weather", {"location": "Москва", "forecast_days": 1}, ctx)
    print(f"ok={result.ok}, duration={result.duration_sec:.3f}s")
    if result.ok:
        print(f"output:\n{result.output}")
    else:
        print(f"error (network ok): {result.error}")


def main() -> None:
    print("=== ТЕСТ ДВИЖКА ДЕЙСТВИЙ (Part 4) ===")
    print(f"Доступные инструменты: {list_available_tools()}")
    print(f"Function calling schema: {len(get_tools_schema())} tools")

    ctx = make_context()

    test_system_status(ctx)
    test_web_search(ctx)
    test_filesystem(ctx)
    test_reminders(ctx)
    test_resolve_app(ctx)
    test_volume(ctx)
    test_weather(ctx)

    print("\n" + "=" * 70)
    print("ТЕСТ ЗАВЕРШЁН")
    print("=" * 70)


if __name__ == "__main__":
    main()