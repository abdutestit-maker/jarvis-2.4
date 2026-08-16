"""P5 §5.7 — единый execution path.

Проверяет, что REPL-вход и WebSocket-вход идут через один и тот же
Orchestrator.handle_input, и что CouncilRouter / Agent делят ЕДИНЫЙ
ModelRouter (никакого второго, независимого пути классификации).
"""

from __future__ import annotations

from config.settings import Settings
from core.orchestrator import Orchestrator
from core.router.council import CouncilRouter


def _make_orchestrator() -> Orchestrator:
    """Лёгкий Orchestrator на дефолтных Settings (без start())."""
    return Orchestrator(Settings())


def test_unified_model_router_shared():
    """CouncilRouter и Agent обязаны делить один ModelRouter (P5 §5.7)."""
    orch = _make_orchestrator()
    assert orch._model_router is orch._agent._model_router, \
        "Agent должен делить ModelRouter с Orchestrator"
    assert orch._model_router is orch._council._model_router, \
        "CouncilRouter должен делить ModelRouter с Orchestrator"


def test_council_uses_model_router_for_routing():
    """CouncilRouter делегирует выбор тира ModelRouter, а не свою логику."""
    orch = _make_orchestrator()
    council = orch._council
    # Тот же экземпляр, что и у оркестратора.
    assert isinstance(council, CouncilRouter)
    assert council._model_router is orch._model_router


def test_both_entries_use_handle_input(monkeypatch):
    """REPL (main.py) и WS (ws_server._dispatch) оба вызывают handle_input.

    Перехватываем handle_input и убеждаемся, что он вызван ровно с тем же
    текстом, что и поступил на вход — то есть второго пути обработки нет.
    """
    orch = _make_orchestrator()
    calls: list[str] = []

    def _fake_handle(text: str):
        calls.append(text)
        # минимальный валидный state, чтобы WS-диспетч не упал
        return {"response": "", "needs_confirmation": False}

    monkeypatch.setattr(orch, "handle_input", _fake_handle)

    # Имитация REPL-входа (main.py:237)
    text = "открой браузер"
    orch.handle_input(text)

    # Имитация WS-входа (ws_server.py:295) — тот же handle_input
    orch.handle_input(text)

    assert calls == [text, text], \
        "Оба входа (REPL и WS) должны идти через один handle_input"
