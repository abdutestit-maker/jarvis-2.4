"""Тесты D1 — voice-first confirmation flow (П1 §1.3): таймаут -> авто-reject + UI fallback.

Confirmation реализован как action-specific state machine: каждое ожидающее
подтверждение живёт в ``agent._pending_confirmations[conf_id]`` (НЕ глобальный
bool), а watchdog по истечении ``confirmation_timeout_sec`` вызывает
безопасный авто-reject (отказ). Ответ до таймаута гасит таймер и исключает
двойную обработку (race-safe: первое валидное решение выигрывает).
"""

import threading
import time

from core.agent import Agent, AgentConfig
from core.task_runtime import Mission, MissionStatus


def _make_agent_with_pending(settings, timeout_sec, conf_id="x"):
    """Собирает Agent и засеивает одно ожидающее подтверждение (без реального LLM)."""
    agent = Agent(
        settings=settings,
        config=AgentConfig(enable_skill_forge=False, confirmation_timeout_sec=timeout_sec),
    )
    mission = Mission(task_id=conf_id, goal="тест подтверждения")
    cancel = threading.Event()
    agent._pending_confirmations[conf_id] = {
        "goal": "тест",
        "tool": "delete_file",
        "args": {},
        "risk": None,
        "caps": [],
        "mission": mission,
        "cancel": cancel,
        "trace": [],
    }
    return agent, mission, cancel


def test_p1_confirmation_timeout_auto_rejects(settings):
    """П1 §1.3: таймаут ожидания подтверждения -> безопасный авто-reject (отказ)."""
    agent, mission, _cancel = _make_agent_with_pending(
        settings, timeout_sec=0.01, conf_id="x"
    )
    agent._start_confirmation_watchdog("x")
    # Ждём срабатывания таймера (0.01с) с запасом.
    time.sleep(0.12)
    # Таймаут = молчаливый отказ: pending очищен, миссия отменена.
    assert "x" not in agent._pending_confirmations
    assert mission.status == MissionStatus.CANCELLED


def test_p1_confirmation_answer_before_timeout_cancels_timer(settings):
    """Ответ до таймаута гасит таймер и не даёт двойной обработки (race-safe)."""
    agent, mission, _cancel = _make_agent_with_pending(
        settings, timeout_sec=5.0, conf_id="x"
    )
    agent._start_confirmation_watchdog("x")
    # Пользователь ответил сразу (отклонил) — до истечения 5с.
    outcome = agent.answer_confirmation("x", approved=False)
    assert outcome is not None
    assert outcome.mode == "confirmation_rejected"
    # Повторный вызов — pending уже нет, двойной обработки быть не должно.
    assert agent.answer_confirmation("x", approved=False) is None
    # Таймер должен быть снят (не висит в словаре после ответа).
    assert "x" not in agent._confirmation_timers


def test_p1_confirmation_timeout_disabled_by_zero(settings):
    """timeout <= 0 отключает watchdog (подтверждение ждёт ответа бесконечно)."""
    agent, mission, _cancel = _make_agent_with_pending(
        settings, timeout_sec=0.0, conf_id="x"
    )
    agent._start_confirmation_watchdog("x")
    time.sleep(0.12)
    # При выключенном таймауте pending НЕ должен сам исчезнуть.
    assert "x" in agent._pending_confirmations
    assert mission.status != MissionStatus.CANCELLED
    # Убираем за собой, чтобы не висело в памяти.
    agent.answer_confirmation("x", approved=False)
