"""Low-overhead Windows context sampling without screenshots or key logging."""

from __future__ import annotations

import ctypes
import threading
from pathlib import Path
from typing import Any, Callable

from core.platform.windows import NativeWindowsProvider

from .context import LivingContextEngine
from .models import ContextObservation, CurrentContext


class WindowsContextSampler:
    """Collects only foreground-window metadata and coarse activity state.

    The sampler never captures pixels, clipboard contents or typed characters.
    Optional probes may contribute already-structured browser/application state.
    """

    _MEETING_APPS = {"teams", "zoom", "skype", "webex", "discord"}
    _MEDIA_APPS = {"vlc", "mpv", "spotify", "wmplayer", "foobar2000"}

    def __init__(
        self,
        *,
        provider: Any | None = None,
        process_lookup: Callable[[int], str] | None = None,
        idle_lookup: Callable[[], float] | None = None,
        fullscreen_lookup: Callable[[int | None], bool] | None = None,
        browser_probe: Callable[[], dict[str, Any]] | None = None,
        activity_probe: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self.provider = provider or NativeWindowsProvider()
        self.process_lookup = process_lookup or self._process_name
        self.idle_lookup = idle_lookup or self._idle_seconds
        self.fullscreen_lookup = fullscreen_lookup or self._is_fullscreen
        self.browser_probe = browser_probe
        self.activity_probe = activity_probe

    def sample(self) -> ContextObservation:
        active = self.provider.window_active()
        value = dict(active.value or {}) if getattr(active, "ok", False) else {}
        process_id = int(value.get("process_id") or 0)
        process = self.process_lookup(process_id) if process_id else ""
        stem = Path(process).stem
        application = stem.replace("_", " ").replace("-", " ").title()
        title = str(value.get("title") or "")
        handle = value.get("handle")
        browser = dict(self.browser_probe() or {}) if self.browser_probe else {}
        activity = dict(self.activity_probe() or {}) if self.activity_probe else {}
        process_key = stem.casefold()
        meeting = bool(activity.get("meeting_active")) or any(
            name in process_key for name in self._MEETING_APPS
        )
        media = bool(activity.get("media_active") or browser.get("media_active")) or any(
            name in process_key for name in self._MEDIA_APPS
        )
        return ContextObservation(
            source="native_windows_metadata",
            application=application,
            process=process,
            window_title=title,
            domain=str(browser.get("domain") or ""),
            page_title=str(browser.get("page_title") or ""),
            action="foreground_active" if title or process else "",
            idle_seconds=max(0.0, float(self.idle_lookup())),
            fullscreen=bool(self.fullscreen_lookup(int(handle) if handle else None)),
            media_active=media,
            meeting_active=meeting,
            typing_active=bool(activity.get("typing_active")),
            do_not_disturb=bool(activity.get("do_not_disturb")),
            active_mission=bool(activity.get("active_mission")),
            metadata={
                "provider": getattr(active, "provider", "native_windows"),
                "ui_focus_role": str(activity.get("ui_focus_role") or ""),
                "ui_role_counts": dict(activity.get("ui_role_counts") or {}),
            },
        )

    @staticmethod
    def _process_name(process_id: int) -> str:
        try:
            import psutil
            return str(psutil.Process(process_id).name())
        except Exception:
            return ""

    @staticmethod
    def _idle_seconds() -> float:
        try:
            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

            info = LASTINPUTINFO()
            info.cbSize = ctypes.sizeof(info)
            if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
                return 0.0
            elapsed_ms = (ctypes.windll.kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF
            return elapsed_ms / 1000.0
        except Exception:
            return 0.0

    @staticmethod
    def _is_fullscreen(handle: int | None) -> bool:
        if not handle:
            return False
        try:
            import win32api
            import win32gui

            left, top, right, bottom = win32gui.GetWindowRect(handle)
            monitor = win32api.MonitorFromWindow(handle, 2)
            monitor_rect = win32api.GetMonitorInfo(monitor)["Monitor"]
            return (left, top, right, bottom) == tuple(monitor_rect)
        except Exception:
            return False


class LivingContextMonitor:
    """Quiet daemon sampler whose one-shot ``tick`` is independently testable."""

    def __init__(self, engine: LivingContextEngine, *, sampler: Any | None = None,
                 interval_seconds: float = 2.0) -> None:
        self.engine = engine
        self.sampler = sampler or WindowsContextSampler()
        self.interval_seconds = max(0.05, float(interval_seconds))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def tick(self) -> CurrentContext:
        return self.engine.update(self.sampler.sample())

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="LivingContextMonitor", daemon=False,
        )
        self._thread.start()

    def stop(self, *, close_episode: bool = True) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=max(1.0, self.interval_seconds * 2))
        self._thread = None
        if close_episode:
            self.engine.close_episode(outcome="service_stopped")

    def join(self, timeout: float | None = None) -> bool:
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        return bool(self._thread is None or not self._thread.is_alive())

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:
                # Context collection is auxiliary and must never affect Active Mode.
                pass
            self._stop.wait(self.interval_seconds)


__all__ = ["LivingContextMonitor", "WindowsContextSampler"]
