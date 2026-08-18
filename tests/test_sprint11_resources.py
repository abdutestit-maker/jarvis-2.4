"""Background resource budget, Shadow priority and quality-loop contracts."""

from __future__ import annotations

from pathlib import Path

from core.living.resources import (
    BackgroundBudgetManager,
    BackgroundMode,
    CapabilityQualityLoop,
    ResourceSnapshot,
    ShadowPriorityFactors,
)
from core.shadow.backlog import ShadowBacklog


def test_background_budget_runs_when_idle_and_pauses_under_user_load() -> None:
    manager = BackgroundBudgetManager()

    idle = manager.assess(ResourceSnapshot(cpu_percent=12, ram_percent=30,
                                           foreground_latency_ms=20))
    gaming = manager.assess(ResourceSnapshot(cpu_percent=45, ram_percent=60,
                                             foreground_latency_ms=80, gaming=True,
                                             fullscreen=True))
    speaking = manager.assess(ResourceSnapshot(cpu_percent=20, ram_percent=40,
                                               foreground_latency_ms=40, active_tts=True))

    assert idle.mode is BackgroundMode.RUN
    assert idle.cpu_quota > 0
    assert gaming.mode is BackgroundMode.PAUSE
    assert speaking.mode in {BackgroundMode.THROTTLE, BackgroundMode.PAUSE}


def test_shadow_priority_balances_pain_reuse_risk_and_learning_cost() -> None:
    useful = ShadowPriorityFactors(
        user_pain=0.9, frequency=0.9, time_saved=0.8,
        reuse_probability=0.9, risk=0.1, learning_cost=0.2,
    )
    novelty = ShadowPriorityFactors(
        user_pain=0.1, frequency=0.1, time_saved=0.2,
        reuse_probability=0.1, risk=0.5, learning_cost=0.9,
    )

    assert useful.score() > novelty.score()
    assert useful.score() >= 0.7
    assert novelty.score() < 0.3


def test_shadow_backlog_add_ranked_returns_highest_value_work(tmp_path: Path) -> None:
    backlog = ShadowBacklog(tmp_path)
    backlog.add_ranked(
        "novelty", reason="low value", user_pain=0.1, frequency=0.1,
        time_saved=0.1, reuse_probability=0.1, risk=0.5, learning_cost=0.8,
    )
    backlog.add_ranked(
        "repeat_export", reason="repeated pain", user_pain=0.9, frequency=0.9,
        time_saved=0.8, reuse_probability=0.9, risk=0.1, learning_cost=0.2,
    )

    selected = backlog.next(cpu_percent=10, gpu_percent=5, gaming=False)

    assert selected is not None
    assert selected.id == "repeat_export"


def test_quality_loop_enqueues_optimization_for_repairs_fallbacks_and_slow_runs(tmp_path: Path) -> None:
    backlog = ShadowBacklog(tmp_path / "backlog")
    loop = CapabilityQualityLoop(tmp_path / "quality", backlog)

    loop.record("workflow_export", verified=True, duration=12, expected_duration=3,
                repairs=2, fallbacks=1)
    result = loop.record("workflow_export", verified=False, duration=15,
                         expected_duration=3, repairs=1, fallbacks=1)
    selected = backlog.next(cpu_percent=5, gpu_percent=5, gaming=False)

    assert result.optimization_needed is True
    assert selected is not None
    assert selected.id == "optimize_workflow_export"
    assert result.evidence


def test_background_budget_respects_battery_and_active_user_mission() -> None:
    manager = BackgroundBudgetManager()

    result = manager.assess(ResourceSnapshot(
        cpu_percent=15, ram_percent=30, foreground_latency_ms=20,
        on_battery=True, battery_percent=10, active_user_mission=True,
    ))

    assert result.mode is BackgroundMode.PAUSE
    assert "battery" in " ".join(result.reasons)


class _Memory:
    percent = 37.5


class _Battery:
    power_plugged = False
    percent = 25


class _Psutil:
    @staticmethod
    def cpu_percent(interval=None):
        assert interval is None
        return 12.5

    @staticmethod
    def virtual_memory():
        return _Memory()

    @staticmethod
    def sensors_battery():
        return _Battery()


def test_local_resource_sampler_collects_coarse_metrics_only() -> None:
    from core.living.resources import LocalResourceSampler

    snapshot = LocalResourceSampler(_Psutil()).sample(
        foreground_latency_ms=4, active_tts=True, gpu_percent=7,
    )

    assert snapshot.cpu_percent == 12.5
    assert snapshot.ram_percent == 37.5
    assert snapshot.gpu_percent == 7
    assert snapshot.on_battery is True
    assert snapshot.battery_percent == 25
    assert snapshot.active_tts is True
