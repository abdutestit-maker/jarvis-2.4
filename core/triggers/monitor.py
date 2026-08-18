"""Best-effort OS sampler for configured system triggers."""
from __future__ import annotations
import threading
import time
from datetime import datetime
from typing import Callable
from .engine import SystemTriggerEngine, TriggerContext

class SystemMonitor:
    def __init__(self, engine: SystemTriggerEngine, interval: float = 60.0) -> None:
        self.engine, self.interval = engine, interval
        self._stop = threading.Event(); self._thread: threading.Thread | None = None
    def start(self) -> None:
        if self._thread and self._thread.is_alive(): return
        self._stop.clear(); self._thread = threading.Thread(target=self._run, daemon=False, name="jarvis-system-triggers"); self._thread.start()
    def stop(self) -> None:
        self._stop.set()
        if self._thread: self._thread.join(timeout=2)
    def join(self, timeout: float | None = None) -> bool:
        if self._thread and self._thread.is_alive(): self._thread.join(timeout=timeout)
        return bool(self._thread is None or not self._thread.is_alive())
    def sample(self) -> TriggerContext:
        processes: set[str] = set()
        try:
            import psutil  # type: ignore
            processes = {str(p.info.get("name", "")).lower() for p in psutil.process_iter(["name"]) if p.info.get("name")}
        except Exception: pass
        window = ""
        try:
            import pygetwindow  # type: ignore
            window = str(getattr(pygetwindow.getActiveWindow(), "title", "") or "")
        except Exception: pass
        return TriggerContext(active_window=window, active_processes=processes, now=datetime.now())
    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            try: self.engine.check(self.sample())
            except Exception: pass
