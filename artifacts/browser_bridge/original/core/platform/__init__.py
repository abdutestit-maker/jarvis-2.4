"""Replaceable platform providers used by the Capability Engine."""
from .browser import BrowserAutomationProvider, DOMSelector
from .windows import (
    NativeWindowsProvider, ProviderChain, ProviderResult, UIAutomationProvider,
    VisionFallbackProvider, WinAppProvider, WindowsAutomationProvider,
    WindowsCapabilityLayer,
)

__all__ = [
    "BrowserAutomationProvider", "DOMSelector", "NativeWindowsProvider", "ProviderChain",
    "ProviderResult", "UIAutomationProvider", "VisionFallbackProvider",
    "WinAppProvider", "WindowsAutomationProvider", "WindowsCapabilityLayer",
]
