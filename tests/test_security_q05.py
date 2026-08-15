"""Тесты Q05 (P0 §4) — SSRF-защита сетевых инструментов.

DoD: web_fetch НЕ ходит на внутренние/зарезервированные адреса
(127/10.x/192.168.x/169.254.x/localhost/file:///не-http схема).

Проверяем ДВА слоя:
1. ``is_ssrf_blocked`` блокирует опасные URL и пропускает публичные.
2. ``WebFetchTool.run`` при заблокированном URL возвращает ok=False
   (не уходит в сеть, не падает исключением).
"""

from __future__ import annotations

import pytest

from config.settings import Settings
from core.actions.base import ToolContext
from core.actions.web_fetch import WebFetchTool
from core.network_guard import is_ssrf_blocked, assert_safe_url, SSRFBlocked


# --- 1. Утилита ----------------------------------------------------------- #

def test_ssrf_blocks_internal_and_metadata():
    blocked = [
        "http://127.0.0.1/",
        "http://localhost/",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.5/admin",
        "http://192.168.1.1/",
        "http://0.0.0.0/",
        "http://[::1]/",
        "file:///etc/passwd",
        "ftp://example.com/",
        "gopher://127.0.0.1:11211/",
        "http://metadata.google.internal/",
    ]
    for url in blocked:
        assert is_ssrf_blocked(url), f"должен быть заблокирован: {url}"


def test_ssrf_allows_public():
    allowed = [
        "http://example.com",
        "https://news.ycombinator.com",
        "https://ru.wikipedia.org/wiki/Python",
    ]
    for url in allowed:
        assert not is_ssrf_blocked(url), f"не должен быть заблокирован: {url}"


def test_assert_safe_url_raises_on_blocked():
    with pytest.raises(SSRFBlocked):
        assert_safe_url("http://169.254.169.254/")
    # Публичный — возвращает нормализованный.
    assert assert_safe_url("  https://example.com/  ") == "https://example.com/"


# --- 2. Инструмент -------------------------------------------------------- #

def test_web_fetch_blocks_ssrf_target():
    """WebFetchTool НЕ уходит в сеть на внутренний адрес (ok=False)."""
    settings = Settings()
    ctx = ToolContext(settings=settings)

    # Монкипнуть сеть не нужно: блокировка происходит ДО requests.get.
    result = WebFetchTool().run({"url": "http://169.254.169.254/latest/"}, ctx)

    assert result.ok is False
    assert "SSRF" in (result.error or "") or "заблок" in (result.error or "").lower()


def test_web_fetch_blocks_file_scheme():
    settings = Settings()
    ctx = ToolContext(settings=settings)
    result = WebFetchTool().run({"url": "file:///C:/Windows/System32/drivers/etc/hosts"}, ctx)
    assert result.ok is False
