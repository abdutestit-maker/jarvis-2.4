"""Small live capability graph used by the CognitiveKernel."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable


@dataclass
class CapabilityManifest:
    name: str
    intent_families: tuple[str, ...] = ()
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    preconditions: tuple[str, ...] = ()
    postconditions: tuple[str, ...] = ()
    risk: str = "low"
    confirmation_policy: str = "policy"
    verification: tuple[str, ...] = ()
    rollback: tuple[str, ...] = ()
    reliability: float = 0.5
    executor: Any = field(default=None, repr=False, compare=False)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("executor", None)
        value["reliability"] = round(max(0.0, min(1.0, float(self.reliability))), 4)
        return value


class CapabilityGraph:
    """One deterministic lookup surface for tools and learned skills."""

    def __init__(self, manifests: Iterable[CapabilityManifest] | None = None) -> None:
        self._items: dict[str, CapabilityManifest] = {}
        for manifest in manifests or ():
            self.register(manifest)

    def register(self, manifest: CapabilityManifest) -> CapabilityManifest:
        if not manifest.name.strip():
            raise ValueError("capability name is required")
        self._items[manifest.name] = manifest
        return manifest

    def get(self, name: str) -> CapabilityManifest | None:
        return self._items.get(str(name or "").strip())

    def resolve(self, intent_family: str, *, name: str = "") -> list[CapabilityManifest]:
        if name:
            item = self.get(name)
            return [item] if item is not None else []
        family = str(intent_family or "").casefold()
        return sorted(
            [item for item in self._items.values() if family in {v.casefold() for v in item.intent_families}],
            key=lambda item: item.reliability,
            reverse=True,
        )

    def has_family(self, intent_family: str) -> bool:
        return bool(self.resolve(intent_family))

    def snapshot(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in sorted(self._items.values(), key=lambda value: value.name)]

    def __len__(self) -> int:
        return len(self._items)


__all__ = ["CapabilityGraph", "CapabilityManifest"]
