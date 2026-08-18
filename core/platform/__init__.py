"""Replaceable platform providers used by the Capability Engine."""
from .browser import BrowserAutomationProvider, DOMSelector
from .browser_bridge import (
    BrowserActionResult, BrowserBridge, BrowserBridgeError, BrowserPolicy,
    BrowserSession, ConfirmationGrant, FindResult, PolicyDecision,
    canonical_selector_fingerprint, canonical_selector_value,
)
from .windows import (
    NativeWindowsProvider, ProviderChain, ProviderResult, UIAutomationProvider,
    VisionFallbackProvider, WinAppProvider, WindowsAutomationProvider,
    WindowsCapabilityLayer,
)

__all__ = [
    "BrowserAutomationProvider", "DOMSelector", "BrowserActionResult", "BrowserBridge",
    "BrowserBridgeError", "BrowserPolicy", "BrowserSession", "ConfirmationGrant",
    "FindResult", "PolicyDecision", "canonical_selector_fingerprint",
    "canonical_selector_value", "NativeWindowsProvider", "ProviderChain",
    "ProviderResult", "UIAutomationProvider", "VisionFallbackProvider",
    "WinAppProvider", "WindowsAutomationProvider", "WindowsCapabilityLayer",
]
