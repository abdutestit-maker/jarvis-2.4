"""Q07 (NEXT P1) — парсинг JARVIS_COMMAND_LIBRARY.md → реестр команд↔capabilities.

Чистый офлайн-парсинг: разбирает 1450+ записей библиотеки команд в
структурированный реестр, маппит инструменты/капabilities (из записи)
на РЕАЛЬНЫЕ инструменты J.A.RVIS (`core.actions.DEFAULT_REGISTRY`) и
выявляет ХОТ-СПОТЫ:
  * команды, чьи `Tools:`/`Caps:` НЕ покрываются ни одним реальным
    инструментом (gap analysis — что ещё предстоит реализовать);
  * категории с наибольшим числом команд (приоритет интеграции).

Маппинг coverage СТРОИТСЯ ДИНАМИЧЕСКИ из реального реестра инструментов
(`DEFAULT_REGISTRY`), а не из жёстко зашитого словаря — чтобы анализ
отражал АКТУАЛЬНЫЕ возможности и не дрейфовал при добавлении инструментов.

НЕ меняет рантайм, НЕ трогает модели. Только анализ + вывод статистики.
Используется в night-режиме для расширения покрытия команд.

Формат записи (см. docs/JARVIS_COMMAND_LIBRARY.md):
    ### 001 — Полная диагностика компьютера
    «...описание...»
    Cat: SYSTEM ADMIN | Diagnostic
    Diff: L3 | Tools: tasklist, wmic/powershell, eventvwr, perfmon | Web0 Code1 Files1 Vision0 Long0 | Auto 8
    Caps: system inventory, log mining, health scoring, remediation planning
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Корень проекта в sys.path, чтобы `from core.actions import ...` работал
# при запуске как `python scripts/command_library_parser.py`.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

#: Путь к библиотеке команд.
LIBRARY_PATH = _ROOT / "docs" / "JARVIS_COMMAND_LIBRARY.md"


@dataclass
class CommandEntry:
    """Одна запись библиотеки команд."""

    number: int
    title: str
    category: str = ""
    subcategory: str = ""
    difficulty: str = ""
    tools_raw: str = ""
    caps_raw: str = ""
    auto: Optional[int] = None
    web: Optional[int] = None
    code: Optional[int] = None
    files: Optional[int] = None
    vision: Optional[int] = None
    voice: Optional[int] = None
    long: Optional[int] = None
    safety_sensitive: bool = False
    description: str = ""
    # Вычисляемые поля (gap analysis).
    matched_tools: Set[str] = field(default_factory=set)
    gap: bool = False  # True, если ни один реальный инструмент не покрыт.

    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "category": self.category,
            "subcategory": self.subcategory,
            "difficulty": self.difficulty,
            "tools_raw": self.tools_raw,
            "caps_raw": self.caps_raw,
            "auto": self.auto,
            "flags": {
                "web": self.web, "code": self.code, "files": self.files,
                "vision": self.vision, "voice": self.voice, "long": self.long,
            },
            "safety_sensitive": self.safety_sensitive,
            "matched_tools": sorted(self.matched_tools),
            "gap": self.gap,
        }


def _build_coverage_index() -> Dict[str, Set[str]]:
    """Динамически строит keyword→tool индекс из РЕАЛЬНОГО реестра.

    Для каждого инструмента берём:
      * токены имени (camelCase/snake_case разбиваются на слова);
      * первые ~8 слов description (нижний регистр, >=3 символа).

    Возвращает {tool_name: {kw1, kw2, ...}}.
    """
    from core.actions import DEFAULT_REGISTRY

    index: Dict[str, Set[str]] = {}
    for tool in DEFAULT_REGISTRY.list_tools():
        name = tool.name
        desc = (tool.description or "").lower()
        kws: Set[str] = set()
        # Имя: разбиваем snake_case / camelCase на слова.
        name_parts = re.findall(r"[a-z0-9]+|[A-Z][a-z0-9]+", name)
        for p in name_parts:
            p = p.lower()
            if len(p) >= 3:
                kws.add(p)
        # Несколько осмысленных синонимов из имени целиком.
        if name == "system_status":
            kws.update({"system", "status", "diagnos", "perf", "hardware",
                        "telemetry", "temperature", "thermal", "cpu", "ram",
                        "disk", "memory", "health"})
        elif name == "web_search":
            kws.update({"web", "search", "browse", "google", "duckduckgo", "internet"})
        elif name == "web_fetch":
            kws.update({"fetch", "url", "website", "page", "scrape", "crawl"})
        elif name in ("read_file", "write_file", "list_files", "search_files"):
            kws.update({"file", "files", "document", "read", "write", "edit",
                        "save", "create file", "list", "directory", "folder",
                        "search file", "find file", "grep"})
        elif name in ("add_reminder", "list_reminders", "cancel_reminder"):
            kws.update({"reminder", "remind", "schedule", "alarm", "timer"})
        elif name in ("computer_mouse", "computer_keyboard", "computer_screenshot"):
            kws.update({"click", "mouse", "cursor", "pointer", "type", "keyboard",
                        "keypress", "press key", "screenshot", "screen capture", "snip"})
        elif name == "open_app":
            kws.update({"open", "launch", "app", "start"})
        elif name == "close_app":
            kws.update({"close", "kill", "terminate"})
        elif name == "volume":
            kws.update({"volume", "sound", "audio", "mute"})
        elif name == "weather":
            kws.update({"weather", "forecast", "temperature outside"})
        # Из description: первые содержательные слова.
        for w in re.findall(r"[a-zа-яё0-9_]+", desc)[:8]:
            if len(w) >= 3:
                kws.add(w)
        index[name] = kws
    return index


_COVERAGE_INDEX: Optional[Dict[str, Set[str]]] = None


def _get_index() -> Dict[str, Set[str]]:
    global _COVERAGE_INDEX
    if _COVERAGE_INDEX is None:
        _COVERAGE_INDEX = _build_coverage_index()
    return _COVERAGE_INDEX


def _compute_coverage(e: CommandEntry) -> None:
    """Маппит Tools:/Caps:/описание на реальные инструменты J.A.RVIS (gap)."""
    haystack = " ".join([
        e.tools_raw, e.caps_raw, e.description, e.title, e.category,
    ]).lower()
    matched: Set[str] = set()
    for tool, kws in _get_index().items():
        for kw in kws:
            if kw in haystack:
                matched.add(tool)
                break
    e.matched_tools = matched
    e.gap = len(matched) == 0


def _parse_entry(block: str, number: int) -> CommandEntry:
    """Парсит блок одной записи (между `### NNN` и следующим `### `)."""
    lines = block.splitlines()
    title = ""
    for ln in lines:
        if ln.startswith("### "):
            m = re.match(r"###\s+\d+\s+—\s+(.+)", ln)
            if m:
                title = m.group(1).strip()
            break

    e = CommandEntry(number=number, title=title)

    text = block
    m = re.search(r"^Cat:\s*(.+?)\s*$", text, re.MULTILINE)
    if m:
        cats = [c.strip() for c in m.group(1).split("|")]
        e.category = cats[0] if cats else ""
        e.subcategory = cats[1] if len(cats) > 1 else ""
    m = re.search(r"^Diff:\s*(L\d)\s*\|?\s*Tools:\s*([^|]+)", text, re.MULTILINE)
    if m:
        e.difficulty = m.group(1).strip()
        e.tools_raw = m.group(2).strip()
    m = re.search(r"Web(\d)\s+Code(\d)\s+Files(\d)\s+Vision(\d)\s+Long(\d)", text)
    if m:
        e.web, e.code, e.files, e.vision, e.long = (int(x) for x in m.groups())
    m = re.search(r"Auto\s+(\d+)", text)
    if m:
        e.auto = int(m.group(1))
    m = re.search(r"^Caps:\s*(.+?)\s*$", text, re.MULTILINE)
    if m:
        e.caps_raw = m.group(1).strip()
    if "SAFETY-SENSITIVE" in text.upper():
        e.safety_sensitive = True
    m = re.search(r"«(.+?)»", text, re.DOTALL)
    if m:
        e.description = m.group(1).strip()

    _compute_coverage(e)
    return e


def parse_library(path: Optional[Path] = None) -> List[CommandEntry]:
    """Парсит всю библиотеку команд в список записей."""
    p = Path(path) if path else LIBRARY_PATH
    text = p.read_text(encoding="utf-8")
    parts = re.split(r"(?=^###\s+\d+\s+—)", text, flags=re.MULTILINE)
    entries: List[CommandEntry] = []
    for part in parts:
        m = re.match(r"###\s+(\d+)\s+—", part.strip())
        if not m:
            continue
        number = int(m.group(1))
        entries.append(_parse_entry(part, number))
    return entries


def coverage_stats(entries: List[CommandEntry]) -> Dict[str, Any]:
    """Статистика покрытия + хот-споты."""
    total = len(entries)
    covered = [e for e in entries if not e.gap]
    gaps = [e for e in entries if e.gap]

    cat_counter: Counter = Counter()
    for e in entries:
        cat_counter[e.category or "UNKNOWN"] += 1

    gap_cat: Counter = Counter()
    for e in gaps:
        gap_cat[e.category or "UNKNOWN"] += 1

    tool_hits: Counter = Counter()
    for e in covered:
        for t in e.matched_tools:
            tool_hits[t] += 1

    safety = [e for e in entries if e.safety_sensitive]

    return {
        "total": total,
        "covered": len(covered),
        "gaps": len(gaps),
        "coverage_pct": round(100.0 * len(covered) / total, 1) if total else 0.0,
        "top_categories": cat_counter.most_common(10),
        "top_gap_categories": gap_cat.most_common(10),
        "tool_hits": tool_hits.most_common(),
        "safety_sensitive_count": len(safety),
        "gap_examples": [
            {"number": e.number, "title": e.title, "category": e.category,
             "tools_raw": e.tools_raw, "caps_raw": e.caps_raw}
            for e in gaps[:20]
        ],
    }


def summarize(entries: Optional[List[CommandEntry]] = None) -> str:
    """Человекочитаемый отчёт (для лога/отчёта утра)."""
    if entries is None:
        entries = parse_library()
    s = coverage_stats(entries)
    lines = [
        f"Команд в библиотеке: {s['total']}",
        f"Покрыты реальными инструментами: {s['covered']} ({s['coverage_pct']}%)",
        f"GAP (не покрыты): {s['gaps']}",
        f"SAFETY-SENSITIVE: {s['safety_sensitive_count']}",
        "",
        "Топ категорий:",
    ]
    for cat, n in s["top_categories"]:
        lines.append(f"  {cat}: {n}")
    lines.append("")
    lines.append("Топ GAP-категорий (что ещё реализовать):")
    for cat, n in s["top_gap_categories"]:
        lines.append(f"  {cat}: {n}")
    lines.append("")
    lines.append("Нагрузка на реальные инструменты:")
    for tool, n in s["tool_hits"]:
        lines.append(f"  {tool}: {n}")
    return "\n".join(lines)


if __name__ == "__main__":
    import json

    _entries = parse_library()
    if "--json" in sys.argv:
        print(json.dumps([e.to_dict() for e in _entries], ensure_ascii=False, indent=2))
    else:
        print(summarize(_entries))
