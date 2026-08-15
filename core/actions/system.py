"""Системные инструменты (Windows): громкость, статус системы.

Инструменты:
- ``VolumeTool`` — управление громкостью (up/down/mute).
- ``SystemStatusTool`` — CPU%, RAM%, диск, батарея.

Громкость: пытаемся использовать ``pycaw`` (Windows Core Audio API).
Фоллбэк: клавиши мультимедиа через ``pyautogui``.
Если ничего не доступно — возвращаем ok=False с понятной ошибкой.
"""

from __future__ import annotations

import platform
from typing import Any, Dict, List, Optional

import psutil

from config.settings import Settings
from core.actions.base import ActionResult, Tool, ToolContext
from core.actions.registry import DEFAULT_REGISTRY
from core.utils.logger import get_logger

__all__ = [
    "increase_volume",
    "decrease_volume",
    "mute_volume",
    "system_status",
    "VolumeTool",
    "SystemStatusTool",
]

log = get_logger(__name__)

# Пытаемся импортировать pycaw для точного управления громкостью
_PYCAW_AVAILABLE = False
try:
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    _PYCAW_AVAILABLE = True
except Exception:
    _PYCAW_AVAILABLE = False
    log.debug("pycaw недоступен — управление громкостью через фоллбэк (pyautogui)")

# Пытаемся импортировать pyautogui для фоллбэка
_PYAUTOGUI_AVAILABLE = False
try:
    import pyautogui

    _PYAUTOGUI_AVAILABLE = True
except Exception:
    log.debug("pyautogui недоступен — фоллбэк громкости отключён")


def _get_volume_interface():
    """Возвращает IAudioEndpointVolume для default playback device."""
    if not _PYCAW_AVAILABLE:
        return None
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return interface.QueryInterface(IAudioEndpointVolume)
    except Exception as exc:
        log.warning("Не удалось получить аудио-интерфейс: %s", exc)
        return None


def increase_volume(step: int = 10) -> ActionResult:
    """Увеличивает громкость на ``step`` процентов (0-100)."""
    return _adjust_volume(step)


def decrease_volume(step: int = 10) -> ActionResult:
    """Уменьшает громкость на ``step`` процентов."""
    return _adjust_volume(-step)


def mute_volume() -> ActionResult:
    """Переключает mute (вкл/выкл)."""
    if _PYCAW_AVAILABLE:
        vol = _get_volume_interface()
        if vol:
            try:
                current_mute = vol.GetMute()
                vol.SetMute(not current_mute, None)
                state = "включён" if not current_mute else "выключен"
                return ActionResult(
                    tool="mute_volume",
                    args={},
                    ok=True,
                    output=f"Mute {state}.",
                )
            except Exception as exc:
                log.error("Ошибка переключения mute через pycaw: %s", exc)

    # Фоллбэк: клавиша mute
    if _PYAUTOGUI_AVAILABLE:
        try:
            import pyautogui
            pyautogui.press("volumemute")
            return ActionResult(
                tool="mute_volume",
                args={},
                ok=True,
                output="Mute переключён (клавиша).",
            )
        except Exception as exc:
            log.error("Ошибка pyautogui volumemute: %s", exc)

    return ActionResult(
        tool="mute_volume",
        args={},
        ok=False,
        error="Управление громкостью недоступно (нет pycaw/pyautogui)",
    )


