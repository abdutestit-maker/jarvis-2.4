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
import re
import threading
import time
from typing import Any, Dict, Optional, Set
from urllib.parse import urlparse

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
        # Settings — единый runtime-объект, переданный Orchestrator. Его
        # обновление через WS сразу доступно CouncilRouter/Agent без
        # параллельного формата или перезапуска процесса.
        orchestrator_settings = getattr(orchestrator, "_settings", None)
        self._settings: Settings = (
            orchestrator_settings if orchestrator_settings is not None else Settings()
        )
        self._host = host
        self._port = port
        self._clients: Set[Any] = set()
        self._lock = threading.RLock()
        # task_id, для которых уже отправлен event:jarvis:start (чтобы не
        # дублировать start на каждый токен в streaming-пути).
        self._streaming_started: Set[str] = set()
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
            # ВАЖНО (P5 §5.4/frontend): фронт рендерит пузырь ответа ТОЛЬКО после
            # event:jarvis:start (useBackendBridge создаёт пузырь по start, а token/end
            # лишь обновляют его). Без start пузырь не создаётся и ответ не виден в
            # чате. Поэтому шлём start непосредственно перед end (fast-path без
            # токенов), чтобы контракт совпадал с streaming-путём.
            self._emit({
                "type": "event",
                "event": {
                    "type": "event:jarvis:start",
                    "payload": {
                        "id": f"sync-{_now_ms()}",
                        "kind": "jarvis",
                        "content": "",
                    },
                    "timestamp": _now_ms(),
                },
            })
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

    def _cloud_settings_payload(self) -> Dict[str, Any]:
        """Безопасное представление cloud-профиля для UI.

        API-ключ намеренно НИКОГДА не входит в WebSocket-ответ: клиенту
        доступны лишь флаг наличия и маска последних четырёх символов.
        """
        provider = self._settings.tier_providers.get("analyst")
        key = self._settings.api_keys.get(provider) or ""
        suffix = key[-4:] if key else ""
        return {
            "provider": provider,
            "base_url": self._settings.api_endpoints.get(provider) or "",
            "model": self._settings.model_tiers.get("analyst") or "",
            "has_api_key": bool(key),
            "api_key_masked": f"••••{suffix}" if key else "",
        }

    @staticmethod
    def _validate_cloud_provider(value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("provider должен быть строкой")
        provider = value.strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", provider):
            raise ValueError("provider должен содержать латинские буквы, цифры, '_' или '-'")
        if provider == "local":
            raise ValueError("provider 'local' нельзя назначить облачному профилю")
        return provider

    @staticmethod
    def _validate_base_url(value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("base_url должен быть строкой")
        url = value.strip().rstrip("/")
        if not url or len(url) > 2048:
            raise ValueError("base_url должен содержать от 1 до 2048 символов")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("base_url должен быть корректным http(s) URL")
        if parsed.username or parsed.password:
            raise ValueError("base_url не должен содержать учётные данные")
        return url

    @staticmethod
    def _validate_model(value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("model должен быть строкой")
        model = value.strip()
        if not model or len(model) > 256:
            raise ValueError("model должен содержать от 1 до 256 символов")
        return model

    def _update_cloud_settings(self, patch: Any) -> Dict[str, Any]:
        """Валидирует и атомарно применяет allowlist-патч cloud-профиля."""
        if not isinstance(patch, dict):
            raise ValueError("settings должен быть объектом")

        allowed = {"provider", "base_url", "model", "api_key", "clear_api_key"}
        unknown = set(patch) - allowed
        if unknown:
            raise ValueError(f"Недопустимые поля settings: {', '.join(sorted(unknown))}")

        provider = self._settings.tier_providers.get("analyst")
        if "provider" in patch:
            provider = self._validate_cloud_provider(patch["provider"])

        endpoint = self._settings.api_endpoints.get(provider) or ""
        if "base_url" in patch:
            endpoint = self._validate_base_url(patch["base_url"])

        model = self._settings.model_tiers.get("analyst") or ""
        if "model" in patch:
            model = self._validate_model(patch["model"])

        clear_key = patch.get("clear_api_key", False)
        if not isinstance(clear_key, bool):
            raise ValueError("clear_api_key должен быть boolean")
        key_patch = patch.get("api_key")
        if key_patch is not None and not isinstance(key_patch, str):
            raise ValueError("api_key должен быть строкой")
        if isinstance(key_patch, str) and len(key_patch) > 512:
            raise ValueError("api_key не должен превышать 512 символов")

        # Не делаем частичную запись: весь набор валидирован до мутации.
        self._settings.tier_providers.analyst = provider
        self._settings.api_endpoints.__setattr__(provider, endpoint)
        self._settings.model_tiers.analyst = model
        if clear_key:
            self._settings.api_keys.__setattr__(provider, "")
        elif isinstance(key_patch, str) and key_patch.strip():
            self._settings.api_keys.__setattr__(provider, key_patch.strip())
        # Пустая password-строка означает «ключ не менять».

        self._settings.save_config()
        # Новые ключ/base URL должны использоваться следующим запросом, а не
        # остаться в кэше RemoteAPIBackend.
        from core.llm.factory import clear_backend_cache

        clear_backend_cache()
        return self._cloud_settings_payload()

    async def _on_message(self, ws, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await ws.send(json.dumps({"type": "error", "message": "bad json"}))
            return

        mtype = (msg.get("type") or "").lower()
        if mtype == "settings:get":
            await ws.send(json.dumps({"type": "settings", "settings": self._cloud_settings_payload()}))
        elif mtype == "settings:update":
            try:
                settings = self._update_cloud_settings(msg.get("settings"))
            except Exception as exc:
                # Не логируем payload: в нём мог быть API-ключ.
                log.warning("Отклонено обновление cloud-настроек: %s", exc)
                await ws.send(json.dumps({"type": "error", "message": str(exc)}))
                return
            await ws.send(json.dumps({"type": "settings:saved", "ok": True, "settings": settings}))
        elif mtype == "command":
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
            # Фронт создаёт пузырь ответа только после event:jarvis:start
            # (useBackendBridge). Шлём start ровно один раз — перед первым
            # токеном этого task_id.
            if event.task_id not in self._streaming_started:
                self._streaming_started.add(event.task_id)
                self._emit({
                    "type": "event",
                    "event": {
                        "type": "event:jarvis:start",
                        "payload": {
                            "id": event.task_id,
                            "kind": "jarvis",
                            "content": "",
                        },
                        "timestamp": _now_ms(),
                    },
                })
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
