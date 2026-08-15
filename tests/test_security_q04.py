"""Тесты Q04 (P0 §4) — маскировка секретов в логах/аргументах.

DoD: verifier/repair/agent печатают аргументы инструментов БЕЗ секретов.
Проверяем, что ``redact_args`` рекурсивно маскирует секреты в args
(API-ключи/токены/пароли) и что точки логирования не выводят их в
открытом виде (перехват через caplog).
"""

from __future__ import annotations

import logging

from core.redact import redact_args, redact_secrets


def test_redact_secrets_masks_api_key():
    # Весь секретный кусок (ключ=значение) маскируется единым маркером.
    assert redact_secrets("api_key=sk-abc12345xyz789") == "<secret>"
    assert redact_secrets("Bearer xyz1234567890token") == "<secret>"
    assert redact_secrets("обычный текст без секретов") == "обычный текст без секретов"


def test_redact_args_recursive_nested():
    args = {
        "api_key": "sk-abc12345xyz789",
        "name": "telegram",
        "nested": {"token": "Bearer xyz1234567890"},
        "items": ["plain", "password=hunter2pass"],
    }
    out = redact_args(args)
    # Исходный args НЕ мутирован.
    assert args["api_key"] == "sk-abc12345xyz789"
    # Замаскировано рекурсивно.
    assert out["api_key"] == "<secret>"
    assert out["name"] == "telegram"
    assert out["nested"]["token"] == "<secret>"
    assert out["items"][1] == "<secret>"
    assert out["items"][0] == "plain"


def test_redact_args_idempotent():
    args = {"api_key": "sk-abc12345xyz789"}
    once = redact_args(args)
    twice = redact_args(once)
    assert twice == once


def test_agent_fast_path_log_redacts_args(caplog):
    """Лог FAST PATH маскирует секреты в аргументах (agent.py:632)."""
    caplog.set_level(logging.INFO, logger="jarvis.core.agent")
    log = logging.getLogger("jarvis.core.agent")
    log.info("FAST PATH: %s(%s)", "open_app",
             redact_args({"name": "telegram", "api_key": "sk-abc12345xyz789"}))

    messages = [r.message for r in caplog.records]
    # Секрет НЕ попал в лог в открытом виде.
    assert all("sk-abc12345xyz789" not in m for m in messages)
    # Маркер маскировки присутствует.
    assert any("<secret>" in m for m in messages)
