"""Thread-safe runtime registry for hot-swappable providers."""
from __future__ import annotations

import threading
from dataclasses import dataclass

from .provider import BrainProvider


@dataclass(frozen=True)
class ProviderEntry:
    provider: BrainProvider
    priority: int
    order: int


class BrainProviderRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, ProviderEntry] = {}
        self._lock = threading.RLock()
        self._order = 0
        self.generation = 0

    def register(self, provider: BrainProvider, *, priority: int = 0) -> None:
        name = str(provider.name).strip()
        if not name:
            raise ValueError("provider name is required")
        with self._lock:
            self._order += 1
            self._entries[name] = ProviderEntry(provider, int(priority), self._order)
            self.generation += 1

    def remove(self, name: str, *, close: bool = True) -> BrainProvider | None:
        with self._lock:
            entry = self._entries.pop(name, None)
            if entry is not None:
                self.generation += 1
        if entry is not None and close:
            entry.provider.close()
        return entry.provider if entry else None

    def get(self, name: str) -> BrainProvider | None:
        with self._lock:
            entry = self._entries.get(name)
            return entry.provider if entry else None

    def providers(self) -> tuple[ProviderEntry, ...]:
        with self._lock:
            return tuple(sorted(
                self._entries.values(), key=lambda item: (-item.priority, item.order),
            ))

    def names(self) -> tuple[str, ...]:
        return tuple(entry.provider.name for entry in self.providers())

    def replace(self, providers: tuple[BrainProvider, ...] | list[BrainProvider]) -> None:
        incoming = {provider.name: provider for provider in providers}
        with self._lock:
            removed = [entry.provider for name, entry in self._entries.items() if name not in incoming]
            self._entries.clear()
            for provider in providers:
                self._order += 1
                self._entries[provider.name] = ProviderEntry(provider, 0, self._order)
            self.generation += 1
        for provider in removed:
            provider.close()

    def close(self) -> None:
        for entry in self.providers():
            entry.provider.close()


__all__ = ["BrainProviderRegistry", "ProviderEntry"]

