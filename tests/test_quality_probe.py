from __future__ import annotations

from config.settings import Settings
from scripts.quality_probe import (
    _percentiles,
    probe_current_time,
    probe_media_safety,
    probe_memory_relevance,
    probe_system_status,
    probe_unknown_task,
)


def test_percentiles_are_deterministic():
    assert _percentiles([3, 1, 2]) == {
        "count": 3,
        "p50_ms": 2.0,
        "p95_ms": 3.0,
        "max_ms": 3.0,
    }


def test_quality_probe_time_uses_real_local_clock():
    result = probe_current_time(Settings(offline_mode=True))
    assert result["tool"] == "current_time"
    assert result["verified"] is True
    assert result["foreign_tool"] is False


def test_quality_probe_system_status_is_observed():
    result = probe_system_status(Settings(offline_mode=True))
    assert result["verified"] is True
    assert "CPU:" in result["output"]
    assert "RAM:" in result["output"]


def test_quality_probe_blocks_network_music_without_reminder():
    result = probe_media_safety(Settings(offline_mode=True))
    assert result["verified"] is True
    assert result["action_taken"] is False
    assert result["reminder_called"] is False


def test_quality_probe_unknown_task_stays_research_pending():
    result = probe_unknown_task(Settings(offline_mode=True))
    assert result["research_pending"] is True
    assert result["success"] is False
    assert result["foreign_tool_call"] is False


def test_quality_probe_memory_relevance_does_not_leak_unrelated_fact():
    result = probe_memory_relevance()
    assert result["verified"] is True
    assert result["irrelevant_fact_leaked"] is False
