"""Shared lifecycle primitives for local background services."""
from __future__ import annotations

import threading
from typing import Optional


class Lifecycle:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._stopped = threading.Event()
        self._stopped.set()

    def start(self) -> None:
        self._stop.clear()
        self._stopped.clear()

    def request_stop(self) -> None:
        self._stop.set()

    def wait_stop(self, timeout: Optional[float] = None) -> bool:
        return self._stop.wait(timeout)

    @property
    def stop_event(self) -> threading.Event:
        return self._stop

    @property
    def stopped(self) -> threading.Event:
        return self._stopped

    def mark_stopped(self) -> None:
        self._stopped.set()

