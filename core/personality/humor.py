"""Deterministic humor calibration; no random joke injection."""

from __future__ import annotations


class HumorPolicy:
    def __init__(self, base_level: float = 0.35) -> None:
        self.base_level = max(0.0, min(1.0, float(base_level)))

    def calibrate(self, *, task_type: str = "conversation", risk: str = "low",
                  is_error: bool = False, preference: float | None = None) -> float:
        if is_error or str(risk).casefold() not in {"", "none", "low"}:
            return 0.0
        base = self.base_level if preference is None else max(0.0, min(1.0, float(preference)))
        kind = str(task_type or "conversation").casefold()
        if kind in {"work", "report", "installation", "automation", "coding", "learning"}:
            return round(min(0.1, base * 0.2), 3)
        return round(min(0.45, base), 3)

