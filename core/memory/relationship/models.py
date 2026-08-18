"""Serializable relationship-memory records and hierarchy results."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RelationshipMemory:
    id: str
    fact: str
    source: str
    confidence: float
    last_confirmed: str
    importance: float
    category: str = "preference"
    key: str = ""
    created_at: str = ""
    expires_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RelationshipMemory":
        return cls(
            id=str(value.get("id") or ""), fact=str(value.get("fact") or ""),
            source=str(value.get("source") or "unknown"),
            confidence=float(value.get("confidence", 0)),
            last_confirmed=str(value.get("last_confirmed") or ""),
            importance=float(value.get("importance", 0)),
            category=str(value.get("category") or "preference"),
            key=str(value.get("key") or ""), created_at=str(value.get("created_at") or ""),
            expires_at=str(value.get("expires_at") or ""),
        )


@dataclass
class MemoryContext:
    working: dict[str, Any] = field(default_factory=dict)
    session: list[dict[str, str]] = field(default_factory=list)
    long_term: list[str] = field(default_factory=list)
    relationship: list[RelationshipMemory] = field(default_factory=list)

    def to_prompt(self, max_chars: int = 1200) -> str:
        parts: list[str] = []
        if self.working:
            compact = ", ".join(f"{key}={value}" for key, value in self.working.items())
            parts.append(f"Working: {compact}")
        if self.session:
            recent = " | ".join(f"{item.get('role')}: {item.get('content')}" for item in self.session[-4:])
            parts.append(f"Session: {recent}")
        if self.long_term:
            parts.append("Long term: " + " | ".join(self.long_term[:3]))
        if self.relationship:
            parts.append("Relationship: " + " | ".join(item.fact for item in self.relationship[:4]))
        return "\n".join(parts)[:max(0, int(max_chars))]

