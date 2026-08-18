"""Explicit, local-only screen capture with optional OCR."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

@dataclass(frozen=True)
class ScreenCaptureResult:
    text: str
    active_window: str = ""
    url: str = ""

class ScreenCapture:
    def __init__(self, *, ocr_enabled: bool = True) -> None:
        self.ocr_enabled = ocr_enabled

    def capture(self, *, permission: bool = False) -> ScreenCaptureResult:
        if not permission:
            raise PermissionError("Screen capture requires explicit permission")
        try:
            import mss  # type: ignore
            with mss.mss() as monitor:
                image = monitor.grab(monitor.monitors[0])
        except Exception as exc:
            raise RuntimeError("Screen capture unavailable; install mss") from exc
        text = self._ocr(image) if self.ocr_enabled else ""
        return ScreenCaptureResult(text=text, active_window=self._active_window())

    def _ocr(self, image: Any) -> str:
        try:
            import pytesseract  # type: ignore
            return str(pytesseract.image_to_string(image)).strip()
        except Exception:
            return ""

    @staticmethod
    def _active_window() -> str:
        try:
            import pygetwindow  # type: ignore
            windows = pygetwindow.getActiveWindow()
            return str(getattr(windows, "title", "") or "")
        except Exception:
            return ""
