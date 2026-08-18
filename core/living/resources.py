"""Resource budgets, Shadow value ranking and capability quality feedback."""

from __future__ import annotations

import json
import math
import threading
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any
from core.security.atomic import atomic_json_write, load_json


class BackgroundMode(str, Enum):
    RUN = "RUN"
    THROTTLE = "THROTTLE"
    PAUSE = "PAUSE"


@dataclass(frozen=True)
class ResourceSnapshot:
    cpu_percent: float = 0.0
    gpu_percent: float = 0.0
    ram_percent: float = 0.0
    foreground_latency_ms: float = 0.0
    gaming: bool = False
    fullscreen: bool = False
    active_tts: bool = False
    active_user_mission: bool = False
    on_battery: bool = False
    battery_percent: float = 100.0


@dataclass(frozen=True)
class BackgroundDecision:
    mode: BackgroundMode
    load_score: float
    cpu_quota: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ShadowPriorityFactors:
    user_pain: float
    frequency: float
    time_saved: float
    reuse_probability: float
    risk: float
    learning_cost: float

    def score(self) -> float:
        values = [max(0.0, min(1.0, float(value))) for value in asdict(self).values()]
        pain, frequency, time_saved, reuse, risk, cost = values
        benefit = 0.28 * pain + 0.22 * frequency + 0.20 * time_saved + 0.20 * reuse
        penalty = 0.18 * risk + 0.12 * cost
        return round(max(0.0, min(1.0, benefit - penalty)), 3)


@dataclass(frozen=True)
class QualityResult:
    capability_id: str
    optimization_needed: bool
    priority: float
    evidence: tuple[str, ...]


class BackgroundBudgetManager:
    """Weighted saturation model protecting foreground responsiveness."""

    def assess(self, snapshot: ResourceSnapshot) -> BackgroundDecision:
        reasons: list[str] = []
        load = (
            0.23 * max(0.0, min(1.0, snapshot.cpu_percent / 100))
            + 0.17 * max(0.0, min(1.0, snapshot.gpu_percent / 100))
            + 0.18 * max(0.0, min(1.0, snapshot.ram_percent / 100))
            + 0.18 * max(0.0, min(1.0, snapshot.foreground_latency_ms / 250))
        )
        for name, weight in (
            ("gaming", 0.40), ("fullscreen", 0.18), ("active_tts", 0.35),
            ("active_user_mission", 0.35),
        ):
            if getattr(snapshot, name):
                load += weight
                reasons.append(name)
        if snapshot.on_battery:
            battery_pressure = max(0.0, min(1.0, (35 - snapshot.battery_percent) / 35))
            load += 0.45 * battery_pressure
            if battery_pressure > 0:
                reasons.append("battery conservation")
        load = max(0.0, min(1.0, load))
        if load >= 0.65:
            return BackgroundDecision(BackgroundMode.PAUSE, round(load, 3), 0.0, tuple(reasons))
        if load >= 0.38:
            return BackgroundDecision(BackgroundMode.THROTTLE, round(load, 3),
                                      round(max(0.05, (0.65 - load) * 0.5), 3), tuple(reasons))
        return BackgroundDecision(BackgroundMode.RUN, round(load, 3),
                                  round(max(0.1, 0.5 - load), 3), tuple(reasons))


class LocalResourceSampler:
    """Reads coarse local load metrics; it records no process contents."""

    def __init__(self, psutil_module: Any = None) -> None:
        if psutil_module is None:
            import psutil
            psutil_module = psutil
        self.psutil = psutil_module

    def sample(self, *, foreground_latency_ms: float = 0.0,
               gaming: bool = False, fullscreen: bool = False,
               active_tts: bool = False, active_user_mission: bool = False,
               gpu_percent: float = 0.0) -> ResourceSnapshot:
        battery = None
        try:
            battery = self.psutil.sensors_battery()
        except (AttributeError, OSError):
            pass
        return ResourceSnapshot(
            cpu_percent=float(self.psutil.cpu_percent(interval=None)),
            gpu_percent=max(0.0, float(gpu_percent)),
            ram_percent=float(self.psutil.virtual_memory().percent),
            foreground_latency_ms=max(0.0, float(foreground_latency_ms)),
            gaming=bool(gaming), fullscreen=bool(fullscreen),
            active_tts=bool(active_tts), active_user_mission=bool(active_user_mission),
            on_battery=bool(battery and not battery.power_plugged),
            battery_percent=float(battery.percent if battery else 100.0),
        )


class CapabilityQualityLoop:
    def __init__(self, directory: Path | str, backlog: Any) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "capability_quality.json"
        self.backlog = backlog
        self._lock = threading.RLock()

    def record(self, capability_id: str, *, verified: bool, duration: float,
               expected_duration: float, repairs: int = 0,
               fallbacks: int = 0) -> QualityResult:
        with self._lock:
            data = self._load()
            item = dict(data.get(capability_id) or {
                "runs": 0, "failures": 0, "repairs": 0, "fallbacks": 0,
                "duration_ratio_total": 0.0,
            })
            item["runs"] += 1
            item["failures"] += int(not verified)
            item["repairs"] += max(0, int(repairs))
            item["fallbacks"] += max(0, int(fallbacks))
            ratio = max(0.0, duration) / max(0.01, expected_duration)
            item["duration_ratio_total"] += ratio
            data[capability_id] = item
            self._save(data)

        runs = item["runs"]
        failure_rate = item["failures"] / runs
        repair_pressure = min(1.0, item["repairs"] / runs)
        fallback_pressure = min(1.0, item["fallbacks"] / runs)
        average_ratio = item["duration_ratio_total"] / runs
        slowness = min(1.0, max(0.0, average_ratio - 1) / 3)
        pressure = min(1.0, 0.40 * failure_rate + 0.20 * repair_pressure
                       + 0.20 * fallback_pressure + 0.20 * slowness)
        evidence = (
            f"failure_rate={failure_rate:.3f}", f"repairs_per_run={item['repairs'] / runs:.3f}",
            f"fallbacks_per_run={item['fallbacks'] / runs:.3f}",
            f"duration_ratio={average_ratio:.3f}",
        )
        needed = pressure >= 0.45
        if needed:
            self.backlog.add_ranked(
                f"optimize_{capability_id}", reason="; ".join(evidence),
                user_pain=pressure, frequency=min(1.0, 1 - math.exp(-runs / 3)),
                time_saved=slowness, reuse_probability=min(1.0, runs / 5),
                risk=0.1, learning_cost=0.35,
            )
        return QualityResult(capability_id, needed, round(pressure, 3), evidence)

    def _load(self) -> dict[str, Any]:
        try:
            return dict(load_json(self.path, default={}) or {})
        except (OSError, ValueError, TypeError):
            return {}

    def _save(self, data: dict[str, Any]) -> None:
        atomic_json_write(self.path, data)


__all__ = [
    "BackgroundBudgetManager", "BackgroundDecision", "BackgroundMode",
    "CapabilityQualityLoop", "LocalResourceSampler", "QualityResult", "ResourceSnapshot",
    "ShadowPriorityFactors",
]
