"""Canonical ATLAS runtime identity with explicit compatibility aliases."""

from __future__ import annotations

from dataclasses import dataclass


def _normalize(value: str) -> str:
    return " ".join((value or "").casefold().replace("ё", "е").split())


@dataclass(frozen=True)
class AtlasIdentityCore:
    canonical_name: str = "ATLAS"
    canonical_name_ru: str = "АТЛАС"
    internal_role: str = "digital intelligence"
    internal_concept: str = "one continuous digital mind"
    public_description: str = "intelligent assistant"
    compatibility_aliases: tuple[str, ...] = ("JARVIS", "ДЖАРВИС", "Джарвис")

    @property
    def address_roots(self) -> tuple[str, ...]:
        return ("атлас", "atlas")

    def matches_legacy(self, value: str) -> bool:
        candidate = _normalize(value)
        return candidate in {_normalize(alias) for alias in self.compatibility_aliases}


__all__ = ["AtlasIdentityCore"]

