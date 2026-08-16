"""P5 §5.10 — реальные функциональные само-проверки (end-to-end).

Сквозные проверки поверх реальных компонентов Джарвиса (только нижний
слой LLM подменён фейком, как и во всём спринте). Покрывает критерии
§5.10 из мастер-спеки:
  * текстовая команда через Orchestrator -> реальный ответ backend;
  * HIGH-risk действие -> карточка подтверждения -> отмена ->
    действие НЕ выполнилось;
  * голосовая команда (§5.9 готова) -> STT доступен, распознанный текст
    прогоняется через тот же Orchestrator;
  * перезапуск сессии -> граф-память сохранилась (персистентна).
"""

from __future__ import annotations

import core.agent as agent_mod
import core.llm as llm_mod
import core.router.council as council_mod
from config.settings import Settings


def _patch_backend(monkeypatch, fake_backend):
    """Глобально подменяет get_llm_backend фейком на всех путях вызова."""
    monkeypatch.setattr(llm_mod, "get_llm_backend", lambda s, t=None: fake_backend)
    monkeypatch.setattr(agent_mod, "get_llm_backend", lambda s, t=None: fake_backend)
    monkeypatch.setattr(council_mod, "get_llm_backend", lambda s, t=None: fake_backend)
    monkeypatch.setattr(Settings, "is_tier_available", lambda self, tier: True)


# --------------------------------------------------------------------------- #
#  1) Текстовая команда -> реальный ответ backend
# --------------------------------------------------------------------------- #

def test_e2e_text_command_via_orchestrator(settings, fake_backend, tmp_path, monkeypatch):
    """Команда через Orchestrator.handle_input даёт непустой ответ."""
    _patch_backend(monkeypatch, fake_backend)

    from core.orchestrator import Orchestrator

    monkeypatch.chdir(tmp_path)
    settings.paths.documents_dir = str(tmp_path)
    fake_backend.set_answer("Сэр, системы в норме. Джарвис к вашим услугам.")
    orch = Orchestrator(settings)
    try:
        state = orch.handle_input("привет")
        assert state.get("response", "").strip(), "ответ backend не должен быть пустым"
    finally:
        orch.shutdown()


# --------------------------------------------------------------------------- #
#  2) HIGH-risk -> подтверждение -> ОТМЕНА -> действие не выполнено
# --------------------------------------------------------------------------- #

def test_e2e_high_risk_cancel(settings, fake_backend, tmp_path, monkeypatch):
    """Отмена HIGH-risk подтверждения -> действие НЕ выполняется."""
    _patch_backend(monkeypatch, fake_backend)

    from core.orchestrator import Orchestrator

    monkeypatch.chdir(tmp_path)
    settings.paths.documents_dir = str(tmp_path)
    # HIGH-risk: цель удаляет/создаёт файл -> write_file требует подтверждения.
    fake_backend.set_plan("write_file", {"path": "danger.txt", "content": "x"})
    orch = Orchestrator(settings)
    try:
        state = orch.handle_input("удали файл danger.txt и создай новый")
        assert state.get("needs_confirmation") is True, state
        cid = state.get("confirmation_id")
        assert cid, "confirmation_id должен быть выдан"

        # Отклоняем -> файл НЕ создаётся.
        result = orch.answer_confirmation(cid, approved=False)
        assert result is not None
        assert (tmp_path / "danger.txt").exists() is False, \
            "при отмене HIGH-risk файл не должен быть создан"
    finally:
        orch.shutdown()


# --------------------------------------------------------------------------- #
#  3) Голосовая команда (§5.9) -> STT доступен, текст прогоняется через Orchestrator
# --------------------------------------------------------------------------- #

def test_e2e_voice_command_available_and_routed(settings, fake_backend, tmp_path, monkeypatch):
    """STT доступен при stt_enabled=True, распознанный текст идёт в handle_input."""
    _patch_backend(monkeypatch, fake_backend)

    from core.orchestrator import Orchestrator
    from core.voice.stt import STTEngine

    settings.voice.stt_enabled = True
    eng = STTEngine(settings)
    # В этом окружении faster-whisper установлен -> движок реально готов.
    assert eng.is_available() is True, "STT должен быть доступен при stt_enabled=True"

    monkeypatch.chdir(tmp_path)
    settings.paths.documents_dir = str(tmp_path)
    fake_backend.set_answer("Принято, сэр. Выполняю голосовую команду.")
    orch = Orchestrator(settings)
    try:
        # Имитация: STT распознал фразу -> та же команда, что и из консоли.
        recognized = "открой браузер"
        state = orch.handle_input(recognized)
        assert state.get("response", "").strip(), "голосовая команда дала ответ"
    finally:
        orch.shutdown()


# --------------------------------------------------------------------------- #
#  4) Перезапуск сессии -> память сохранилась (граф персистентен)
# --------------------------------------------------------------------------- #

def test_e2e_memory_persists_across_sessions(settings, fake_backend, tmp_path):
    """Граф-память персистентна между перезапусками Orchestrator."""
    from core.memory.knowledge_graph import GraphMemoryStore

    # Направляем data_dir в tmp, чтобы graph_dir = tmp/graph был изолирован.
    settings.paths.data_dir = str(tmp_path)

    # Сессия 1: пишем факт.
    store1 = GraphMemoryStore(settings)
    node_id = store1.create_node(
        "J.A.R.V.I.S. v3.0",
        {"detail": "важный факт про проект", "kind": "fact"},
    )
    assert node_id > 0, "узел должен создаться"
    store1.close()

    # Сессия 2: читаем тот же факт (эмуляция перезапуска).
    store2 = GraphMemoryStore(settings)
    try:
        results = store2.search_nodes("J.A.R.V.I.S", top_k=5)
        texts = " ".join(
            (r.get("label") or "") + " " + (r.get("properties", {}).get("detail") or "")
            for r in results
        )
        assert "важный факт" in texts or "J.A.R.V.I.S" in texts, \
            "факт должен пережить перезапуск сессии"
    finally:
        store2.close()
