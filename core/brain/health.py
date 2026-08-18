"""Fast provider health accounting and bounded circuit breaking."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from .models import HealthSnapshot, HealthStatus


@dataclass
class _State:
    status: HealthStatus = HealthStatus.AVAILABLE
    latency_ms: float | None = None
    failures: int = 0
    consecutive_failures: int = 0
    timeouts: int = 0
    recent_success: bool = False
    last_error: str = ""
    opened_at: float = 0.0


class BrainHealthManager:
    def __init__(self, *, failure_threshold: int = 2, cooldown_seconds: float = 10.0) -> None:
        self.failure_threshold = max(1, int(failure_threshold))
        self.cooldown_seconds = max(0.0, float(cooldown_seconds))
        self._states: dict[str, _State] = {}
        self._lock = threading.RLock()

    def _state(self, key: str) -> _State:
        return self._states.setdefault(key, _State())

    def record_success(self, key: str, *, latency_ms: float) -> None:
        with self._lock:
            state = self._state(key)
            state.status = HealthStatus.AVAILABLE
            state.latency_ms = float(latency_ms)
            state.consecutive_failures = 0
            state.recent_success = True
            state.last_error = ""
            state.opened_at = 0.0

    def record_failure(self, key: str, *, latency_ms: float | None = None,
                       timeout: bool = False, error: str = "") -> None:
        with self._lock:
            state = self._state(key)
            state.failures += 1
            state.consecutive_failures += 1
            state.timeouts += int(timeout)
            state.recent_success = False
            state.latency_ms = latency_ms
            state.last_error = str(error)[:240]
            if state.consecutive_failures >= self.failure_threshold:
                state.status = HealthStatus.UNHEALTHY
                state.opened_at = time.monotonic()
            else:
                state.status = HealthStatus.DEGRADED

    def allow(self, key: str) -> bool:
        with self._lock:
            state = self._state(key)
            if state.status is not HealthStatus.UNHEALTHY:
                return state.status is not HealthStatus.OFFLINE
            if time.monotonic() - state.opened_at >= self.cooldown_seconds:
                state.status = HealthStatus.DEGRADED
                return True
            return False

    def force_retry(self, key: str) -> None:
        with self._lock:
            state = self._state(key)
            state.status = HealthStatus.DEGRADED
            state.opened_at = 0.0

    def set_status(self, key: str, status: HealthStatus) -> None:
        with self._lock:
            self._state(key).status = status

    def snapshot(self, key: str) -> HealthSnapshot:
        with self._lock:
            state = self._state(key)
            return HealthSnapshot(
                status=state.status, latency_ms=state.latency_ms,
                failures=state.failures, timeouts=state.timeouts,
                recent_success=state.recent_success, last_error=state.last_error,
            )


__all__ = ["BrainHealthManager"]

