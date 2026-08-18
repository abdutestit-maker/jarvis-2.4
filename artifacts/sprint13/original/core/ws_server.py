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
from uuid import uuid4

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
        # Sprint 1: per-request контекст (thread-local). Каждый WS-запрос
        # обрабатывается в своём потоке executor'а, поэтому параллельные
        # запросы имеют независимые correlation ID и не перемешиваются.
        self._tls = threading.local()
        # Sprint 5: приветствие отправляется ОДИН раз за сессию сервера —
        # при подключении первого клиента (не при каждом открытии окна).
        self._greeted = False
        self._system_monitor = None
        self._stt_engine = None
        try:
            from core.voice.stt import STTEngine
            candidate = STTEngine(self._settings)
            if candidate.is_available(): self._stt_engine = candidate
        except Exception as exc:
            log.debug("STT startup probe failed: %s", exc)
        # Перехватываем output_callback, чтобы синхронный fast-path
        # ответ тоже доходил до фронта (handle_input сам его печатает).
        self._orig_output = orchestrator._output_callback

        def _emit_jarvis_event(etype: str, rid: str, payload: Dict[str, Any]) -> None:
            self._emit({
                "type": "event",
                "event": {
                    "type": etype,
                    "payload": {"id": rid, "kind": "jarvis", **payload},
                    "timestamp": _now_ms(),
                },
            })

        def _cb(text: str) -> None:
            # Оркестратор уже отправил typed AssistantOutput в TTS. Callback
            # отвечает только за UI transport — повторная raw озвучка запрещена.
            try:
                self._orig_output(text)
            except Exception:
                pass
            # Транслируем в события J.A.R.V.I.S.
            # ВАЖНО (P5 §5.4/frontend): фронт рендерит пузырь ответа ТОЛЬКО после
            # event:jarvis:start (useBackendBridge создаёт пузырь по start, а
            # token/end лишь обновляют его).
            #
            # Sprint 1 STEP 1: correlation ID создаётся ОДИН РАЗ на весь
            # логический ответ (uuid, без timestamp-гонки). Если этот запрос
            # стримился (пузырь с rid уже открыт) — закрываем ЕГО тем же rid.
            tls = self._tls
            rid = getattr(tls, "cid", None)
            if rid and getattr(tls, "started", False) and not getattr(tls, "ended", False):
                tls.ended = True
                _emit_jarvis_event("event:jarvis:end", rid, {"content": text, "model": "local"})
                self._emit({"type": "state", "state": "idle"})
                return
            # Стримленная миссия этого потока: финальный текст закрывает
            # её пузырь (тот же task_id), не создавая второй ответ.
            consume = getattr(self._orch, "consume_streamed_mission", None)
            mission_rid = consume() if callable(consume) else None
            if mission_rid:
                self._streaming_started.discard(mission_rid)
                _emit_jarvis_event("event:jarvis:end", mission_rid,
                                   {"content": text, "model": "local"})
                self._emit({"type": "state", "state": "idle"})
                return
            response_id = uuid4().hex
            _emit_jarvis_event("event:jarvis:start", response_id, {"content": ""})
            _emit_jarvis_event("event:jarvis:end", response_id, {"content": text, "model": "local"})
            self._emit({"type": "state", "state": "idle"})

        orchestrator._output_callback = _cb
        # Proactor is an existing system-trigger source.  Preserve its output
        # callback (notifications/TTS) and mirror it as a distinct UI event;
        # it never becomes a user command or an action request.
        proactor = getattr(orchestrator, "proactor", None)
        if proactor is not None and hasattr(proactor, "_output"):
            original_proactive = proactor._output

            def _proactive_cb(text: str) -> None:
                original_proactive(text)
                self._emit({
                    "type": "event",
                    "event": {
                        "type": "event:system_initiated",
                        "payload": {"text": text},
                        "timestamp": _now_ms(),
                    },
                })

            proactor._output = _proactive_cb
        try:
            from core.triggers import SystemMonitor, SystemTriggerEngine
            configured = getattr(self._settings, "system_triggers", []) or []
            self._system_monitor = SystemMonitor(SystemTriggerEngine(configured, emit=lambda event, text: self._emit({"type": "event", "event": {"type": "event:system_initiated", "payload": {"text": text}, "timestamp": _now_ms()}}))) if configured else None
        except Exception as exc:
            log.warning("System triggers disabled: %s", exc)

    # ----------------------------------------------------------------- #
    #  Sprint 5 — ALWAYS-ON TTS + приветствие
    # ----------------------------------------------------------------- #

    def _tts_queue(self):
        """TTSQueue оркестратора (None, если недоступен)."""
        return getattr(self._orch, "_tts_queue", None)

    def _speak(self, output) -> None:
        """Typed greeting/system path; arbitrary WS messages are never spoken."""
        try:
            from core.voice.output import AssistantOutput
            if not isinstance(output, AssistantOutput):
                raise TypeError("WS speech boundary accepts AssistantOutput only")
            voice = getattr(self._settings, "voice", None)
            if not getattr(voice, "tts_enabled", True):
                return
            if not getattr(voice, "tts_always_on", True):
                return
            tts = self._tts_queue()
            if tts is None:
                return
            tts.add_output(output)
        except Exception as exc:  # noqa: BLE001 — TTS не ломает ответы
            log.debug("TTS-озвучка пропущена: %s", exc)

    def _tts_interrupt(self) -> None:
        """Barge-in (Sprint 5 STEP 5.3): прерывает текущую речь и очередь."""
        try:
            tts = self._tts_queue()
            if tts is not None:
                tts.interrupt()
        except Exception as exc:  # noqa: BLE001
            log.debug("TTS-interrupt пропущен: %s", exc)

    def _send_startup_greeting(self) -> None:
        """Приветствие при старте сессии (Sprint 5 STEP 3).

        Условия: launcher.greeting_enabled, ещё не отправляли, профиль
        читается для персонального обращения. Идёт через обычный WS
        pipeline (event:jarvis:start/end) и озвучивается always-on TTS.
        """
        launcher = getattr(self._settings, "launcher", None)
        if not getattr(launcher, "greeting_enabled", True):
            return
        try:
            from core.voice.greeting import build_startup_greeting
            return_context = None
            try:
                living = getattr(self._orch, "_living", None)
                if living is not None:
                    return_context = living.context.return_context(min_confidence=0.75)
            except Exception as exc:  # context is optional; ordinary greeting remains
                log.debug("Контекст прошлого сеанса недоступен: %s", exc)
            text = build_startup_greeting(self._settings, return_context=return_context)
        except Exception as exc:  # noqa: BLE001
            log.warning("Приветствие не сформировано: %s", exc)
            return
        rid = uuid4().hex
        log.info("Приветствие сессии: %s", text)
        self._emit({
            "type": "event",
            "event": {
                "type": "event:jarvis:start",
                "payload": {"id": rid, "kind": "jarvis", "content": ""},
                "timestamp": _now_ms(),
            },
        })
        self._emit({
            "type": "event",
            "event": {
                "type": "event:jarvis:end",
                "payload": {"id": rid, "kind": "jarvis",
                            "content": text, "model": "local"},
                "timestamp": _now_ms(),
            },
        })
        from core.voice.output import AssistantOutput
        self._speak(AssistantOutput.natural(text))

    # ----------------------------------------------------------------- #
    #  Управление подключениями
    # ----------------------------------------------------------------- #
    async def _handler(self, ws):
        peer = getattr(ws, "remote_address", "?")
        log.info("WS клиент подключён: %s", peer)
        with self._lock:
            self._clients.add(ws)
            # Sprint 5 STEP 3: приветствие — ОДИН раз за сессию сервера,
            # при подключении первого клиента (не при каждом открытии окна).
            first_client = len(self._clients) == 1 and not self._greeted
            if first_client:
                self._greeted = True
        try:
            await ws.send(json.dumps({"type": "state", "state": "idle"}))
            try:
                from core.memory.profile import load_profile
                has_name = bool((load_profile(self._settings).get("name") or "").strip())
            except Exception:
                has_name = False
            await ws.send(json.dumps({"type": "profile", "has_name": has_name}))
            if first_client:
                # Пауза, чтобы фронт успел подписаться на события.
                await asyncio.sleep(0.5)
                self._send_startup_greeting()
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

    # ----------------------------------------------------------------- #
    #  Sprint 5 — Launcher API (autostart / hotkey / greeting)
    # ----------------------------------------------------------------- #

    def _launcher_payload(self) -> Dict[str, Any]:
        """Текущая конфигурация launcher для UI."""
        launcher = getattr(self._settings, "launcher", None)
        if launcher is None:
            return {}
        return {
            "autostart": getattr(launcher, "autostart", False),
            "hotkey": getattr(launcher, "hotkey", "Ctrl+Space"),
            "backend_command": getattr(launcher, "backend_command", []),
            "backend_workdir": getattr(launcher, "backend_workdir", ""),
            "greeting_enabled": getattr(launcher, "greeting_enabled", True),
        }

    def _update_launcher(self, patch: Any) -> Dict[str, Any]:
        """Валидирует и применяет allowlist-патч launcher config."""
        if not isinstance(patch, dict):
            raise ValueError("launcher должен быть объектом")
        allowed = {"autostart", "hotkey", "greeting_enabled"}
        unknown = set(patch) - allowed
        if unknown:
            raise ValueError(f"Недопустимые поля launcher: {', '.join(sorted(unknown))}")

        launcher = self._settings.launcher
        if "autostart" in patch:
            v = patch["autostart"]
            if not isinstance(v, bool):
                raise ValueError("autostart должен быть boolean")
            launcher.autostart = v
            self._apply_autostart(v)

        if "hotkey" in patch:
            v = patch["hotkey"]
            if not isinstance(v, str) or not v.strip():
                raise ValueError("hotkey должен быть непустой строкой")
            launcher.hotkey = v.strip()

        if "greeting_enabled" in patch:
            v = patch["greeting_enabled"]
            if not isinstance(v, bool):
                raise ValueError("greeting_enabled должен быть boolean")
            launcher.greeting_enabled = v

        self._settings.save_config()
        return self._launcher_payload()

    @staticmethod
    def _apply_autostart(enable: bool) -> None:
        """HKCU\\...\\Run — автозапуск Jarvis при логоне пользователя.

        Запись/удаление через winreg; на других ОС — no-op (безопасно).
        """
        import sys
        if sys.platform != "win32":
            return
        try:
            import winreg  # type: ignore[import-untyped]
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            name = "JARVIS"
            exe = sys.executable  # python.exe из текущего venv
            # Команда: python -m core.ws_server из backend_workdir
            cmd = f'"{exe}" -m core.ws_server'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                                winreg.KEY_SET_VALUE) as hk:
                if enable:
                    winreg.SetValueEx(hk, name, 0, winreg.REG_SZ, cmd)
                else:
                    try:
                        winreg.DeleteValue(hk, name)
                    except FileNotFoundError:
                        pass
        except Exception as exc:  # noqa: BLE001
            log.warning("HKCU autostart %s не удался: %s",
                        "запись" if enable else "удаление", exc)

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
        if mtype == "voice_input":
            text = (msg.get("text") or "").strip()
            confidence = msg.get("confidence", 1.0)
            if isinstance(confidence, (int, float)) and confidence < 0.7:
                await ws.send(json.dumps({"type": "event", "event": {"type": "event:system", "payload": {"content": "Не расслышал, повтори."}, "timestamp": _now_ms()}}))
                return
            mtype = "command"
            msg["text"] = text
        elif mtype == "wake_word_detected":
            self._emit({"type": "event", "event": {"type": "event:wake_word_detected", "payload": {}, "timestamp": _now_ms()}})
            return
        elif mtype == "voice_listen":
            if not getattr(getattr(self._settings, "stt", None), "enabled", False) and not getattr(getattr(self._settings, "voice", None), "stt_enabled", False):
                return
            loop = self._loop
            def _listen() -> None:
                try:
                    if self._stt_engine is None: return
                    text, confidence = self._stt_engine.transcribe_with_confidence_from_mic()
                    self._emit({"type": "voice_input", "text": text, "confidence": confidence})
                except Exception as exc:
                    self._emit({"type": "error", "message": str(exc)})
            if loop is not None: loop.call_soon_threadsafe(lambda: loop.run_in_executor(None, _listen))
            return
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
            # Sprint 5 STEP 5.3 (barge-in): новый ввод прерывает текущую
            # речь Джарвиса — новая команда важнее договариваемой фразы.
            self._tts_interrupt()
            # Единый путь (P5 §5.7): тот же handle_input, что и в REPL.
            # Гоним через executor, чтобы не блокировать asyncio-цикл
            # во время модельного inference, и ловим возвращаемый state,
            # чтобы не потерять confirmation_id (P5 §5.6) при синхронном
            # fast-path (mission=None -> EVENT_CONFIRMATION_REQUIRED не
            # эмитится в TaskEvent).
            loop = self._loop

            def _dispatch(t: str) -> None:
                # Sprint 1 STEP 1/2: один correlation ID на весь логический
                # ответ. Sink принимает кумулятивный текст реального SSE-потока
                # модели и транслирует его в event:jarvis:token. Если бэкенд
                # не поддерживает streaming — sink ни разу не вызовется и
                # ответ пойдёт классическим start/end через _cb (fallback).
                tls = self._tls
                rid = uuid4().hex
                tls.cid = rid
                tls.started = False
                tls.ended = False
                tls.streamed = ""

                def _sink(visible: str) -> None:
                    tls.streamed = visible
                    if not tls.started:
                        tls.started = True
                        self._emit({
                            "type": "event",
                            "event": {
                                "type": "event:jarvis:start",
                                "payload": {"id": tls.cid, "kind": "jarvis", "content": ""},
                                "timestamp": _now_ms(),
                            },
                        })
                    self._emit({
                        "type": "event",
                        "event": {
                            "type": "event:jarvis:token",
                            "payload": {"id": tls.cid, "token": visible},
                            "timestamp": _now_ms(),
                        },
                    })

                install = getattr(self._orch, "install_stream_sink", None)
                try:
                    if callable(install):
                        install(_sink)
                    state = self._orch.handle_input(t)
                    if isinstance(state, dict) and state.get("assistant_output"):
                        # Typed diagnostics channel for Developer Mode. The
                        # frontend has no speech synthesis path for this event.
                        self._emit({
                            "type": "assistant_output",
                            "output": state["assistant_output"],
                        })
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
                finally:
                    clear = getattr(self._orch, "clear_stream_sink", None)
                    if callable(clear):
                        try:
                            clear()
                        except Exception:  # pragma: no cover
                            pass
                    # Пузырь остался открытым (экзотический путь без _cb):
                    # закрываем честно накопленным текстом.
                    if getattr(tls, "started", False) and not getattr(tls, "ended", False):
                        tls.ended = True
                        self._emit({
                            "type": "event",
                            "event": {
                                "type": "event:jarvis:end",
                                "payload": {
                                    "id": tls.cid,
                                    "kind": "jarvis",
                                    "content": tls.streamed or "Сэр, ответ не сформирован.",
                                    "model": "local",
                                },
                                "timestamp": _now_ms(),
                            },
                        })
                        self._emit({"type": "state", "state": "idle"})
                    tls.cid = None
                    tls.started = False
                    tls.ended = False
                    tls.streamed = ""

            if loop is not None:
                loop.call_soon_threadsafe(
                    lambda t=text: loop.run_in_executor(None, _dispatch, t)
                )
        elif mtype == "confirm":
            cid = msg.get("confirmation_id")
            approve = bool(msg.get("approve", False))
            if cid:
                # Sprint 1 STEP 3: подтверждение запускает реальное выполнение
                # инструмента — тоже через executor, чтобы не блокировать цикл.
                loop = self._loop

                def _dispatch_confirm(cid_: str, approve_: bool) -> None:
                    try:
                        self._orch.answer_confirmation(cid_, approve_)
                    except Exception as exc:
                        log.error("Ошибка ответа на подтверждение из WS: %s", exc)

                if loop is not None:
                    loop.call_soon_threadsafe(
                        lambda c=cid, a=approve: loop.run_in_executor(
                            None, _dispatch_confirm, c, a
                        )
                    )
                else:
                    _dispatch_confirm(cid, approve)
        elif mtype == "interrupt":
            # Отменяем все активные миссии (best-effort).
            try:
                for m in self._orch.list_missions(include_terminal=False):
                    self._orch.cancel_mission(m.task_id)
            except Exception as exc:  # pragma: no cover
                log.debug("interrupt error: %s", exc)
        elif mtype == "hotkey_pressed":
            # Sprint 5 STEP 4: overlay открыт глобальным hotkey — текущая
            # речь прерывается (пользователь перебивает, чтобы ввести новое).
            self._tts_interrupt()
        elif mtype == "ambient_initiated":
            # Sprint 6: system sources can ask the already-connected UI to
            # present a proactive phrase.  It is deliberately an event, not
            # a command: it never enters the action/conversation router.
            text = (msg.get("text") or "").strip()
            if text:
                self._emit({
                    "type": "event",
                    "event": {
                        "type": "event:system_initiated",
                        "payload": {"text": text},
                        "timestamp": _now_ms(),
                    },
                })
                self._speak(text)
        elif mtype == "screen_capture":
            if msg.get("permission") is not True:
                await ws.send(json.dumps({"type": "error", "message": "Screen capture requires explicit permission"}))
                return
            try:
                from core.vision.screen import ScreenCapture
                result = ScreenCapture().capture(permission=True)
                await ws.send(json.dumps({"type": "screen_capture", "text": result.text, "active_window": result.active_window, "url": result.url}))
            except Exception as exc:
                await ws.send(json.dumps({"type": "error", "message": str(exc)}))
        elif mtype == "first_launch":
            # The ritual owns exactly one durable datum: the name.  Save it
            # through the existing profile store instead of inventing a
            # second onboarding database or changing command routing.
            name = (msg.get("name") or "").strip()
            if name:
                try:
                    from core.memory.profile import update_profile
                    update_profile(self._settings, "name", name)
                except Exception as exc:  # pragma: no cover - disk edge
                    log.warning("Не удалось сохранить имя первого запуска: %s", exc)
        elif mtype == "launcher:get":
            await ws.send(json.dumps({"type": "launcher", "launcher": self._launcher_payload()}))
        elif mtype == "launcher:update":
            try:
                updated = self._update_launcher(msg.get("launcher"))
            except Exception as exc:
                log.warning("Отклонено обновление launcher: %s", exc)
                await ws.send(json.dumps({"type": "error", "message": str(exc)}))
                return
            await ws.send(json.dumps({"type": "launcher:saved", "ok": True,
                                      "launcher": updated}))
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
                # Sprint 1 STEP 3: один медленный/зависший клиент не должен
                # задерживать рассылку остальным (стриминг не должен
                # «замерзать» из-за backpressure одного соединения).
                await asyncio.wait_for(ws.send(data), timeout=5.0)
            except Exception:  # pragma: no cover - dropped/медленный клиент
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
        except Exception:  # pragma: no cover - loop закрыт
            # Sprint 1: потеря события больше не «тихая» — иначе UI слепнет
            # без следа в логах.
            log.warning("WS emit не удался (event loop закрыт?): type=%s",
                        payload.get("type"))

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
            if event.task_id in self._streaming_started:
                # Sprint 1 STEP 5: стримленный пузырь не должен висеть
                # открытым — закрываем понятным текстом, детали в лог.
                self._streaming_started.discard(event.task_id)
                self._emit({
                    "type": "event",
                    "event": {
                        "type": "event:jarvis:end",
                        "payload": {
                            "id": event.task_id,
                            "kind": "jarvis",
                            "content": "Сэр, задача не завершилась. Попробуйте ещё раз.",
                            "model": "local",
                        },
                        "timestamp": _now_ms(),
                    },
                })

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
            if event.task_id in self._streaming_started:
                # Sprint 1: миссия стримилась — пузырь с этим task_id уже
                # закрыт финальным output_callback (consume_streamed_mission).
                # Карточку-дубль не создаём.
                self._streaming_started.discard(event.task_id)
                if payload.get("status") == "cancelled":
                    self._emit({
                        "type": "event",
                        "event": {
                            "type": "event:jarvis:end",
                            "payload": {
                                "id": event.task_id,
                                "kind": "jarvis",
                                "content": "Задача отменена.",
                                "model": "local",
                            },
                            "timestamp": _now_ms(),
                        },
                    })
                return
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
        if self._system_monitor is not None:
            self._system_monitor.start()
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
        if self._system_monitor is not None:
            self._system_monitor.stop()
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
