"""Capability Graph built from the existing Tool/Capability registries."""

from __future__ import annotations

import threading
from typing import Any, Iterable, Optional

from .models import CapabilitySpec, normalize_tokens


class CapabilityGraph:
    def __init__(self, capability_registry: Any = None, tool_registry: Any = None) -> None:
        self._lock = threading.RLock()
        self._items: dict[str, CapabilitySpec] = {}
        if capability_registry is not None:
            source = capability_registry.all() if hasattr(capability_registry, "all") else getattr(capability_registry, "_items", {})
            values = source.values() if isinstance(source, dict) else source
            for item in values:
                self.register(self._from_capability(item))
        if tool_registry is not None:
            for tool in tool_registry.list_tools():
                if getattr(tool, "name", "") not in self._items:
                    self.register(CapabilitySpec(name=tool.name, tools=[tool.name], tags=[tool.name]))

    @staticmethod
    def _from_capability(item: Any) -> CapabilitySpec:
        risk = getattr(getattr(item, "risk_level", None), "value", getattr(item, "risk_level", "medium"))
        speed = getattr(getattr(item, "speed", None), "value", getattr(item, "speed", "fast"))
        latency = {"instant": 0.5, "fast": 3.0, "slow": 15.0}.get(speed)
        name = str(getattr(item, "name", ""))
        return CapabilitySpec(name=name, outputs=[str(getattr(item, "success_check", ""))] if getattr(item, "success_check", "") else [],
                             risk=str(risk), cost=str(getattr(item, "cost", "free")), reliability=0.8 if getattr(item, "success_check", "") else 0.5,
                             latency_sec=latency, tools=[name], tags=list(getattr(item, "tags", []) or []))

    def register(self, spec: CapabilitySpec) -> CapabilitySpec:
        if not spec.name:
            raise ValueError("capability name is required")
        with self._lock:
            self._items[spec.name] = spec
        return spec

    def get(self, name: str) -> Optional[CapabilitySpec]:
        return self._items.get(name)

    def all(self) -> list[CapabilitySpec]:
        return list(self._items.values())

    def find(self, query: str, *, limit: int = 5) -> list[CapabilitySpec]:
        tokens = normalize_tokens(query)
        scored = []
        for spec in self._items.values():
            haystack = normalize_tokens(" ".join([spec.name, *spec.tags, *spec.preconditions, *spec.postconditions]))
            score = len(tokens & haystack)
            if score:
                scored.append((score, spec.reliability, spec))
        scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
        return [spec for _, _, spec in scored[:max(1, int(limit))]]

    def compose(self, names: Iterable[str], *, goal: str = "") -> dict[str, Any]:
        selected = [self._items[name] for name in names if name in self._items]
        return {
            "goal": goal,
            "capabilities": [item.to_dict() for item in selected],
            "inputs": sorted({value for item in selected for value in item.inputs}),
            "outputs": sorted({value for item in selected for value in item.outputs}),
            "preconditions": sorted({value for item in selected for value in item.preconditions}),
            "postconditions": sorted({value for item in selected for value in item.postconditions}),
            "risk": "high" if any(item.risk in {"high", "critical"} for item in selected) else "low",
        }

