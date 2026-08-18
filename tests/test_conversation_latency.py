from __future__ import annotations

from core.orchestrator import Orchestrator


def test_common_smalltalk_is_deterministic_and_local():
    assert Orchestrator._quick_local_reply("как дела?") == "В порядке, сэр. Готов помочь с задачей."
    assert Orchestrator._quick_local_reply("спасибо") == "Всегда пожалуйста, сэр."


def test_conversation_budget_is_bounded(settings):
    assert 16 <= settings.limits.conversation_max_tokens <= 96
