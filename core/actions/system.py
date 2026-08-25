"""Системные инструменты (Windows): громкость, статус системы.

Инструменты:
- ``VolumeTool`` — управление громкостью (up/down/mute).
- ``SystemStatusTool`` — CPU%, RAM%, диск, батарея.

Громкость: пытаемся использовать ``pycaw`` (Windows Core Audio API).
Фоллбэк: клавиши мультимедиа через ``pyautogui``.
Если ничего не доступно — возвращаем ok=False с понятной ошибкой.
"""

from __future__ import annotations

import os
import platform
from typing import Any, Dict, List, Optional

import psutil

from config.settings import Settings
from core.actions.base import ActionResult, Tool, ToolContext
from core.actions.registry import DEFAULT_REGISTRY
from core.executive.world import DomainObservation, LocalWorldObserver
from core.utils.logger import get_logger

__all__ = [
    "increase_volume",
    "decrease_volume",
    "mute_volume",
    "system_status",
    "get_machine_state",
    "get_storage_state",
    "list_drives",
    "list_processes",
    "list_windows",
    "get_active_window",
    "list_installed_apps",
    "VolumeTool",
    "SystemStatusTool",
]

log = get_logger(__name__)
_WORLD_OBSERVER = LocalWorldObserver()

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


def get_machine_state() -> DomainObservation:
    return _WORLD_OBSERVER.observe("machine")


def get_storage_state() -> DomainObservation:
    return _WORLD_OBSERVER.observe("storage")


def list_drives() -> List[Dict[str, Any]]:
    observation = get_storage_state()
    return list(observation.data.get("volumes", [])) if observation.ok else []


def list_processes(limit: int = 128) -> DomainObservation:
    return _WORLD_OBSERVER.observe("processes", limit=limit)


def list_windows(limit: int = 64) -> DomainObservation:
    return _WORLD_OBSERVER.observe("desktop", limit=limit)


def get_active_window() -> Dict[str, Any]:
    observation = list_windows(limit=64)
    return dict(observation.data.get("active_window", {})) if observation.ok else {}


def list_installed_apps(limit: int = 256) -> DomainObservation:
    return _WORLD_OBSERVER.observe("applications", limit=limit)


def system_status() -> Dict[str, Any]:
    """Compatibility summary backed by canonical current-world observations."""
    machine = get_machine_state()
    storage = get_storage_state()
    status: Dict[str, Any] = {
        "observed_at": max(machine.observed_at, storage.observed_at).isoformat(),
        "source": [machine.source, storage.source],
        "freshness": "fresh",
        "fact_type": "observed",
        "evidence": [*machine.evidence, *storage.evidence],
        "errors": [item.error for item in (machine, storage) if item.error],
    }
    if machine.ok:
        data = machine.data
        status["cpu_percent"] = data["cpu"]["used_percent"]
        status["cpu_count"] = data["cpu"]["logical_count"]
        status["cpu_freq_mhz"] = data["cpu"]["frequency_mhz"]
        memory = data["memory"]
        status["ram"] = {
            "total_gb": round(memory["total_bytes"] / (1024**3), 1),
            "available_gb": round(memory["available_bytes"] / (1024**3), 1),
            "used_percent": memory["used_percent"],
        }
        status["battery"] = data["battery"] or "не обнаружена (стационарный ПК)"
        status["os"] = {
            "platform": platform.platform(), "version": platform.version(),
            "python": platform.python_version(), "hostname": data["hostname"],
        }
    if storage.ok:
        status["volumes"] = storage.data["volumes"]
        if status["volumes"]:
            first = status["volumes"][0]
            status["disk"] = {
                "path": first["mountpoint"],
                "total_gb": round(first["total_bytes"] / (1024**3), 1),
                "free_gb": round(first["free_bytes"] / (1024**3), 1),
                "used_percent": first["used_percent"],
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
            ok=not bool(status.get("errors")),
            output={"summary": summary, **status},
            error="; ".join(str(item) for item in status.get("errors", [])) or None,
        )


# Авто-регистрация
DEFAULT_REGISTRY.register(VolumeTool())
DEFAULT_REGISTRY.register(SystemStatusTool())
