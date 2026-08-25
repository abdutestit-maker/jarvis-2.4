from __future__ import annotations

from pathlib import Path

from core.orchestrator import Orchestrator


def test_common_smalltalk_reaches_local_backend(fake_backend, settings):
    settings.offline_mode = True
    agent = __import__("core.agent", fromlist=["Agent"]).Agent(settings)
    outcome = agent.execute("как дела?")
    assert outcome.mode == "conversation"
    assert outcome.verified is True
    assert outcome.text == "Сэр, я вас понял. Это тестовый ответ Джарвиса."
    assert fake_backend.calls


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


def test_production_conversation_uses_local_backend(settings, fake_backend, monkeypatch):
    settings.offline_mode = True
    settings.warmup_local_on_start = True
    settings.source_path = Path(__file__).resolve().parents[1] / "config" / "settings.json"
    orch = Orchestrator(settings, output_callback=lambda _text: None)
    def ready():
        orch._warmup_diagnostics["state"] = "ready"
        orch._warmup_ready.set()
    monkeypatch.setattr(orch, "_start_local_warmup", ready)
    try:
        state = orch.handle_input("Привет")
    finally:
        orch.shutdown()
    assert state["mode"] == "conversation"
    assert state["verified"] is True
    assert fake_backend.calls
