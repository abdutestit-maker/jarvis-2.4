"""Provider protocol owned by Brain Fabric rather than concrete vendors."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from .models import BrainRequest, BrainResult, HealthSnapshot, ModelCapabilityProfile


class BrainProvider(ABC):
    name: str
    external: bool = True

    @abstractmethod
    def health(self) -> HealthSnapshot: ...

    @abstractmethod
    def models(self) -> tuple[str, ...]: ...

    @abstractmethod
    def generate(self, request: BrainRequest, *, model: str | None = None) -> BrainResult: ...

    @abstractmethod
    def stream(self, request: BrainRequest, *, model: str | None = None) -> Iterator[str]: ...

    @abstractmethod
    def cancel(self, request_id: str | None = None) -> bool: ...

    @abstractmethod
    def capabilities(self, model: str) -> ModelCapabilityProfile: ...

    def close(self) -> None:
        return None


__all__ = ["BrainProvider"]

