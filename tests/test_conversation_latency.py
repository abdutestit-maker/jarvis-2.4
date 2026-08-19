from __future__ import annotations

from pathlib import Path

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


def test_production_quick_reply_exposes_verified_fast_state(settings, monkeypatch):
    settings.offline_mode = True
    settings.warmup_local_on_start = True
    settings.source_path = Path(__file__).resolve().parents[1] / "config" / "settings.json"
    orch = Orchestrator(settings, output_callback=lambda _text: None)
    monkeypatch.setattr(orch, "_start_local_warmup", orch._warmup_ready.set)
    try:
        state = orch.handle_input("Привет")
    finally:
        orch.shutdown()
    assert state["mode"] == "conversation_fast"
    assert state["verified"] is True
