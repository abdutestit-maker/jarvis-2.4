#!/usr/bin/env python
"""Production GUI -> WS -> local runtime smoke suite.

The suite talks to the same localhost WebSocket and origin as the Tauri GUI;
it does not instantiate mocks or call Orchestrator directly.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

import psutil
import websockets


ROOT = Path(__file__).resolve().parents[1]
WS_URL = "ws://127.0.0.1:8771"
WS_ORIGIN = "tauri://localhost"
ARTIFACT = ROOT / "artifacts" / "review_20260822" / "production_smoke_results.json"
LOG_PATHS = (
    ROOT / "data" / "logs" / "jarvis.log",
    ROOT / "jarvis" / "src-tauri" / "target" / "release" / "resources" / "jarvis-runtime" / "data" / "logs" / "jarvis.log",
)

FORBIDDEN_RESPONSES = {
    "слышу вас, сэр. канал связи работает.",
    "в порядке, сэр. готов помочь с задачей.",
    "всё в порядке, сэр. готов к следующей задаче.",
    "источник временно не ответил. задача сохранена для повторной попытки.",
    "сэр, сейчас не отвечает. попробуйте ещё раз.",
}

CASES = [
    ("conversation", "Привет, как дела?"),
    ("unknown_input", "квантовый чайник 7f3a говорит с северным окном"),
    ("question", "Почему небо голубое?"),
    ("conversation", "Сколько будет 37 умножить на 19?"),
    ("system_action", "Который час?"),
    ("system_action", "Какой статус системы?"),
    ("open_app", "Открой блокнот"),
    ("close_app", "Закрой блокнот"),
    ("complex", "Составь краткий план проверки цепочки GUI, WebSocket, локальной модели, действия, проверки и озвучивания без запуска команд"),
    ("question", "Объясни разницу между локальной моделью и runtime одним абзацем"),
]


def process_names() -> set[str]:
    names: set[str] = set()
    for process in psutil.process_iter(["name"]):
        try:
            name = str(process.info.get("name") or "").casefold()
        except (psutil.Error, OSError):
            continue
        if name:
            names.add(name)
    return names


def gui_running() -> bool:
    return any(
        str((p.info.get("name") or "")).casefold() == "jarvis-frontend.exe"
        for p in psutil.process_iter(["name"])
    )


def notepad_running() -> bool:
    return "notepad.exe" in process_names()


def log_marker() -> dict[str, tuple[int, int]]:
    marker: dict[str, tuple[int, int]] = {}
    for path in LOG_PATHS:
        try:
            stat = path.stat()
            marker[str(path)] = (stat.st_size, int(stat.st_mtime_ns))
        except OSError:
            marker[str(path)] = (0, 0)
    return marker


def has_new_tts(before: dict[str, tuple[int, int]]) -> bool:
    for path in LOG_PATHS:
        try:
            stat = path.stat()
            previous_size, previous_mtime = before.get(str(path), (0, 0))
            if int(stat.st_mtime_ns) <= previous_mtime and stat.st_size <= previous_size:
                continue
            with path.open("rb") as handle:
                handle.seek(previous_size)
                text = handle.read().decode("utf-8", errors="replace")
            if "Piper WAV generated" in text:
                return True
        except OSError:
            continue
    return False


async def wait_for_new_tts(before: dict[str, tuple[int, int]], timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if has_new_tts(before):
            return True
        await asyncio.sleep(0.25)
    return False


async def wait_for_runtime(ws, events: list[dict[str, Any]], timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        remaining = max(0.1, deadline - time.monotonic())
        raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        event = json.loads(raw)
        events.append(event)
        if event.get("type") == "runtime_status":
            latest = event
            if event.get("state") == "ready" and event.get("ready") is True:
                return event
            if event.get("state") == "unavailable":
                raise RuntimeError(f"runtime unavailable: {event.get('diagnostics')}")
    raise TimeoutError(f"runtime did not become ready: {latest}")


def event_type(event: dict[str, Any]) -> str:
    nested = event.get("event")
    return str(nested.get("type") if isinstance(nested, dict) else event.get("type") or "")


def event_payload(event: dict[str, Any]) -> dict[str, Any]:
    nested = event.get("event")
    payload = nested.get("payload") if isinstance(nested, dict) else event
    return payload if isinstance(payload, dict) else {}


def event_timestamp(event: dict[str, Any]) -> int:
    value = event.get("timestamp")
    if value is None and isinstance(event.get("event"), dict):
        value = event["event"].get("timestamp")
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def all_assistant_text(events: list[dict[str, Any]]) -> str:
    values: list[str] = []
    for event in events:
        if event_type(event) == "event:jarvis:end":
            content = event_payload(event).get("content")
            if content:
                values.append(str(content))
    return "\n".join(values).strip()


async def run_case(ws, kind: str, text: str, index: int) -> dict[str, Any]:
    before_tts = log_marker()
    sent_at = int(time.time() * 1000)
    await ws.send(json.dumps({"type": "command", "text": text}, ensure_ascii=False))
    events: list[dict[str, Any]] = []
    deadline = time.monotonic() + 150.0
    got_end = False
    got_assistant_output = False
    mission_ack = False
    got_result = False
    while time.monotonic() < deadline:
        raw = await asyncio.wait_for(ws.recv(), timeout=max(0.2, deadline - time.monotonic()))
        event = json.loads(raw)
        events.append(event)
        et = event_type(event)
        payload = event_payload(event)
        timestamp = event_timestamp(event)
        if et == "mission:ack" and (timestamp == 0 or timestamp >= sent_at - 1000):
            mission_ack = True
        if et == "event:jarvis:end" and timestamp >= sent_at - 1000:
            got_end = True
        if et == "event:result" and timestamp >= sent_at - 1000:
            got_result = True
        if event.get("type") == "assistant_output":
            got_assistant_output = True
        needs_result = kind in {"open_app", "close_app"}
        if got_end and got_assistant_output and (not needs_result or got_result):
            await asyncio.sleep(0.5)
            break

    text_out = all_assistant_text(events)
    assistant_outputs = [
        event.get("output") for event in events if event.get("type") == "assistant_output"
    ]
    routes = [event.get("route") for event in events if event.get("type") == "route"]
    tool_events = [event_payload(event) for event in events if event_type(event) == "event:tool"]
    result_events = [event_payload(event) for event in events if event_type(event) == "event:result"]
    errors = [event.get("message") for event in events if event.get("type") == "error"]
    lowered = text_out.casefold()
    checks = {
        "end_event": got_end,
        "non_empty_response": bool(text_out),
        "no_canned_response": lowered not in FORBIDDEN_RESPONSES and not any(
            phrase in lowered for phrase in FORBIDDEN_RESPONSES
        ),
        "no_transport_error": not errors,
        "tts_generated": await wait_for_new_tts(before_tts),
    }
    if kind in {"conversation", "unknown_input", "question", "complex"}:
        checks["local_reasoning_trace"] = any(
            isinstance(output, dict)
            and isinstance(output.get("debug"), dict)
            and (
                output["debug"].get("mode") in {"conversation", "quick_answer"}
                or any("conversation gate" in str(item) for item in output["debug"].get("trace", []))
            )
            for output in assistant_outputs
        )
    if kind == "open_app":
        await asyncio.sleep(1.5)
        checks["notepad_process_started"] = notepad_running() or any(
            "процесс запущен" in str((payload.get("verification") or {}).get("detail", "")).casefold()
            for payload in result_events
        )
        checks["open_app_tool"] = any(payload.get("tool") == "open_app" for payload in tool_events)
        checks["open_app_verified"] = any(payload.get("verified") is True for payload in result_events)
    if kind == "close_app":
        await asyncio.sleep(1.5)
        checks["notepad_process_stopped"] = not notepad_running()
        checks["close_app_tool"] = any(payload.get("tool") == "close_app" for payload in tool_events)
        checks["close_app_verified"] = any(payload.get("verified") is True for payload in result_events)
    passed = all(checks.values())
    return {
        "index": index,
        "kind": kind,
        "input": text,
        "sent_at_ms": sent_at,
        "passed": passed,
        "checks": checks,
        "response": text_out,
        "routes": routes,
        "assistant_outputs": assistant_outputs,
        "tool_events": tool_events,
        "result_events": result_events,
        "errors": errors,
        "event_types": sorted({event_type(event) for event in events}),
    }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ARTIFACT)
    args = parser.parse_args()
    results: list[dict[str, Any]] = []
    started = time.time()
    startup_events: list[dict[str, Any]] = []
    ready: dict[str, Any] = {}
    error: str | None = None
    try:
        if not gui_running():
            raise RuntimeError("production GUI process jarvis-frontend.exe is not running")
        async with websockets.connect(
            WS_URL, origin=WS_ORIGIN, open_timeout=15, close_timeout=5,
            ping_interval=None,
        ) as ws:
            ready = await wait_for_runtime(ws, startup_events, 120.0)
            if notepad_running():
                os.system("taskkill /IM notepad.exe /F >NUL 2>&1")
                await asyncio.sleep(0.8)
            for index, (kind, text) in enumerate(CASES, start=1):
                try:
                    result = await run_case(ws, kind, text, index)
                except Exception as exc:
                    result = {
                        "index": index,
                        "kind": kind,
                        "input": text,
                        "passed": False,
                        "checks": {"case_exception": False},
                        "response": "",
                        "routes": [],
                        "assistant_outputs": [],
                        "tool_events": [],
                        "result_events": [],
                        "errors": [f"{type(exc).__name__}: {exc}"],
                        "event_types": [],
                    }
                results.append(result)
                print(json.dumps({"index": index, "kind": kind, "passed": result["passed"], "checks": result["checks"]}, ensure_ascii=False))
                if not result["passed"]:
                    break
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    report = {
        "suite": "production_gui_e2e_smoke",
        "gui_process": "jarvis-frontend.exe",
        "ws_url": WS_URL,
        "ws_origin": WS_ORIGIN,
        "runtime_status": ready,
        "case_count": len(CASES),
        "completed_cases": len(results),
        "passed": len(results) == len(CASES) and all(item["passed"] for item in results),
        "duration_sec": round(time.time() - started, 3),
        "startup_events": startup_events,
        "results": results,
    }
    if error:
        report["error"] = error
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "completed_cases": len(results), "output": str(args.output)}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
