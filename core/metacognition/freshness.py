"""Domain-sensitive freshness semantics for volatile and stable knowledge."""

from __future__ import annotations

from datetime import datetime

from core.metacognition.models import Freshness


class FreshnessPolicy:
    _TTLS = (
        (("active.window", "current_app", "foreground"), 5),
        (("file.exists", "file.state"), 30),
        (("website", "site.state"), 300),
        (("system.setting", "setting"), 300),
        (("software.version", "app.version", "installed.version"), 86_400),
        (("preference", "relationship"), 15_552_000),
    )

    def for_key(self, key: str, observed_at: datetime) -> Freshness:
        value = (key or "").casefold()
        if any(marker in value for marker in ("identity", "canonical_name")):
            return Freshness.timeless(observed_at)
        for markers, ttl in self._TTLS:
            if any(marker in value for marker in markers):
                return Freshness.volatile(observed_at, ttl_seconds=ttl)
        return Freshness.stable(observed_at)


__all__ = ["FreshnessPolicy"]
