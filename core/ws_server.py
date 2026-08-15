"""WebSocket-мост J.A.R.V.I.S. (P5 §5.2 / §5.4 / §5.7).

Поднимает асинхронный ``websockets`` сервер РЯДОМ с существующим
консольным REPL (main.py). Сервер не заменяет логику backend — он
переиспользует тот же ``Orchestrator`` и тот же единый путь
``Orchestrator.handle_input`` (P5 §5.7: оба входа — консоль и WS —
идут через один и тот же роутер ``Agent.execute`` -> ``ModelRouter``).

Протокол (JSON, одна строка на сообщение):

  Клиент -> Сервер:
    {"type": "command",  "text": "<текст команды>"}
    {"type": "confirm",  "confirmation_id": "<id>", "approve": true|false}
    {"type": "interrupt"}
    {"type": "ping"}

  Сервер -> Клиент (broadcast на всех подключённых):
    {"type": "state",    "state": "thinking"|"executing"|"streaming"|"idle"|"error"|"cloud"|"listening"}
    {"type": "event",    "event": { ... ActivityEvent-совместимый объект ... }}
    {"type": "confirmation_required", "confirmation_id": "<id>", "prompt": "...", "tool": "...", "risk": {...}}
    {"type": "vitals",   "vitals": {...}}
    {"type": "pong"}
    {"type": "error",    "message": "..."}

События миссий (TaskRuntime) транслируются в ``event``/``state``
сообщения, понятные фронтенду из ``jarvis/src/integrations/backend.ts``
(mapTransportEvent ожидает типы с префиксом ``state:`` / ``event:``).
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from typing import Any, Dict, Optional, Set

from config import load_config
from config.settings import Settings
from core.orchestrator import Orchestrator
from core.task_runtime import (
    EVENT_ACKNOWLEDGED,
    EVENT_CONFIRMATION_REQUIRED,
    EVENT_STREAM_CHUNK,
    EVENT_STREAM_END,
    EVENT_TASK_COMPLETED,
    EVENT_TASK_FAILED,
    EVENT_TASK_STARTED,
    TaskEvent,
)
from core.utils.logger import get_logger

try:
    import websockets  # type: ignore
    from websockets.server import serve
    _HAS_WS = True
except Exception:  # pragma: no cover - optional dep
    _HAS_WS = False

__all__ = ["JarvisWSServer", "run_server"]

log = get_logger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8771

# Маппинг статусов миссии -> entity state фронтенда
_STATUS_TO_STATE = {
    "queued": "thinking",
    "acknowledging": "thinking",
    "analyzing": "thinking",
    "planning": "thinking",
    "executing": "executing",
    "verifying": "executing",
    "repairing": "executing",
    "completed": "idle",
    "paused": "idle",
    "cancelled": "idle",
    "failed": "error",
}


def _now_ms() -> int:
    return int(time.time() * 1000)


class JarvisWSServer:
    """Мост Orchestrator <-> WebSocket-клиенты."""

    def __init__(
        self,
        orchestrator: Orchestrator,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
    ) -> None:
        self._orch = orchestrator
        self._host = host
        self._port = port
        self._clients: Set[Any] = set()
        self._lock = threading.RLock()
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._unsub: Optional[Any] = None
        # Перехватываем output_callback, чтобы синхронный fast-path
        # ответ тоже доходил до фронта (handle_input сам его печатает).
        self._orig_output = orchestrator._output_callback

        def _cb(text: str) -> None:
            # Дефолтный вывод оркестратора (print + TTS)
            try:
                self._orig_output(text)
            except Exception:
                pass
            # Транслируем в событие J.A.R.V.I.S. ответа.
            self._emit({
                "type": "event",
                "event": {
                    "type": "event:jarvis:end",
                    "payload": {
                        "id": f"sync-{_now_ms()}",
                        "kind": "jarvis",
                        "content": text,
                        "model": "local",
                    },
                    "timestamp": _now_ms(),
                },
            })
            self._emit({"type": "state", "state": "idle"})

        orchestrator._output_callback = _cb

    # ----------------------------------------------------------------- #
    #  Управление подключениями
    # ----------------------------------------------------------------- #
    async def _handler(self, ws):
        peer = getattr(ws, "remote_address", "?")
        log.info("WS клиент подключён: %s", peer)
        with self._lock:
            self._clients.add(ws)
        try:
            await ws.send(json.dumps({"type": "state", "state": "idle"}))
            async for raw in ws:
                await self._on_message(ws, raw)
        except websockets.exceptions.ConnectionClosed:  # type: ignore
            pass
        except Exception as exc:  # pragma: no cover - network edge
            log.error("WS соединение упало: %s", exc)
        finally:
            with self._lock:
                self._clients.discard(ws)
            log.info("WS клиент отключён: %s", peer)

    async def _on_message(self, ws, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await ws.send(json.dumps({"type": "error", "message": "bad json"}))
            return

        mtype = (msg.get("type") or "").lower()
        if mtype == "command":
            text = (msg.get("text") or "").strip()
            if not text:
                return
            # Единый путь (P5 §5.7): тот же handle_input, что и в REPL.
            # Гоним через executor, чтобы не блокировать asyncio-цикл
            # во время модельного inference, и ловим возвращаемый state,
            # чтобы не потерять confirmation_id (P5 §5.6) при синхронном
            # fast-path (mission=None -> EVENT_CONFIRMATION_REQUIRED не
            # эмитится в TaskEvent).
            loop = self._loop

            def _dispatch(t: str) -> None:
                try:
                    state = self._orch.handle_input(t)
                    if isinstance(state, dict) and state.get("needs_confirmation"):
                        self._emit({
                            "type": "confirmation_required",
                            "confirmation_id": state.get("confirmation_id"),
                            "prompt": state.get("response", ""),
                            "tool": "",
                            "risk": {},
                        })
                        self._emit({"type": "state", "state": "idle"})
                except Exception as exc:
                    log.error("Ошибка обработки команды из WS: %s", exc, exc_info=True)
                    self._emit({"type": "error", "message": str(exc)})

            if loop is not None:
                loop.call_soon_threadsafe(
                    lambda t=text: loop.run_in_executor(None, _dispatch, t)
                )
        elif mtype == "confirm":
            cid = msg.get("confirmation_id")
            approve = bool(msg.get("approve", False))
            if cid:
                try:
                    self._orch.answer_confirmation(cid, approve)
                except Exception as exc:
                    log.error("Ошибка ответа на подтверждение из WS: %s", exc)
        elif mtype == "interrupt":
            # Отменяем все активные миссии (best-effort).
            try:
                for m in self._orch.list_missions(include_terminal=False):
                    self._orch.cancel_mission(m.task_id)
            except Exception as exc:  # pragma: no cover
                log.debug("interrupt error: %s", exc)
        elif mtype == "ping":
            await ws.send(json.dumps({"type": "pong"}))

    # ----------------------------------------------------------------- #
    #  Исходящие сообщения
    # ----------------------------------------------------------------- #
    async def _broadcast(self, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload)
        with self._lock:
            targets = list(self._clients)
        for ws in targets:
            try:
                await ws.send(data)
            except Exception:  # pragma: no cover - dropped client
                pass

    def _emit(self, payload: Dict[str, Any]) -> None:
        """Потокобезопасно шлёт сообщение из любого потока."""
        loop = self._loop
        if loop is None or not self._running:
            return
        try:
            loop.call_soon_threadsafe(
                lambda p=payload: asyncio.ensure_future(self._broadcast(p))
            )
        except Exception:  # pragma: no cover
            pass

    def _on_task_event(self, event: TaskEvent) -> None:
        """Подписка на TaskRuntime -> трансляция в WS."""
        et = event.event_type
        payload = event.payload or {}

        if et in (EVENT_TASK_STARTED, EVENT_ACKNOWLEDGED):
            self._emit({"type": "state", "state": "thinking"})
        elif et == EVENT_TASK_COMPLETED:
            self._emit({"type": "state", "state": "idle"})
        elif et == EVENT_TASK_FAILED:
            self._emit({"type": "state", "state": "error"})

        if et == EVENT_STREAM_CHUNK:
            self._emit({
                "type": "event",
                "event": {
                    "type": "event:jarvis:token",
                    "payload": {"id": event.task_id, "token": payload.get("text", "")},
                    "timestamp": _now_ms(),
                },
            })
        elif et == EVENT_STREAM_END:
            self._emit({
                "type": "event",
                "event": {
                    "type": "event:jarvis:end",
                    "payload": {
                        "id": event.task_id,
                        "content": payload.get("text", ""),
                        "model": payload.get("model", "local"),
                    },
                    "timestamp": _now_ms(),
                },
            })
        elif et == EVENT_CONFIRMATION_REQUIRED:
            self._emit({
                "type": "confirmation_required",
                "confirmation_id": payload.get("confirmation_id"),
                "prompt": payload.get("prompt", ""),
                "tool": payload.get("tool", ""),
                "risk": payload.get("risk", {}),
            })
            self._emit({"type": "state", "state": "idle"})
        elif et == EVENT_TASK_COMPLETED:
            result = payload.get("result", "")
            self._emit({
                "type": "event",
                "event": {
                    "type": "event:jarvis",
                    "payload": {
                        "id": event.task_id,
                        "kind": "result",
                        "content": result if isinstance(result, str) else "",
                    },
                    "timestamp": _now_ms(),
                },
            })

    # ----------------------------------------------------------------- #
    #  Жизненный цикл
    # ----------------------------------------------------------------- #
    def start(self) -> None:
        if not _HAS_WS:
            log.error("websockets не установлен — WS-сервер недоступен")
            return
        if self._running:
            return
        # Запускаем оркестратор (он поднимет фоновые сервисы)
        self._orch.start()
        self._unsub = self._orch.subscribe_events(self._on_task_event)
        self._running = True

        def _run_loop() -> None:
            asyncio.run(self._serve_forever())

        self._thread = threading.Thread(target=_run_loop, name="jarvis-ws", daemon=True)
        self._thread.start()
        log.info("WS-сервер стартует на ws://%s:%s", self._host, self._port)

    async def _serve_forever(self) -> None:
        # ВАЖНО (P5 §5.2): этот метод ВСЕГДА вызывается из asyncio.run(),
        # который уже создал и запустил свой event-loop. Брать
        # asyncio.new_event_loop() здесь — ошибка: handler крутится на loop'е
        # asyncio.run, а self._loop указывал бы на другой, никогда не
        # запущенный loop, и все call_soon_threadsafe/_emit терялись бы.
        self._loop = asyncio.get_running_loop()
        async with serve(self._handler, self._host, self._port):  # type: ignore
            log.info("WS-сервер слушает ws://%s:%s", self._host, self._port)
            await asyncio.Future()  # run forever

    def shutdown(self) -> None:
        self._running = False
        if self._unsub is not None:
            try:
                self._unsub()
            except Exception:  # pragma: no cover
                pass
        self._orch.shutdown()


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Точка входа для автономного WS-сервера (без REPL)."""
    if not _HAS_WS:
        raise RuntimeError("websockets не установлен")
    settings: Settings = load_config()
    settings.ensure_directories()
    orch = Orchestrator(settings)
    server = JarvisWSServer(orch, host=host, port=port)
    server.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    run_server()
