"""Тесты каталога свободных LLM-провайдеров (free_providers).

Цель: ноль жёстко-зашитых секретов; resolver корректно выбирает провайдера
только когда у пользователя есть ключ; offline_mode уважается; OpenAI-совместимая
конфигурация собирается без подстановки ключа.
"""

import sys
import types

import pytest

sys.path.insert(0, ".")

from core.llm.free_providers import (  # noqa: E402
    FREE_PROVIDERS,
    as_openai_compatible,
    resolve_free_provider,
)


class _FakeSettings:
    """Минимик settings: offline_mode + get_api_key + get_endpoint."""

    def __init__(self, keys=None, offline_mode=False):
        self._keys = keys or {}
        self.offline_mode = offline_mode

    def get_api_key(self, provider):
        return self._keys.get(provider)


def test_catalog_no_plains_secrets():
    """Каталог не должен содержать реальных api-ключей."""
    import json as _json
    import re as _re
    for p in FREE_PROVIDERS:
        raw = _json.dumps(p.__dict__)
        # запрещаем длинные hex/«sk-» строки
        assert not _re.search(r"sk-[A-Za-z0-9]{8,}", raw)
        assert "api_key=" not in raw.lower() or "requires_key" in raw


def test_catalog_has_expected_providers():
    names = {p.name for p in FREE_PROVIDERS}
    assert {"openrouter", "groq", "gemini"}.issubset(names)


def test_resolve_none_when_offline_or_no_key():
    s = _FakeSettings(offline_mode=True)
    assert resolve_free_provider(s) is None
    s2 = _FakeSettings(offline_mode=False, keys={})
    assert resolve_free_provider(s2) is None


def test_resolve_prefers_keyed_provider():
    s = _FakeSettings(keys={"groq": "KEY"})
    prov = resolve_free_provider(s)
    assert prov is not None and prov.name == "groq"


def test_resolve_respects_preferred():
    s = _FakeSettings(keys={"openrouter": "K", "groq": "K"})
    prov = resolve_free_provider(s, preferred="openrouter")
    assert prov is not None and prov.name == "openrouter"


def test_as_openai_compatible_no_key_injected():
    prov = next(p for p in FREE_PROVIDERS if p.name == "groq")
    cfg = as_openai_compatible(prov)
    assert cfg["base_url"].startswith("http")
    assert cfg["model"]
    assert "api_key" not in cfg  # ключ НЕ сидим здесь
