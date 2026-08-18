"""Wake-word foundation; real detector intentionally deferred and disabled."""
from __future__ import annotations
from typing import Callable

class WakeWordDetector:
    def __init__(self, *, enabled: bool = False, phrase: str = "ATLAS", sensitivity: float = 0.5, on_detected: Callable[[], None] | None = None) -> None:
        self.enabled = enabled
        self.phrase = phrase
        self.sensitivity = sensitivity
        self.on_detected = on_detected
    def start(self) -> None: return None
    def stop(self) -> None: return None
    @property
    def available(self) -> bool: return False

class NoOpWakeWord(WakeWordDetector):
    pass
