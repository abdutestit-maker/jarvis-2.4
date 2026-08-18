"""Replaceable platform providers used by the Capability Engine."""
from .browser import BrowserAutomationProvider
from .windows import (
    NativeWindowsProvider, ProviderChain, ProviderResult, UIAutomationProvider,
    VisionFallbackProvider, WinAppProvider, WindowsAutomationProvider,
    WindowsCapabilityLayer,
)

__all__ = [
    "BrowserAutomationProvider", "NativeWindowsProvider", "ProviderChain",
    "ProviderResult", "UIAutomationProvider", "VisionFallbackProvider",
    "WinAppProvider", "WindowsAutomationProvider", "WindowsCapabilityLayer",
]
