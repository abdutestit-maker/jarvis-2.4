"""Уведомления (Windows toast / fallback).

``show_toast`` — показывает системное уведомление.
Пробует: win10toast -> plyer -> fallback на print/log.
"""

from __future__ import annotations

from typing import Optional

from core.utils.logger import get_logger

__all__ = ["show_toast", "NotificationBackend"]

log = get_logger(__name__)


class NotificationBackend:
    """Абстракция бэкенда уведомлений."""

    def show(self, title: str, message: str, duration: int = 5) -> bool:
        raise NotImplementedError


class Win10ToastBackend(NotificationBackend):
    """win10toast (Windows 10/11 нативные тосты)."""

    def __init__(self) -> None:
        try:
            from win10toast import ToastNotifier
            self._toaster = ToastNotifier()
            self._available = True
        except Exception as exc:
            log.debug("win10toast недоступен: %s", exc)
            self._available = False
            self._toaster = None

    def is_available(self) -> bool:
        return self._available

    def show(self, title: str, message: str, duration: int = 5) -> bool:
        if not self._available:
            return False
        try:
            self._toaster.show_toast(title, message, duration=duration, threaded=True)
            return True
        except Exception as exc:
            log.warning("win10toast.show ошибка: %s", exc)
            return False


class PlyerBackend(NotificationBackend):
    """plyer (кросс-платформенный, на Windows использует win10toast/winrt)."""

    def __init__(self) -> None:
        try:
            from plyer import notification
            self._notification = notification
            self._available = True
        except Exception as exc:
            log.debug("plyer недоступен: %s", exc)
            self._available = False
            self._notification = None

    def is_available(self) -> bool:
        return self._available

    def show(self, title: str, message: str, duration: int = 5) -> bool:
        if not self._available:
            return False
        try:
            self._notification.notify(
                title=title,
                message=message,
                timeout=duration,
            )
            return True
        except Exception as exc:
            log.warning("plyer.notify ошибка: %s", exc)
            return False


class PrintBackend(NotificationBackend):
    """Фоллбэк: вывод в консоль/лог."""

    def is_available(self) -> bool:
        return True

    def show(self, title: str, message: str, duration: int = 5) -> bool:
        log.info("УВЕДОМЛЕНИЕ: %s — %s", title, message)
        print(f"🔔 [{title}] {message}")
        return True


# Порядок попыток
_BACKENDS = [
    Win10ToastBackend(),
    PlyerBackend(),
    PrintBackend(),  # всегда последний, всегда работает
]


def show_toast(title: str, message: str, duration: int = 5) -> bool:
    """Показывает уведомление (пробует бэкенды по очереди).

    Args:
        title: заголовок уведомления.
        message: текст сообщения.
        duration: время показа в секундах.

    Returns:
        True — уведомление показано, False — все бэкенды упали.
    """
    if not title or not message:
        log.debug("show_toast: пустой заголовок или сообщение")
        return False

    for backend in _BACKENDS:
        if backend.is_available():
            try:
                if backend.show(title, message, duration):
                    log.debug("Уведомление показано через %s", type(backend).__name__)
                    return True
            except Exception as exc:
                log.warning("Бэкенд %s упал: %s", type(backend).__name__, exc)
                continue

    log.error("Все бэкенды уведомлений недоступны")
    return False