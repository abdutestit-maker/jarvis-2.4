from __future__ import annotations

import time
from pathlib import Path

from core.agent import Agent, AgentConfig


def test_common_conversation_does_not_call_model(settings, fake_backend):
    settings.offline_mode = True
    settings.source_path = Path(__file__).resolve().parents[1] / "config" / "settings.json"
    agent = Agent(settings, config=AgentConfig(enable_skill_forge=False))
    started = time.perf_counter()
    outcome = agent.execute("как дела?")
    elapsed_ms = (time.perf_counter() - started) * 1000

    assert outcome.mode == "conversation_fast"
    assert outcome.verified is True
    assert "в порядке" in outcome.text.lower()
    assert elapsed_ms < 500
    assert fake_backend.calls == []


def test_greeting_and_channel_check_are_deterministic(settings, fake_backend):
    settings.offline_mode = True
    settings.source_path = Path(__file__).resolve().parents[1] / "config" / "settings.json"
    agent = Agent(settings, config=AgentConfig(enable_skill_forge=False))

    outcome = agent.execute("Привет! Ты меня слышишь?")

    assert outcome.mode == "conversation_fast"
    assert "слышу" in outcome.text.lower()
    assert fake_backend.calls == []
