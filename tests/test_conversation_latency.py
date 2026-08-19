from __future__ import annotations

from core.orchestrator import Orchestrator


def test_common_smalltalk_is_deterministic_and_local():
    assert Orchestrator._quick_local_reply("как дела?") == "В порядке, сэр. Готов помочь с задачей."
    assert Orchestrator._quick_local_reply("спасибо") == "Всегда пожалуйста, сэр."


def test_conversation_budget_is_bounded(settings):
    assert 16 <= settings.limits.conversation_max_tokens <= 96


def test_live_ack_never_invokes_model(monkeypatch, settings):
    from core.agent import pick_acknowledgement

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("ACK path attempted model inference")

    monkeypatch.setattr("core.llm.get_llm_backend", fail_if_called)
    assert pick_acknowledgement(
        "web", goal="найди книгу", settings=settings, allow_model=False,
    ) == "Разбираюсь."
