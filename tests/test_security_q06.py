"""Тесты Q06 (P1 §6 + NEXT) — computer-use слой ТОЛЬКО fake/dry-run.

DoD: mouse/keyboard/screenshot как tools с dry-run; тесты НЕ двигают
реальную мышь.

Проверяем:
1. Инструменты регистрируются и возвращают ok=True с пометкой dry-run.
2. Намерения записываются в контроллер.
3. Модуль НЕ импортирует реальные библиотеки ввода (pyautogui/pynput/
   win32api) — значит реальный ввод физически невозможен.
4. НИКАКОЙ реальный ввод не происходит (нет вызовов указателя/клавиш).
"""

from __future__ import annotations

import sys

from config.settings import Settings
from core.actions.base import ToolContext
from core.actions.computer_use import (
    ComputerKeyboardTool,
    ComputerMouseTool,
    ComputerScreenshotTool,
    DryRunInputController,
    _CONTROLLER,
)


def test_computer_use_tools_registered():
    from core.actions import DEFAULT_REGISTRY
    for name in ("computer_mouse", "computer_keyboard", "computer_screenshot"):
        assert DEFAULT_REGISTRY.get(name) is not None, f"инструмент {name} не зарегистрирован"


def test_computer_mouse_is_dry_run():
    ctx = ToolContext(settings=Settings())
    res = ComputerMouseTool().run({"action": "click", "x": 100, "y": 200}, ctx)
    assert res.ok is True
    assert "dry-run" in res.output.lower()
    assert "реальн" in res.output.lower()


def test_computer_keyboard_is_dry_run():
    ctx = ToolContext(settings=Settings())
    res = ComputerKeyboardTool().run({"action": "type", "text": "hello"}, ctx)
    assert res.ok is True
    assert "dry-run" in res.output.lower()


def test_computer_screenshot_is_dry_run():
    ctx = ToolContext(settings=Settings())
    res = ComputerScreenshotTool().run({"path": "shot.png"}, ctx)
    assert res.ok is True
    assert "dry-run" in res.output.lower()


def test_intents_recorded():
    before = len(_CONTROLLER.actions)
    ctx = ToolContext(settings=Settings())
    ComputerMouseTool().run({"action": "move", "x": 1, "y": 2}, ctx)
    ComputerKeyboardTool().run({"action": "press", "key": "enter"}, ctx)
    ComputerScreenshotTool().run({}, ctx)
    assert len(_CONTROLLER.actions) == before + 3
    kinds = [a["kind"] for a in _CONTROLLER.actions[-3:]]
    assert "computer_mouse" in kinds
    assert "computer_keyboard" in kinds
    assert "computer_screenshot" in kinds
    # Все записи помечены dry_run.
    assert all(a["mode"] == "dry_run" for a in _CONTROLLER.actions[-3:])


def test_no_real_input_libraries_imported():
    """Модуль computer_use НЕ содержит реальных библиотек/вызовов ввода.

    Доказывает, что реальный ввод физически невозможен: в исходнике модуля
    нет импортов pyautogui/pynput/win32api/ctypes и нет ссылок на них в коде
    (докстринги НЕ учитываются — в них эти слова могут упоминаться как
    «мы их не используем»). Контроллер не умеет 'исполнять' — только
    записывать.
    """
    import ast
    import core.actions.computer_use as cu
    import inspect

    src = inspect.getsource(cu)
    tree = ast.parse(src)

    # 1) Нет импортов реальных библиотек ввода.
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    for lib in ("pyautogui", "pynput", "win32api", "ctypes", "autopy"):
        assert not any(lib in n for n in imported), f"запрещённый импорт: {lib}"

    # 2) Нет ссылок на реальный ввод в коде (пропускаем докстринги).
    doc_nodes = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.ClassDef)):
            body = node.body
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                doc_nodes.add(id(body[0].value))
    forbidden = ("pyautogui", "SendInput", "ctypes.windll", "pynput", "win32api")
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in doc_nodes:
                continue
            for f in forbidden:
                assert f not in node.value, f"запрещённая библиотека ввода в коде: {f}"

    # 3) Контроллер не умеет «исполнять» — только записывать.
    assert hasattr(cu.DryRunInputController, "record")
    assert not hasattr(cu.DryRunInputController, "execute")
