"""Тесты Q07 (NEXT P1) — интеграция библиотеки команд (офлайн, без сети).

DoD: парсер разбирает 1000+ команд, маппит на реальные инструменты,
выявляет GAP. Тесты без сети.
"""

from __future__ import annotations

from pathlib import Path

from scripts.command_library_parser import (
    coverage_stats,
    parse_library,
)


def test_parses_over_1000_commands():
    entries = parse_library()
    assert len(entries) > 1000, f"ожидалось >1000 команд, получено {len(entries)}"


def test_first_entry_parsed():
    entries = parse_library()
    first = entries[0]
    assert first.number == 1
    assert "SYSTEM ADMIN" in first.category
    assert first.tools_raw  # Tools: не пуст
    assert not first.gap  # #001 покрыта system_status


def test_coverage_stats_returns_sane_dict():
    entries = parse_library()
    s = coverage_stats(entries)
    assert isinstance(s, dict)
    assert s["total"] == len(entries)
    assert 0 <= s["coverage_pct"] <= 100
    assert s["gaps"] >= 0
    assert s["covered"] + s["gaps"] == s["total"]
    # GAP-записи действительно genuine — имеют описание или Tools (не пустышки).
    gaps = [e for e in entries if e.gap]
    genuine = [e for e in gaps if e.title or e.tools_raw or e.caps_raw]
    assert len(genuine) == len(gaps), "есть GAP-записи без контента (parse failure?)"


def test_dynamic_registry_index_used():
    """Маппинг строится из РЕАЛЬНОГО реестра, не из зашитого словаря."""
    from core.actions import DEFAULT_REGISTRY

    # У инструментов есть покрытие ключевыми словами.
    entries = parse_library()
    tool_names = {t.name for t in DEFAULT_REGISTRY.list_tools()}
    # Хотя бы часть реальных инструментов матчится на команды.
    matched = set()
    for e in entries:
        matched |= e.matched_tools
    assert matched & tool_names, "ни один реальный инструмент не матчится — индекс пуст?"
    # Нет ссылок на удалённый _REAL_TOOLS.
    import scripts.command_library_parser as mod
    assert not hasattr(mod, "_REAL_TOOLS"), "_REAL_TOOLS должен быть удалён"
