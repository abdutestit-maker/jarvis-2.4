"""Управление Windows-приложениями (app_control).

Инструменты:
- ``OpenAppTool`` — запускает приложение по разговорному имени.
- ``CloseAppTool`` — закрывает приложение по имени процесса.

Сопоставление имен ведётся через словарь популярных программ + настройки
пользователя (``settings.apps.custom``).
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

from config.settings import Settings
from core.actions.base import ActionResult, Tool, ToolContext
from core.actions.registry import DEFAULT_REGISTRY
from core.utils.logger import get_logger

__all__ = [
    "resolve_app",
    "open_app",
    "close_app",
    "OpenAppTool",
    "CloseAppTool",
]

log = get_logger(__name__)

#: Встроенное сопоставление разговорных имён -> команды/пути (Windows).
#: Ключи — нормализованные нижний регистр.
_BUILTIN_APPS: Dict[str, str] = {
    # Системные
    "блокнот": "notepad.exe",
    "notepad": "notepad.exe",
    "калькулятор": "calc.exe",
    "calculator": "calc.exe",
    "командная строка": "cmd.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "проводник": "explorer.exe",
    "explorer": "explorer.exe",
    "диспетчер задач": "taskmgr.exe",
    "task manager": "taskmgr.exe",
    "настройки": "ms-settings:",
    "settings": "ms-settings:",
    # Браузеры (пути типичные для Windows)
    "браузер": "browser",
    "browser": "browser",
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "яндекс": r"C:\Users\%USERNAME%\AppData\Local\Yandex\YandexBrowser\Application\browser.exe",
    "yandex": r"C:\Users\%USERNAME%\AppData\Local\Yandex\YandexBrowser\Application\browser.exe",
    # Офис
    "word": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "excel": r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    "powerpoint": r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
    "outlook": r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE",
    # Медиа
    "влк": r"C:\Program Files\VideoLAN\VLC\vlc.exe",
    "vlc": r"C:\Program Files\VideoLAN\VLC\vlc.exe",
    "potplayer": r"C:\Program Files\DAUM\PotPlayer\PotPlayerMini64.exe",
    # Разработка
    "vscode": r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "code": r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "pycharm": r"C:\Program Files\JetBrains\PyCharm\bin\pycharm64.exe",
    "idea": r"C:\Program Files\JetBrains\IntelliJ IDEA\bin\idea64.exe",
    # Коммуникация
    "телеграм": r"C:\Users\%USERNAME%\AppData\Roaming\Telegram Desktop\Telegram.exe",
    "telegram": r"C:\Users\%USERNAME%\AppData\Roaming\Telegram Desktop\Telegram.exe",
    "discord": r"C:\Users\%USERNAME%\AppData\Local\Discord\app-*\Discord.exe",
    # Архиваторы
    "7zip": r"C:\Program Files\7-Zip\7zFM.exe",
    "7-zip": r"C:\Program Files\7-Zip\7zFM.exe",
    "winrar": r"C:\Program Files\WinRAR\WinRAR.exe",
}

#: Имена процессов для закрытия (ключ — то же имя, что и в _BUILTIN_APPS)
_APP_PROCESS_NAMES: Dict[str, List[str]] = {
    "блокнот": ["notepad.exe"],
    "notepad": ["notepad.exe"],
    "калькулятор": ["CalculatorApp.exe", "calc.exe"],
    "calculator": ["CalculatorApp.exe", "calc.exe"],
    "командная строка": ["cmd.exe"],
    "cmd": ["cmd.exe"],
    "powershell": ["powershell.exe", "pwsh.exe"],
    "проводник": ["explorer.exe"],
    "explorer": ["explorer.exe"],
    "диспетчер задач": ["Taskmgr.exe"],
    "task manager": ["Taskmgr.exe"],
    "chrome": ["chrome.exe"],
    "firefox": ["firefox.exe"],
    "edge": ["msedge.exe"],
    "яндекс": ["browser.exe"],
    "yandex": ["browser.exe"],
    "word": ["WINWORD.EXE"],
    "excel": ["EXCEL.EXE"],
    "powerpoint": ["POWERPNT.EXE"],
    "outlook": ["OUTLOOK.EXE"],
    "влк": ["vlc.exe"],
    "vlc": ["vlc.exe"],
    "potplayer": ["PotPlayerMini64.exe", "PotPlayerMini.exe"],
    "vscode": ["Code.exe"],
    "code": ["Code.exe"],
    "pycharm": ["pycharm64.exe"],
    "idea": ["idea64.exe"],
    "телеграм": ["Telegram.exe"],
    "telegram": ["Telegram.exe"],
    "discord": ["Discord.exe"],
    "7zip": ["7zFM.exe"],
    "7-zip": ["7zFM.exe"],
    "winrar": ["WinRAR.exe"],
}


def _expand_env_vars(path: str) -> str:
    """Раскрывает переменные окружения (%USERNAME% и т.п.)."""
    return os.path.expandvars(path)


def _find_executable(cmd: str) -> Optional[str]:
    """Пытается найти исполняемый файл (по PATH или как абсолютный путь)."""
    # Если это URI-схема (ms-settings:) — возвращаем как есть
    if ":" in cmd and not cmd.startswith("\\") and not cmd[0].isalpha():
        return cmd
    # Абсолютный путь
    expanded = _expand_env_vars(cmd)
    if os.path.isabs(expanded):
        # Поддержка масок типа app-* для Discord
        if "*" in expanded:
            parent = Path(expanded).parent
            pattern = Path(expanded).name
            try:
                matches = list(parent.glob(pattern))
                if matches:
                    return str(matches[0])
            except Exception:
                pass
        if Path(expanded).exists():
            return expanded
    # Поиск в PATH
    if sys.platform == "win32":
        # where.exe работает только для .exe
        try:
            result = subprocess.run(
                ["where.exe", cmd], capture_output=True, text=True, timeout=3, shell=False
            )
            if result.returncode == 0:
                return result.stdout.strip().splitlines()[0]
        except Exception:
            pass
    return None


def resolve_app(name: str, settings: Optional[Settings] = None) -> Optional[str]:
    """Сопоставляет разговорное имя с реальной командой/путем.

    Порядок поиска:
    1. Пользовательские настройки (``settings.apps.custom``).
    2. Встроенный словарь ``_BUILTIN_APPS``.
    3. Прямой поиск в PATH (если имя похоже на исполняемый файл).

    Args:
        name: разговорное имя (например, "хром", "блокнот").
        settings: конфигурация (опционально).

    Returns:
        Команда/путь для запуска или None, если не найдено.
    """
    key = name.strip().lower()

    # 1. Кастомные приложения из настроек
    if settings is not None:
        custom = getattr(getattr(settings, "apps", None), "custom", {}) or {}
        if key in custom:
            return _expand_env_vars(custom[key])

    # 2. Встроенный словарь
    if key in _BUILTIN_APPS:
        builtin = _BUILTIN_APPS[key]
        # Windows resolves canonical system executables through CreateProcess
        # directly. Avoid a synchronous ``where.exe`` probe on every fast
        # command; full paths/URI targets still go through validation.
        if builtin.casefold().endswith(".exe") and not any(token in builtin for token in ("\\", "/", "%")):
            return builtin
        return _find_executable(builtin)

    # 3. Попытка найти как есть (если пользователь сказал полный путь или имя в PATH)
    return _find_executable(name)


def open_app(name: str, settings: Optional[Settings] = None, args: str = "") -> ActionResult:
    """Запускает приложение.

    Args:
        name: разговорное имя приложения.
        settings: конфигурация.
        args: дополнительные аргументы командной строки.

    Returns:
        ActionResult с ok=True при успехе.
    """
    cmd = resolve_app(name, settings)
    if cmd is None:
        return ActionResult(
            tool="open_app",
            args={"name": name, "args": args},
            ok=False,
            error=f"Приложение '{name}' не найдено. Проверьте настройки или уточните имя.",
        )

    try:
        # Opening an already-running app is idempotent.  Reusing the existing
        # process avoids a second cold UI startup and keeps repeated operator
        # turns inside the fast-path budget.
        process_names = _APP_PROCESS_NAMES.get(name.strip().lower(), [])
        resolved_name = Path(cmd).name if cmd and ":" not in cmd else ""
        candidates = [*process_names, resolved_name]
        existing_pids = _process_ids_for_names(candidates)
        if existing_pids:
            return ActionResult(
                tool="open_app",
                args={"name": name, "args": args},
                ok=True,
                output=f"{name} уже запущен (pid={existing_pids[0]}).",
            )
        # URI-схемы (ms-settings:) запускаем через start
        if ":" in cmd and not os.path.isabs(cmd):
            if args.strip():
                return ActionResult(tool="open_app", args={"name": name, "args": args}, ok=False,
                                    error="URI-запуск с аргументами требует отдельного подтверждённого провайдера")
            if hasattr(os, "startfile"):
                os.startfile(cmd)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", cmd], shell=False)
            else:
                subprocess.Popen(["xdg-open", cmd], shell=False)
        else:
            # Обычный исполняемый файл.
            # ВАЖНО: shlex.split() в POSIX-режиме съедает обратные слэши
            # Windows ('C:\Windows\notepad.exe' -> 'C:Windowsnotepad.exe'),
            # поэтому путь передаём как есть, а разбираем только доп. аргументы.
            cmd_parts = [cmd]
            if args:
                cmd_parts.extend(shlex.split(args, posix=False))
            process = subprocess.Popen(cmd_parts, shell=False)
        log.debug("Запущено приложение: %s (cmd=%s)", name, cmd)
        pid_suffix = f" (pid={process.pid})" if "process" in locals() else ""
        return ActionResult(
            tool="open_app",
            args={"name": name, "args": args},
            ok=True,
            output=f"Запустил {name}{pid_suffix}.",
        )
    except Exception as exc:
        log.error("Ошибка запуска '%s': %s", name, exc)
        return ActionResult(
            tool="open_app",
            args={"name": name, "args": args},
            ok=False,
            error=f"Не удалось запустить '{name}': {exc}",
        )


def _process_name_matches(names: List[str]) -> bool:
    """Cheap process-presence probe used by the idempotent app launcher."""
    return bool(_process_ids_for_names(names))


def _process_ids_for_names(names: List[str]) -> List[int]:
    """Return matching PIDs in one bounded process snapshot."""
    wanted = {str(item).casefold() for item in names if item}
    found: List[int] = []
    if not wanted:
        return found
    try:
        for proc in psutil.process_iter(["pid", "name"]):
            pname = str(proc.info.get("name") or "").casefold()
            if pname and any(pname == name or pname == f"{name}.exe" or name in pname for name in wanted):
                found.append(int(proc.info.get("pid") or proc.pid))
    except Exception:
        return found
    return found


def close_app(name: str, settings: Optional[Settings] = None) -> ActionResult:
    """Закрывает приложение по имени процесса (через psutil).

    Args:
        name: разговорное имя приложения.
        settings: конфигурация (не используется напрямую, но для единообразия).

    Returns:
        ActionResult с ok=True, если хотя бы один процесс закрыт.
    """
    key = name.strip().lower()
    process_names = _APP_PROCESS_NAMES.get(key, [key + ".exe" if not key.endswith(".exe") else key])

    closed = 0
    errors: List[str] = []
    for proc_name in process_names:
        try:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    if proc.info["name"] and proc.info["name"].lower() == proc_name.lower():
                        proc.terminate()
                        closed += 1
                        log.info("Завершён процесс: %s (pid=%d)", proc_name, proc.info["pid"])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as exc:
            errors.append(f"{proc_name}: {exc}")

    if closed > 0:
        return ActionResult(
            tool="close_app",
            args={"name": name},
            ok=True,
            output=f"Закрыто процессов: {closed}.",
        )
    else:
        err_msg = "; ".join(errors) if errors else "процессы не найдены"
        return ActionResult(
            tool="close_app",
            args={"name": name},
            ok=False,
            error=f"Не удалось закрыть '{name}': {err_msg}",
        )


# --------------------------------------------------------------------------- #
# Tool-обёртки
# --------------------------------------------------------------------------- #


class OpenAppTool(Tool):
    """Инструмент: открыть приложение."""

    @property
    def name(self) -> str:
        return "open_app"

    @property
    def description(self) -> str:
        return (
            "Открывает Windows-приложение по разговорному имени. "
            "Поддерживает: блокнот, калькулятор, браузер (chrome/firefox/edge), "
            "word, excel, powerpoint, vscode, telegram, discord, vlc и др. "
            "Полный список — в документации. Можно добавить свои через настройки."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Разговорное имя приложения (например, 'блокнот', 'хром', 'word').",
                },
                "args": {
                    "type": "string",
                    "description": "Дополнительные аргументы командной строки (опционально).",
                    "default": "",
                },
            },
            "required": ["name"],
            "additionalProperties": False,
        }

    def run(self, args: Dict[str, Any], context: ToolContext) -> ActionResult:
        return open_app(args["name"], context.settings, args.get("args", ""))


class CloseAppTool(Tool):
    """Инструмент: закрыть приложение."""

    @property
    def name(self) -> str:
        return "close_app"

    @property
    def description(self) -> str:
        return (
            "Закрывает запущенное Windows-приложение по имени. "
            "Находит процессы через psutil и отправляет terminate()."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Разговорное имя приложения для закрытия.",
                },
            },
            "required": ["name"],
            "additionalProperties": False,
        }

    def run(self, args: Dict[str, Any], context: ToolContext) -> ActionResult:
        return close_app(args["name"], context.settings)


# Авто-регистрация при импорте
DEFAULT_REGISTRY.register(OpenAppTool())
DEFAULT_REGISTRY.register(CloseAppTool())
