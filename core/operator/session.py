"""Foreground acquisition that restores the user's prior active window."""

from __future__ import annotations

import time
from enum import Enum
from typing import Any


class ForegroundClass(str, Enum):
    BACKGROUND_SAFE = "BACKGROUND_SAFE"
    FOREGROUND_REQUIRED = "FOREGROUND_REQUIRED"
    USER_REQUIRED = "USER_REQUIRED"


class ForegroundSession:
    def __init__(self, windows: Any, *, classification: ForegroundClass,
                 target_title: str = "", target_handle: int | None = None) -> None:
        self.windows = windows
        self.classification = classification
        self.target_title = target_title
        self.target_handle = target_handle
        self.previous: dict[str, Any] | None = None
        self.acquired = False
        self.restored = False
        self.started_at = 0.0
        self.duration = 0.0

    def __enter__(self) -> "ForegroundSession":
        self.started_at = time.monotonic()
        active = self.windows.window_active()
        if getattr(active, "ok", False):
            value = getattr(active, "value", None)
            self.previous = dict(value) if isinstance(value, dict) else {"title": str(value or "")}
        if self.classification is ForegroundClass.FOREGROUND_REQUIRED:
            kwargs = {"handle": self.target_handle} if self.target_handle else {"title": self.target_title}
            focused = self.windows.window_focus(**kwargs)
            self.acquired = bool(getattr(focused, "ok", False))
            if not self.acquired:
                raise RuntimeError(getattr(focused, "error", "foreground focus failed"))
        return self

    def __exit__(self, *_exc: Any) -> None:
        try:
            if self.acquired and self.previous:
                if self.previous.get("handle"):
                    result = self.windows.window_focus(handle=self.previous["handle"])
                else:
                    result = self.windows.window_focus(title=self.previous.get("title", ""))
                self.restored = bool(getattr(result, "ok", False))
        finally:
            self.duration = time.monotonic() - self.started_at

