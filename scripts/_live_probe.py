#!/usr/bin/env python
"""Живой прогон команд через Orchestrator + замер latency (headless).

Гоняет реальный локальный путь (Qwen3 GGUF), без фронтенда.
"""
from __future__ import annotations

import json
import argparse
import re
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config import load_config  # noqa: E402
from core.orchestrator import Orchestrator  # noqa: E402
from core.utils.logger import setup_logging  # noqa: E402
from core.intelligence import LatencyBudget, latency_summary  # noqa: E402

setup_logging(level="WARNING", console=False)

CAPTURED: list[str] = []


def _capture(text: str) -> None:
    CAPTURED.append(text)


COMMANDS = [
    "Привет! Ты меня слышишь?",
    "Найди книгу 48 законов власти, хочу почитать",
    "Поставь музыку, настроения нет",
    "Который час?",
    "Открой блокнот",
    "Открой блокнот и поставь музыку",
    "Что такое энтропия простыми словами?",
    "Неизвестная команда для проверки capability research",
]

FAST_BUDGET = LatencyBudget("fast", 600.0, 1000.0, 1500.0)


def _assert_behavior(item: dict) -> list[str]:
    """Return assertion failures instead of hiding live behavior problems."""
    cmd = item["cmd"].casefold()
    failures: list[str] = []
    meta = item.get("meta") or {}
    response = (item.get("resp") or "").casefold()
    compound_music = "и поставь музыку" in cmd
    if "привет" in cmd or "как дела" in cmd:
        if meta.get("mode") != "conversation_fast" or meta.get("verified") is not True:
            failures.append("routine conversation paid the model round-trip")
    if "музык" in cmd and not compound_music:
        if meta.get("intent") != "media":
            failures.append("music intent did not resolve to media")
        if meta.get("tool") != "play_music":
            failures.append(f"media request selected {meta.get('tool')!r}, expected play_music")
        if meta.get("verified") is not True:
            failures.append("media playback surface was not verified")
        if any(marker in response for marker in ("youtube", "ютуб", "поиск музыки")):
            failures.append("bare media request opened a network search")
        if "напомин" in response:
            failures.append("media request was routed to reminder")
    if "который час" in cmd:
        if meta.get("intent") != "system":
            failures.append("time intent did not resolve to system")
        if meta.get("tool") != "current_time" or meta.get("verified") is not True:
            failures.append("time request was not verified by current_time")
        if "время не определено" in response or not re.search(r"\b\d{2}:\d{2}", response):
            failures.append("time response is unresolved")
    if "блокнот" in cmd and not compound_music and item["sec"] > 1.5:
        failures.append(f"fast path exceeded 1500ms ({item['sec']:.3f}s)")
    if "блокнот" in cmd and meta.get("tool") not in {"open_app", "command_batch"}:
        failures.append("notepad request selected an unexpected tool")
    if "энтроп" in cmd and any(marker in response for marker in ("gta 5", "менталист")):
        failures.append("irrelevant profile memory leaked into explanation")
    if "найди книгу" in cmd and "источник не ответил" in response:
        failures.append("search returned an unstructured failure instead of result or resumable fallback")
    if "найди книгу" in cmd and not meta.get("verified") and "research-" not in response and "повтор" not in response:
        failures.append("offline search did not expose a resumable task")
    if "неизвестная команда" in cmd and (meta.get("tool") or meta.get("verified")):
        failures.append("unknown request reported a tool success")
    if compound_music:
        if meta.get("tool") != "command_batch" or meta.get("verified") is not True:
            failures.append("compound request did not verify every clause")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS end-to-end behavior and latency probe")
    parser.add_argument("--dry-run", action="store_true", help="run deterministic behavior fixtures without model startup")
    parser.add_argument("--output", default="_live_probe_result.json")
    args = parser.parse_args()
    if args.dry_run:
        results = [
            {"cmd": "Привет! Ты меня слышишь?", "sec": 0.12, "meta": {"intent": "none", "tool": "", "verified": True, "mode": "conversation_fast"}, "resp": "Слышу вас, сэр. Канал связи работает.", "err": None},
            {"cmd": "Поставь музыку", "sec": 0.12, "meta": {"intent": "media", "tool": "play_music", "verified": True}, "resp": "Открыл локальный музыкальный плеер", "err": None},
            {"cmd": "Который час?", "sec": 0.04, "meta": {"intent": "system", "tool": "current_time", "verified": True}, "resp": "Сейчас 12:00:01, 2026-08-19", "err": None},
            {"cmd": "Открой блокнот", "sec": 0.59, "meta": {"intent": "app", "tool": "open_app", "verified": True}, "resp": "Запустил блокнот", "err": None},
            {"cmd": "Что такое энтропия?", "sec": 0.30, "meta": {"intent": "web", "tool": "", "verified": True}, "resp": "Энтропия - мера неопределённости.", "err": None},
            {"cmd": "Найди книгу 48 законов власти", "sec": 0.20, "meta": {"intent": "web", "tool": "web_search", "verified": False}, "resp": "Источник недоступен. Задача сохранена для повторения: research-abc123", "err": None},
            {"cmd": "Неизвестная команда", "sec": 0.30, "meta": {"intent": "none", "tool": "", "verified": False}, "resp": "Сейчас разберусь - готовлю capability research.", "err": None},
            {"cmd": "Открой блокнот и поставь музыку", "sec": 0.82, "meta": {"intent": "app", "tool": "command_batch", "verified": True}, "resp": "Открой блокнот: проверено. Поставь музыку: проверено.", "err": None},
        ]
        for item in results:
            item["failures"] = _assert_behavior(item)
        report = {"pass": not any(item["failures"] for item in results), "offline": True,
                  "results": results, "latency": latency_summary([r["sec"] * 1000 for r in results], path="fast")}
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["pass"] else 1

    settings = load_config()
    settings.ensure_directories()
    # Отключаем TTS-звук на время замера (чистая latency текста).
    try:
        settings.voice.tts_always_on = False
        settings.voice.tts_enabled = False
    except Exception:
        pass

    t0 = time.perf_counter()
    orch = Orchestrator(settings, output_callback=_capture)
    orch.start()
    boot = time.perf_counter() - t0
    print(f"BOOT_SEC={boot:.2f}")

    # Warm the real GUI surface once outside the fast-path sample. Windows
    # packaged apps can spend 1–3 seconds creating their first shell process;
    # the acceptance budget measures the reusable second run, while this
    # preflight remains visible as independent evidence.
    preflight_started = time.perf_counter()
    CAPTURED.clear()
    preflight_state = None
    preflight_error = None
    try:
        preflight_state = orch.handle_input("Открой блокнот")
    except Exception as exc:  # noqa: BLE001
        preflight_error = f"{type(exc).__name__}: {exc}"
    preflight = {
        "cmd": "Открой блокнот",
        "sec": round(time.perf_counter() - preflight_started, 3),
        "err": preflight_error,
        "meta": {
            "tool": preflight_state.get("tool") if isinstance(preflight_state, dict) else None,
            "verified": preflight_state.get("verified") if isinstance(preflight_state, dict) else False,
            "mode": preflight_state.get("mode") if isinstance(preflight_state, dict) else None,
        },
        "resp": " | ".join(CAPTURED)[:400],
        "cold_start": True,
    }
    preflight["failures"] = []
    if preflight_error or preflight["meta"]["verified"] is not True:
        preflight["failures"].append("real GUI preflight was not verified")
    print(f"PREFLIGHT: {preflight}")

    results = []
    for cmd in COMMANDS:
        CAPTURED.clear()
        start = time.perf_counter()
        err = None
        state = None
        try:
            state = orch.handle_input(cmd)
        except Exception as exc:  # noqa: BLE001
            err = f"{type(exc).__name__}: {exc}"
        elapsed = time.perf_counter() - start
        resp = " | ".join(CAPTURED) if CAPTURED else ""
        meta = {}
        try:
            if isinstance(state, dict):
                meta = {
                    "intent": state.get("intent"),
                    "tier": state.get("tier") or state.get("model_used"),
                    "tool": state.get("tool"),
                    "verified": state.get("verified"),
                    "mode": state.get("mode"),
                    "error": state.get("error"),
                }
        except Exception:
            pass
        item = {
            "cmd": cmd,
            "sec": round(elapsed, 2),
            "err": err,
            "meta": meta,
            "resp": (resp[:400] if resp else ""),
        }
        item["failures"] = _assert_behavior(item)
        results.append(item)
        print(f"\n=== CMD: {cmd}")
        print(f"    TIME: {elapsed:.2f}s  ERR: {err}")
        print(f"    META: {meta}")
        print(f"    RESP: {resp[:400]!r}")

    orch.shutdown()

    lat = [r["sec"] for r in results if r["err"] is None]
    if lat:
        print(f"\nSUMMARY latency: min={min(lat):.2f} avg={sum(lat)/len(lat):.2f} max={max(lat):.2f}")
    fast_values = [r["sec"] * 1000 for r in results if r["cmd"] in {"Открой блокнот", "Который час?", "Поставь музыку, настроения нет"} and not r["err"]]
    report = {
        "pass": not preflight["failures"] and not any(r["failures"] for r in results),
        "offline": bool(getattr(settings, "offline_mode", False)),
        "boot_sec": round(boot, 3),
        "runtime_diagnostics": orch.runtime_diagnostics(),
        "preflight": preflight,
        "results": results,
        "latency": latency_summary(fast_values, path="fast") if fast_values else {},
        "budgets": {"fast": {"p50_ms": 600, "p95_ms": 1000, "hard_max_ms": 1500}},
    }
    target = Path(args.output)
    if not target.is_absolute():
        target = PROJECT_ROOT / target
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE {target}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
