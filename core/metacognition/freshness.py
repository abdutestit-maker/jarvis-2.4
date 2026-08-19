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
        # Generic cached version claims stay strict; concrete local
        # observations use ``for_observation`` below for the offline-restart
        # grace period.
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

    def for_observation(self, key: str, observed_at: datetime, *, source: str = "") -> Freshness:
        """Choose freshness for a concrete, provenance-bearing observation.

        The generic policy keeps version claims volatile for one day.  A
        verified local registry observation is a stronger boundary: it stays
        usable across a normal offline restart for seven days, while remaining
        volatile and eligible for re-observation.  This prevents a verified
        local fact from becoming unusable solely because the laptop was
        reopened two days later.
        """
        freshness = self.for_key(key, observed_at)
        value = (key or "").casefold()
        if source == "local_system" and any(
            marker in value for marker in ("software.version", "app.version", "installed.version")
        ):
            return Freshness.volatile(observed_at, ttl_seconds=604_800)
        return freshness


__all__ = ["FreshnessPolicy"]