def _adjust_volume(delta_percent: int) -> ActionResult:
    """Внутренняя: изменяет громкость на delta_percent (+ или -)."""
    if _PYCAW_AVAILABLE:
        vol = _get_volume_interface()
        if vol:
            try:
                current = vol.GetMasterVolumeLevelScalar()  # 0.0 - 1.0
                new_level = max(0.0, min(1.0, current + delta_percent / 100.0))
                vol.SetMasterVolumeLevelScalar(new_level, None)
                return ActionResult(
                    tool="adjust_volume",
                    args={"delta_percent": delta_percent},
                    ok=True,
                    output=f"Громкость: {int(new_level * 100)}%.",
                )
            except Exception as exc:
                log.error("Ошибка изменения громкости через pycaw: %s", exc)

    # Фоллбэк: клавиши volumeup/volumedown
    if _PYAUTOGUI_AVAILABLE:
        try:
            import pyautogui
            key = "volumeup" if delta_percent > 0 else "volumedown"
            presses = max(1, abs(delta_percent) // 5)  # ~5% на нажатие
            for _ in range(presses):
                pyautogui.press(key)
            direction = "увеличена" if delta_percent > 0 else "уменьшена"
            return ActionResult(
                tool="adjust_volume",
                args={"delta_percent": delta_percent},
                ok=True,
                output=f"Громкость {direction} (клавиши, ~{presses * 5}%).",
            )
        except Exception as exc:
            log.error("Ошибка pyautogui volume keys: %s", exc)

    return ActionResult(
        tool="adjust_volume",
        args={"delta_percent": delta_percent},
        ok=False,
        error="Управление громкостью недоступно (нет pycaw/pyautogui)",
    )


def system_status() -> Dict[str, Any]:
    """Собирает статус системы: CPU, RAM, диск, батарея."""
    status: Dict[str, Any] = {}

    # CPU
    try:
        status["cpu_percent"] = psutil.cpu_percent(interval=0.1)
        status["cpu_count"] = psutil.cpu_count(logical=True)
        status["cpu_freq_mhz"] = (
            int(psutil.cpu_freq().current) if psutil.cpu_freq() else None
        )
    except Exception as exc:
        status["cpu_error"] = str(exc)

    # RAM
    try:
        mem = psutil.virtual_memory()
        status["ram"] = {
            "total_gb": round(mem.total / (1024**3), 1),
            "available_gb": round(mem.available / (1024**3), 1),
            "used_percent": mem.percent,
        }
    except Exception as exc:
        status["ram_error"] = str(exc)

    # Диск (системный раздел)
    try:
        system_drive = os.environ.get("SystemDrive", "C:") + "\\"
        disk = psutil.disk_usage(system_drive)
        status["disk"] = {
            "path": system_drive,
            "total_gb": round(disk.total / (1024**3), 1),
            "free_gb": round(disk.free / (1024**3), 1),
            "used_percent": round(disk.used / disk.total * 100, 1),
        }
    except Exception as exc:
        status["disk_error"] = str(exc)

    # Батарея (если ноутбук)
    try:
        battery = psutil.sensors_battery()
        if battery:
            status["battery"] = {
                "percent": battery.percent,
                "plugged": battery.power_plugged,
                "time_left_min": (
                    int(battery.secsleft / 60) if battery.secsleft not in (psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN) else None
                ),
            }
        else:
            status["battery"] = "не обнаружена (стационарный ПК)"
    except Exception as exc:
        status["battery_error"] = str(exc)

    # OS info
    status["os"] = {
        "platform": platform.platform(),
        "version": platform.version(),
        "python": platform.python_version(),
    }

    return status


# --------------------------------------------------------------------------- #
# Tool-обёртки
# --------------------------------------------------------------------------- #


class VolumeTool(Tool):
    """Инструмент: управление громкостью (up/down/mute)."""

    @property
    def name(self) -> str:
        return "volume"

    @property
    def description(self) -> str:
        return (
            "Управляет громкостью системы: увеличить, уменьшить, mute. "
            "Использует Windows Core Audio API (pycaw) или фоллбэк через клавиши мультимедиа."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["up", "down", "mute"],
                    "description": "Действие: up — повысить, down — понизить, mute — переключить mute.",
                },
                "step": {
                    "type": "integer",
                    "description": "Шаг изменения в процентах (для up/down).",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        }

    def run(self, args: Dict[str, Any], context: ToolContext) -> ActionResult:
        action = args["action"]
        step = args.get("step", 10)

        if action == "up":
            return increase_volume(step)
        elif action == "down":
            return decrease_volume(step)
        elif action == "mute":
            return mute_volume()
        else:
            return ActionResult(
                tool=self.name,
                args=args,
                ok=False,
                error=f"Неизвестное действие: {action}. Доступно: up, down, mute",
            )


class SystemStatusTool(Tool):
    """Инструмент: статус системы (CPU, RAM, диск, батарея)."""

    @property
    def name(self) -> str:
        return "system_status"

    @property
    def description(self) -> str:
        return (
            "Возвращает текущее состояние системы: загрузка CPU, использование RAM, "
            "свободное место на диске, уровень батареи (если ноутбук)."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }

    def run(self, args: Dict[str, Any], context: ToolContext) -> ActionResult:
        status = system_status()
        # Формируем краткую сводку для пользователя
        parts = []
        if "cpu_percent" in status:
            parts.append(f"CPU: {status['cpu_percent']}%")
        if "ram" in status:
            ram = status["ram"]
            parts.append(f"RAM: {ram['used_percent']}% ({ram['available_gb']} ГБ свободно)")
        if "disk" in status:
            disk = status["disk"]
            parts.append(f"Диск {disk['path']}: {disk['used_percent']}% занято ({disk['free_gb']} ГБ свободно)")
        if "battery" in status and isinstance(status["battery"], dict):
            bat = status["battery"]
            plugged = " (зарядка)" if bat.get("plugged") else ""
            parts.append(f"Батарея: {bat['percent']}%{plugged}")

        summary = "; ".join(parts) if parts else "Статус получен (детали в output)"

        return ActionResult(
            tool=self.name,
            args=args,
            ok=True,
            output=summary,
            # Полный статус кладём в output как структуру для LLM
        )


# Авто-регистрация
DEFAULT_REGISTRY.register(VolumeTool())
DEFAULT_REGISTRY.register(SystemStatusTool())

# Импорт os для system_drive
import os