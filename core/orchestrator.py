"""Лёгкий оркестратор (без langchain/langgraph).

``Orchestrator`` — полный цикл обработки одного витка:
1. Intake: new_state, push в short_term
2. Memory: retrieve (заполняет retrieved_context)
3. Council: route (выбирает тир, генерирует ответ, решает про tools)
4. Tools: если LLM вернула tool_call — execute_tool, результат в контекст, ре-спрос модели
5. Response: генерация финального ответа
6. Memory: remember_exchange (сохраняем в долгую память)
7. Short-term: push assistant
8. TTS: add_to_queue (если включено)

Простой шаблон tool calling: если в ответе модели есть специальный маркер
``TOOL_CALL:{"name": "...", "args": {...}}`` — парсим, выполняем, добавляем результат
в контекст и переспрашиваем модель ОДИН раз.
"""

from __future__ import annotations

import json
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from config.settings import Settings
from core.actions import DEFAULT_REGISTRY, ToolContext, execute_tool
from core.agent import Agent, pick_acknowledgement
from core.capabilities import CAPABILITIES
from core.cognitive import CognitiveOrchestrator
from core.memory import MemoryRetriever
from core.model_router import ModelRouter, classify_conversation, estimate_complexity
from core.research import is_research_goal
from core.router import CouncilRouter
from core.router.intent_router import resolve_keyword_tool
from core.state import JarvisState, ActionResult, new_state, push_message, trim_short_memory
from core.task_runtime import Mission, MissionStatus, TaskEvent, TaskRuntime
from core.voice import (
    AssistantOutput, PiperTTS, SpeechRenderer, TTSQueue,
    assistant_output_from_outcome, show_toast,
)
from core.proactive import Proactor, BackgroundScheduler
from core.actions.reminders import TaskManager, get_default_manager
from core.utils.logger import get_logger
from core.brain import build_brain_fabric
from core.intelligence import EvidenceRecord, LatencyBudget, TutorEngine, UniversalIntake

__all__ = ["Orchestrator"]

log = get_logger(__name__)

# Регулярка для извлечения tool_call из ответа модели
_TOOL_CALL_PATTERN = re.compile(
    r"TOOL_CALL:\s*(\{.*?\})",
    re.DOTALL
)


class Orchestrator:
    """Единый оркестратор витка обработки запроса."""

    def __init__(
        self,
        settings: Settings,
        output_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Args:
            settings: конфигурация.
            output_callback: функция для вывода ответа пользователю (текст -> None).
                По умолчанию: print + TTS queue + toast.
        """
        self._settings = settings
        self._output_callback = output_callback or self._default_output

        # ЕДИНЫЙ роутер моделей — его делят CouncilRouter и Agent (P5 §5.7),
        # чтобы любой вход (консоль/WebSocket) маршрутизировался одинаково.
        self._brain = build_brain_fabric(settings)
        self._model_router = ModelRouter(settings, brain_fabric=self._brain)

        # Инициализация компонентов
        self._council = CouncilRouter(
            settings, model_router=self._model_router, brain_fabric=self._brain,
        )
        self._session = None  # будет создан в start()
        self._memory = MemoryRetriever(settings)
        self._registry = DEFAULT_REGISTRY

        # --- Агентное ядро J.A.R.V.I.S. 3.0 (§3, §6) ---
        # Агент исполняет миссии, TaskRuntime даёт им асинхронную жизнь.
        # НЕТ watchdog по умолчанию: миссия живёт столько, сколько нужно (§4).
        self._agent = Agent(
            settings, council=self._council, model_router=self._model_router,
            brain_fabric=self._brain,
        )
        # Shadow Engine is owned by Agent but its cadence belongs to the
        # orchestrator lifecycle, alongside other background services.
        self._shadow = self._agent._shadow
        self._shadow.attach_brain_fabric(self._brain)
        self._runtime = TaskRuntime(
            default_watchdog_sec=None,
            persistence_dir=settings.data_dir / "missions",
        )
        from core.living import LivingIntelligence
        self._living = LivingIntelligence(
            settings.data_dir / "living",
            task_runtime=self._runtime,
            shadow_engine=self._shadow,
            relationship_learner=self._agent.preference_learner,
        )
        self._runtime.subscribe(self._living.observe_mission_event)

        # Sprint 13: one continuity/state coordinator above the existing
        # owners. It references their real registries and policies rather than
        # cloning tools, memory, personality, attention, or Shadow behavior.
        self._cognitive = CognitiveOrchestrator(
            settings.data_dir / "cognitive",
            registry=self._registry,
            capability_registry=CAPABILITIES,
            providers={"shadow": self._shadow, "brain": self._brain},
            task_runtime=self._runtime,
            living_context=self._living.context,
            memory_hierarchy=self._agent._memory_hierarchy,
            capability_planner=self._agent._capability_planner,
            personality=self._agent.personality,
            shadow_engine=self._shadow,
            attention_manager=self._living.decisions.attention,
            goal_tracker=self._living.context.goal_tracker,
            brain_fabric=self._brain,
        )

        # TTS
        self._tts = PiperTTS(settings)
        self._speech_renderer = SpeechRenderer(settings.voice)
        self._tts_queue = TTSQueue(self._tts, renderer=self._speech_renderer)

        # Reminders
        self._task_manager = get_default_manager()

        # Proactive
        self._proactor = Proactor(
            settings=settings,
            council=self._council,
            output_callback=self._proactive_output,
            reminder_check_callback=self._check_reminders,
        )
        self._scheduler = BackgroundScheduler(
            settings=settings,
            task_manager=self._task_manager,
            nightly_callback=self._nightly_consolidation,
        )

        self._running = False
        self._lock = threading.Lock()
        self._warmup_thread: Optional[threading.Thread] = None
        self._warmup_diagnostics: Dict[str, Any] = {
            "backend": "unknown",
            "model": "local-qwen",
            "n_gpu_layers": 0,
            "warmup_ms": 0.0,
            "ready_before_first_request": False,
        }
        self._warmup_ready = threading.Event()
        self._intake = UniversalIntake()
        self._tutor = TutorEngine()

    # --------------------------------------------------------------------- #
    #  Публичный API
    # --------------------------------------------------------------------- #

    def install_stream_sink(self, sink) -> None:
        """Sprint 1: проброс stream-sink в агент для ТЕКУЩЕГО потока запроса."""
        install = getattr(self._agent, "install_stream_sink", None)
        if callable(install):
            install(sink)

    def clear_stream_sink(self) -> None:
        clear = getattr(self._agent, "clear_stream_sink", None)
        if callable(clear):
            clear()

    def _new_state(self, text: str) -> JarvisState:
        """Create a state with deterministic intent and bounded executive context."""
        state = new_state(text)
        state["intent"] = resolve_keyword_tool(text, text)
        try:
            state["task_contract"] = self._intake.classify(text).to_dict()
        except Exception as exc:
            log.debug("Universal intake skipped: %s", exc)
            state["task_contract"] = {}
        state["latency_budget"] = self._latency_budget_for(state.get("intent"), text)
        try:
            state["executive"] = self._agent.executive.snapshot()
        except Exception as exc:
            log.debug("Executive snapshot unavailable: %s", exc)
            state["executive"] = {}
        return state

    @staticmethod
    def _latency_budget_for(intent: Optional[str], text: str) -> Dict[str, Any]:
        fast = intent in {"app", "system", "media"} and len((text or "").strip()) <= 180
        if fast:
            budget = LatencyBudget("fast", 600.0, 1000.0, 1500.0)
        elif intent == "web" or is_research_goal(text):
            budget = LatencyBudget("research", 8000.0, 15000.0, 30000.0, 3000.0)
        else:
            budget = LatencyBudget("deliberate", 8000.0, 15000.0, 30000.0, 2500.0)
        return {
            "path": budget.path,
            "p50_ms": budget.p50_ms,
            "p95_ms": budget.p95_ms,
            "hard_max_ms": budget.hard_max_ms,
            "first_progress_p95_ms": budget.first_progress_p95_ms,
        }

    @staticmethod
    def _stamp_latency(state: JarvisState, started: float, path: str) -> JarvisState:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        state.setdefault("latency", {})["total_ms"] = round(elapsed_ms, 3)
        state["latency"]["path"] = path
        state.setdefault("evidence", []).append(EvidenceRecord(
            claim="request completed", source="orchestrator",
            latency_ms=elapsed_ms, path=path,
        ).to_dict())
        return state

    def _start_local_warmup(self) -> None:
        """Warm local backend before the first user request and record diagnostics."""
        if not bool(getattr(self._settings, "warmup_local_on_start", False)):
            return
        if self._warmup_thread is not None and self._warmup_thread.is_alive():
            return

        def _warm() -> None:
            started = time.perf_counter()
            try:
                from core.llm import Tier, get_llm_backend
                backend = get_llm_backend(self._settings, Tier.FAST)
                warm_up = getattr(backend, "warm_up", None)
                if callable(warm_up):
                    warm_up()
                    log.info("Local FAST backend warmed before first request")
                else:
                    log.debug("FAST backend has no warm_up hook: %s", type(backend).__name__)
                info = dict(getattr(backend, "runtime_info", lambda: {})() or {})
                configured_layers = int(info.get("n_gpu_layers", 0) or 0)
                self._warmup_diagnostics.update({
                    "backend": "cuda" if configured_layers != 0 else "cpu",
                    "model": str(getattr(backend, "model", "local-qwen")),
                    "n_gpu_layers": configured_layers,
                    "warmup_ms": round((time.perf_counter() - started) * 1000.0, 3),
                    "ready_before_first_request": True,
                    "runtime": info,
                })
            except Exception as exc:
                # Warmup is an optimisation; normal lazy loading remains valid.
                log.warning("Local backend warmup skipped: %s", exc)
                self._warmup_diagnostics.update({
                    "backend": "unavailable",
                    "warmup_ms": round((time.perf_counter() - started) * 1000.0, 3),
                    "error": f"{type(exc).__name__}: {exc}",
                    "ready_before_first_request": True,
                })
            finally:
                self._warmup_ready.set()

        # Startup pays the model load once; the first user request does not.
        _warm()

    def consume_streamed_mission(self):
        """Sprint 1: task_id миссии, стримленной в текущем потоке (или None)."""
        consume = getattr(self._agent, "consume_streamed_mission", None)
        if callable(consume):
            return consume()
        return None

    def start(self) -> None:
        """Запускает все фоновые сервисы."""
        with self._lock:
            if self._running:
                return
            self._running = True

            self._start_local_warmup()

            # Short-term memory manager
            max_size = getattr(getattr(self._settings, "limits", None), "short_memory_size", 20)
            from core.memory import SessionManager
            self._session = SessionManager(max_size=max_size)

            # TTS queue
            if self._settings.voice.tts_enabled and self._tts.is_available():
                self._tts_queue.start()
                log.info("TTS queue запущен")
            else:
                log.info("TTS отключен или недоступен")

            # Proactive
            self._proactor.start()
            self._scheduler.start()
            shadow_cfg = getattr(self._settings, "shadow", None)
            self._shadow.start(interval_sec=int(getattr(shadow_cfg, "interval_sec", 300)))
            self._living.start()

            log.info("Оркестратор запущен")

    def shutdown(self) -> None:
        """Корректно останавливает всё."""
        with self._lock:
            if not self._running:
                return
            self._running = False

        self._proactor.stop()
        self._scheduler.stop()
        self._living.stop()
        self._shadow.stop()
        self._tts_queue.stop(wait=True)
        try:
            self._brain.close()
        except Exception as exc:
            log.debug("Brain Fabric shutdown cleanup skipped: %s", exc)

        log.info("Оркестратор остановлен")

    def handle_input(self, text: str, *, channel: str = "text",
                     implicit_address: Optional[bool] = None) -> JarvisState:
        """Полный цикл обработки пользовательского ввода.

        Единый вход (§3, §5): любой ввод идёт через один реальный путь —
        агентную миссию (intent -> risk -> MODEL SELECTION -> tool ->
        verify -> repair -> memory). Чтобы лёгкие запросы («привет»,
        простые команды) не платили цену за тяжёлый цикл планирования и
        фоновый поток, они завершаются **синхронно** внутри того же
        агентного пути (fast path, §3) и возвращают JarvisState сразу.
        Всё, что требует реальной работы (анализ, задача, инструмент),
        уходит в фоновую миссию с мгновенным ACK, как и задумано в ТЗ
        (§4, §5, §23): пользователь видит ACK, а работа продолжается
        асинхронно, присылать progress/result.

        Args:
            text: текст от пользователя.

        Returns:
            JarvisState с заполненными полями: response, tts_text, error, etc.
        """
        request_started = time.perf_counter()
        if not self._running:
            self.start()

        # Отмечаем активность для proactor
        self._proactor.mark_user_activity()
        self._agent.set_user_context(self._living.context.current)

        # Production config opts into tiny deterministic replies for high-
        # frequency local probes.  Test/library Settings() stays untouched,
        # while the live path avoids a 40-second model round trip and prompt
        # contamination for greetings and elementary definitions.
        if bool(getattr(self._settings, "warmup_local_on_start", False)):
            quick = self._quick_local_reply(text)
            if quick is not None:
                return self._stamp_latency(self._direct_cognitive_response(text, quick), request_started, "fast")

        # Text arriving through the explicit chat/WS input is implicitly
        # addressed to ATLAS. Voice callers can use ``cognitive`` directly
        # with ``implicit_address=False`` before forwarding an utterance.
        if implicit_address is None:
            implicit_address = channel != "voice"
        cognitive_turn = self._cognitive.begin_interaction(
            text, channel=channel, implicit_address=implicit_address,
        )
        if cognitive_turn.action == "wait":
            state = self._new_state(text)
            state["response"] = ""
            state["tts_text"] = None
            state["addressed_to_atlas"] = False
            state["address_confidence"] = cognitive_turn.confidence
            return self._stamp_latency(state, request_started, "fast")
        if cognitive_turn.action in {"clarify", "self_knowledge"}:
            return self._stamp_latency(self._direct_cognitive_response(text, cognitive_turn.response), request_started, "fast")
        if cognitive_turn.action in {"continue", "retry"} and cognitive_turn.goal:
            text = cognitive_turn.goal

        # Sprint 11: natural queries are answered from evidence-backed local
        # structured context.  This path does not capture pixels or keystrokes.
        context_reply = self._living.answer_context(text)
        if context_reply is not None:
            response = str(context_reply["answer"])
            output = AssistantOutput.natural(response, speech_mode="focused")
            state = self._new_state(text)
            self._session.push("user", text)
            self._session.push("assistant", response)
            self._session.to_state(state)
            state["response"] = response
            state["context_evidence"] = list(context_reply.get("evidence") or [])
            spoken = self._queue_assistant_output(output)
            self._output_callback(response)
            state["tts_text"] = spoken
            state["assistant_output"] = output.to_dict()
            return self._stamp_latency(state, request_started, "fast")

        # Единый путь (§3): тяжёлая задача -> фон (мгновенный ACK),
        # лёгкая -> синхронно в том же агентном цикле (без фоновой миссии).
        run_background = self._should_run_background(text)
        self._living.observe_user_input(text, active_mission=run_background)
        self._agent.set_user_context(self._living.context.current)
        if run_background:
            mission = self.submit_goal(text)
            self._cognitive.state.current_goal = mission.goal
            self._cognitive.state.active_task = mission.current_step or "mission queued"
            self._cognitive.state.active_mission_id = mission.task_id
            self._cognitive.state.mission_state = mission.status.value
            self._cognitive.store.save(self._cognitive.state)
            ack = mission.acknowledgement or "Принято, сэр. Работаю."
            state = self._new_state(text)
            self._session.push("user", text)
            self._session.to_state(state)
            state["response"] = ack
            ack_output = AssistantOutput.natural(ack, speech_mode="focused")
            rendered = self._speech_renderer.render(ack_output)
            state["tts_text"] = rendered.text if rendered else None
            state["assistant_output"] = ack_output.to_dict()
            state["mission_id"] = mission.task_id
            return self._stamp_latency(state, request_started, "background")

        # Синхронный путь через единый агентный цикл
        # (intent -> risk -> MODEL SELECTION -> tool -> verify -> repair).
        outcome = self._agent.execute(text)
        if outcome.tool_used or outcome.mode in {"capability", "unknown_task"}:
            self._living.observe_capability_outcome(
                text, verified=outcome.verified,
                capability_id=outcome.tool_used or outcome.mode,
            )
            def _record_cognitive() -> None:
                self._cognitive.record_external_outcome(
                    goal=text, result=outcome.text, verified=bool(outcome.verified),
                    pending=[] if outcome.verified else ["independent result verification"],
                )
            if outcome.mode == "fast_path":
                threading.Thread(target=_record_cognitive,
                                 name="jarvis-cognitive-write", daemon=True).start()
            else:
                _record_cognitive()

        output = assistant_output_from_outcome(outcome)
        response = output.display_text or "(пустой ответ, сэр)."

        state = self._new_state(text)
        self._session.push("user", text)
        self._session.to_state(state)

        # Memory: remember exchange (не дублируем для confirmation-шагов)
        if not outcome.needs_confirmation:
            self._remember_exchange_background(text, response)

        # Short-term: push assistant
        self._session.push("assistant", response)
        self._session.to_state(state)

        spoken = self._queue_assistant_output(output)

        # Output callback (печать/тост)
        self._output_callback(response)

        state["response"] = response
        state["tts_text"] = spoken
        state["assistant_output"] = output.to_dict()
        state["tool"] = outcome.tool_used or ""
        state["verified"] = bool(outcome.verified)
        state["mode"] = outcome.mode
        if outcome.needs_confirmation:
            state["confirmation_id"] = getattr(outcome, "confirmation_id", None)
            state["needs_confirmation"] = True
        return self._stamp_latency(state, request_started, "background" if run_background else "fast")

    def _should_run_background(self, text: str) -> bool:
        """Решает, уходит ли задача в фоновую миссию (с ACK) или исполняется синхронно.

        В фон уходят исследовательские задачи и всё, что ModelRouter
        классифицирует как достаточно сложное (score >= LOCAL_THRESHOLD).
        Простые команды и приветствия исполняются синхронно — без
        тяжёлого цикла планирования и фонового потока (TEST 1).
        """
        goal = (text or "").strip()
        if not goal:
            return False
        # A conversational question must stay on the immediate path.  The
        # previous score-only check sent "почему..." to a background mission,
        # showing an ACK while the CPU model kept thinking for tens of seconds.
        intent = resolve_keyword_tool(goal, goal)
        conversational, _ = classify_conversation(goal, intent)
        if conversational:
            return False
        if is_research_goal(goal):
            return True
        cx = estimate_complexity(goal)
        # LOCAL_THRESHOLD из ModelRouter (0.35): выше — в фон.
        return cx.score >= 0.35

    @staticmethod
    def _quick_local_reply(text: str) -> Optional[str]:
        lowered = " ".join((text or "").casefold().split())
        # A pasted local installer/path is input context, not a question for
        # the language model.  Keep the response immediate and explicit so a
        # bare path never turns into a long generic safety monologue.
        if re.match(r"^(?:[a-z]:[\\/]|\\\\|/).+", (text or "").strip(), re.IGNORECASE):
            return (
                "Путь получен. Выберите действие: проверить файл, открыть папку "
                "или запустить установку."
            )
        if any(marker in lowered for marker in ("привет", "здравствуй", "ты меня слыш", "слышишь меня")):
            return "Слышу вас, сэр. Канал связи работает."
        if re.fullmatch(r"(?:как дела|как ты|как жизнь)\??", lowered):
            return "В порядке, сэр. Готов помочь с задачей."
        if re.fullmatch(r"почему небо голубое\??", lowered):
            return "Небо голубое из-за рэлеевского рассеяния: короткие синие волны рассеиваются в атмосфере сильнее."
        if re.fullmatch(r"(?:что нового|что делаешь)\??", lowered):
            return "Слушаю вас и готов к следующему шагу, сэр."
        if re.fullmatch(r"(?:спасибо|благодарю)[!.]?", lowered):
            return "Всегда пожалуйста, сэр."
        if re.fullmatch(r"(?:доброе утро|добрый день|добрый вечер)[!.]?", lowered):
            return "Добрый вечер, сэр. Я на связи." if "вечер" in lowered else "На связи, сэр."
        if "энтроп" in lowered and any(marker in lowered for marker in ("что такое", "объясни", "это")):
            return "Энтропия — мера неопределённости или числа возможных состояний системы."
        return None

    # --------------------------------------------------------------------- #
    #  Ответ на подтверждение HIGH-risk операции (§21)
    # --------------------------------------------------------------------- #

    def answer_confirmation(self, confirmation_id: str, approved: bool) -> Optional[JarvisState]:
        """Отвечает на ожидающее подтверждение HIGH-risk операции.

        Args:
            confirmation_id: id из состояния/события подтверждения.
            approved: True — выполнить, False — отклонить.

        Returns:
            JarvisState с результатом (или None, если подтверждение не найдено).
        """
        outcome = self._agent.answer_confirmation(confirmation_id, approved)
        if outcome is None:
            return None

        output = assistant_output_from_outcome(outcome)
        text = output.display_text or "(пустой ответ, сэр)."
        self._output_callback(text)
        spoken = self._queue_assistant_output(output)

        state: JarvisState = self._new_state("")
        state["response"] = text
        state["tts_text"] = spoken
        state["assistant_output"] = output.to_dict()
        if outcome.needs_confirmation:
            state["confirmation_id"] = getattr(outcome, "confirmation_id", None)
            state["needs_confirmation"] = True
        return state

    # --------------------------------------------------------------------- #
    #  Асинхронные миссии J.A.R.V.I.S. 3.0 (§3, §5, §6, §23)
    # --------------------------------------------------------------------- #

    def submit_goal(self, text: str,
                    on_event: Optional[Callable[[TaskEvent], None]] = None) -> Mission:
        """Принимает цель пользователя и запускает миссию АСИНХРОННО (§6).

        Возвращает управление немедленно — до завершения работы. Пользователь
        получает быстрое подтверждение (§5), а сама задача продолжает жить
        в фоне столько, сколько нужно (§4: 5 секунд, 2 минуты, 10 минут — норма).

        Args:
            text: цель человеческим языком.
            on_event: опциональный подписчик на события ЭТОЙ миссии (§23).

        Returns:
            ``Mission`` со статусом queued/acknowledging и готовым ``task_id``.
        """
        if not self._running:
            self.start()

        goal = (text or "").strip()
        self._proactor.mark_user_activity()

        # §5 — ACK формируется мгновенно. Если доступна локальная модель —
        # обогащается контекстной фразой (П1 §1.2); при сбое — canned fallback.
        intent = resolve_keyword_tool(goal, goal)
        ack = pick_acknowledgement(intent, goal=goal, settings=self._settings)

        # Подписка ставится ДО запуска, но task_id известен только после
        # submit(). Держим его в изменяемой ячейке и добираем уже
        # опубликованные события из mission.events, чтобы ничего не потерять.
        task_holder: Dict[str, Optional[str]] = {"id": None}
        seen: set[int] = set()
        unsubscribe: Optional[Callable[[], None]] = None

        if on_event is not None:
            def _filtered(event: TaskEvent) -> None:
                if task_holder["id"] is None or event.task_id != task_holder["id"]:
                    return
                marker = id(event)
                if marker in seen:
                    return
                seen.add(marker)
                on_event(event)

            unsubscribe = self._runtime.subscribe(_filtered)

        mission = self._runtime.submit(
            goal=goal,
            runner=self._mission_runner,
            metadata={"intent": intent, "source": "user",
                      "task_contract": self._intake.classify(goal).to_dict()},
        )
        mission.acknowledgement = ack

        if on_event is not None:
            task_holder["id"] = mission.task_id
            # Догоняем события, опубликованные во время submit().
            for event in list(mission.events):
                marker = id(event)
                if marker not in seen:
                    seen.add(marker)
                    try:
                        on_event(event)
                    except Exception as exc:
                        log.debug("Подписчик события упал: %s", exc)

        # Немедленное подтверждение пользователю (§5).
        self._output_callback(ack)
        self._queue_assistant_output(AssistantOutput.natural(ack, speech_mode="focused"))

        if unsubscribe is not None:
            mission.metadata["_unsubscribe"] = unsubscribe
        return mission

    def _mission_runner(self, mission: Mission, cancel: threading.Event) -> str:
        """Исполнитель миссии: агент + память + озвучка результата."""
        # Контекст диалога — в краткую память до начала работы.
        if self._session is not None:
            self._session.push("user", mission.goal)

        result_text = self._agent.run_mission(mission, cancel)

        verification = mission.verification or {}
        verified = bool(verification.get("verified") is True)
        if not cancel.is_set():
            self._cognitive.record_external_outcome(
                goal=mission.goal, result=result_text, verified=verified,
                pending=[] if verified else ["mission desired state"],
                mission_id=mission.task_id,
            )

        # Память и озвучка — только для завершённых, не отменённых задач.
        if not cancel.is_set():
            self._remember_exchange_background(mission.goal, result_text)
            if self._session is not None:
                self._session.push("assistant", result_text)

            self._output_callback(result_text)
            self._queue_assistant_output(AssistantOutput.natural(result_text))

        return result_text

    def _remember_exchange_background(self, user_text: str, assistant_text: str) -> None:
        """Persist long-term memory off the interactive/voice critical path."""
        if not user_text or not assistant_text:
            return

        def _write() -> None:
            try:
                self._memory.remember_exchange(user_text, assistant_text)
            except Exception as exc:
                log.warning("Не удалось сохранить обмен в память: %s", exc)

        worker = threading.Thread(target=_write, name="jarvis-memory-write", daemon=True)
        worker.start()

    def wait_for(self, task_id: str, timeout: Optional[float] = None) -> Optional[Mission]:
        """Ждёт завершения миссии.

        ВАЖНО (§4): ``timeout`` — это сколько ВЫЗЫВАЮЩИЙ готов ждать, а НЕ
        лимит на саму задачу. ``None`` = ждать сколько угодно.
        """
        return self._runtime.wait(task_id, timeout=timeout)

    def cancel_mission(self, task_id: str) -> bool:
        """Отменяет миссию по ID (§24)."""
        return self._runtime.cancel(task_id)

    def pause_mission(self, task_id: str) -> bool:
        paused = self._runtime.pause(task_id)
        if paused:
            mission = self._runtime.get(task_id)
            if mission is not None:
                self._cognitive.state.current_goal = mission.goal
                self._cognitive.state.active_task = mission.current_step or ""
                self._cognitive.state.active_mission_id = mission.task_id
                self._cognitive.state.mission_state = "paused"
                self._cognitive.suspend_current()
        return paused

    def skip_mission_step(self, task_id: str) -> bool:
        return self._runtime.skip_step(task_id)

    def explain_mission_step(self, task_id: str) -> str:
        return self._runtime.explain_current_step(task_id)

    def get_mission(self, task_id: str) -> Optional[Mission]:
        """Возвращает миссию по ID (для UI/статуса)."""
        return self._runtime.get(task_id)

    def list_missions(self, include_terminal: bool = True) -> List[Mission]:
        """Список миссий (§24 — поддержка нескольких задач одновременно)."""
        return self._runtime.list_missions(include_terminal=include_terminal)

    def subscribe_events(self, callback: Callable[[TaskEvent], None]) -> Callable[[], None]:
        """Подписка на ВСЕ события задач (§23). Возвращает unsubscribe()."""
        return self._runtime.subscribe(callback)

    @property
    def runtime(self) -> TaskRuntime:
        return self._runtime

    @property
    def living(self):
        """Sprint 11 integration facade for local context and proactive policy."""
        return self._living

    @property
    def cognitive(self) -> CognitiveOrchestrator:
        """Sprint 13 typed continuity and factual self-knowledge facade."""
        return self._cognitive

    @property
    def brain(self):
        """Sprint 15 model-orchestration facade owned by Cognitive Core."""
        return self._brain

    @property
    def agent(self) -> Agent:
        return self._agent

    # --------------------------------------------------------------------- #
    #  Внутренние методы
    # --------------------------------------------------------------------- #

    def _maybe_execute_tool(self, state: JarvisState) -> Optional[ActionResult]:
        """Проверяет, есть ли в ответе TOOL_CALL, и выполняет его.

        Формат в ответе модели:
            TOOL_CALL:{"name": "tool_name", "args": {"key": "value"}}

        Returns:
            ActionResult если инструмент выполнен, None если нет вызова.
        """
        response = state.get("response", "")
        match = _TOOL_CALL_PATTERN.search(response)
        if not match:
            return None

        try:
            tool_call = json.loads(match.group(1))
            tool_name = tool_call.get("name")
            args = tool_call.get("args", {})

            if not tool_name:
                log.warning("TOOL_CALL без имени: %s", tool_call)
                return None

            log.info("Выполнение tool_call: %s(%s)", tool_name, redact_args(args))

            context = ToolContext(
                user_id="default",
                settings=self._settings,
                state=state,
            )
            result = execute_tool(self._registry, tool_name, args, context)

            # Убираем маркер из ответа для чистоты
            clean_response = _TOOL_CALL_PATTERN.sub("", response).strip()
            state["response"] = clean_response

            return result

        except json.JSONDecodeError as exc:
            log.error("TOOL_CALL JSON decode ошибка: %s", exc)
            return None
        except Exception as exc:
            log.error("TOOL_CALL выполнение ошибка: %s", exc)
            return None

    def _reask_with_tool_result(
        self,
        state: JarvisState,
        tool_result: ActionResult,
    ) -> JarvisState:
        """Переспрашивает модель с результатом инструмента.

        Добавляет tool_result в контекст как tool message и прогоняет council снова.
        """
        # Формируем сообщение с результатом
        result_text = "Результат инструмента"
        if tool_result.ok:
            result_text += f": {tool_result.output}"
        else:
            result_text += f" (ошибка): {tool_result.error}"

        # Добавляем в short-term как tool message
        self._session.push("tool", result_text)
        self._session.to_state(state)

        # Обновляем memory retrieve (на тот случай, если инструмент добавил факты)
        state = self._memory.retrieve(state)

        # Переспрашиваем council
        state = self._council.route(state)
        return state

    def _default_output(self, text: str) -> None:
        """Дефолтный вывод: print + toast."""
        print(f"🤖 {text}")
        if self._settings.voice.tts_enabled:
            show_toast("АТЛАС", text[:100])

    def _proactive_output(self, text: str) -> None:
        """Вывод проактивного сообщения."""
        print(f"💡 [Проактивно] {text}")
        if self._settings.voice.tts_enabled:
            self._queue_assistant_output(
                AssistantOutput.natural(text, speech_mode="background")
            )
            show_toast("АТЛАС (проактивно)", text[:100])

    def _queue_assistant_output(self, output: AssistantOutput) -> Optional[str]:
        """Single typed path into TTS; returns the final safe spoken text."""
        rendered = self._speech_renderer.render(output)
        if rendered is None:
            return None
        if self._settings.voice.tts_enabled and self._tts.is_available():
            self._tts_queue.add_output(output)
        return rendered.text

    def _direct_cognitive_response(self, user_text: str, response: str) -> JarvisState:
        """Render a deterministic cognitive answer through the existing voice path."""
        output = AssistantOutput.natural(response, speech_mode="focused")
        state = self._new_state(user_text)
        if self._session is not None:
            self._session.push("user", user_text)
            self._session.push("assistant", response)
            self._session.to_state(state)
        spoken = self._queue_assistant_output(output)
        self._output_callback(response)
        state["response"] = response
        state["tts_text"] = spoken
        state["assistant_output"] = output.to_dict()
        state["cognitive_state"] = self._cognitive.state.to_safe_dict()
        return state

    def runtime_diagnostics(self) -> Dict[str, Any]:
        """Startup/model diagnostics for the Wave 0 verification report."""
        return {
            "warmup": dict(self._warmup_diagnostics),
            "warmup_ready": self._warmup_ready.is_set(),
            "budgets": {
                "fast": {"p50_ms": 600.0, "p95_ms": 1000.0, "hard_max_ms": 1500.0},
                "deliberate": {"first_progress_p95_ms": 2500.0, "p50_ms": 8000.0, "p95_ms": 15000.0},
                "research": {"first_progress_p95_ms": 3000.0, "source_timeout_ms": 8000.0},
                "background": {"enqueue_p95_ms": 100.0},
            },
        }

    @property
    def intake(self) -> UniversalIntake:
        return self._intake

    @property
    def tutor(self) -> TutorEngine:
        return self._tutor

    def teach(self, topic: str, *, level: str = "adaptive", mode: str = "socratic",
              session: Any = None) -> Dict[str, Any]:
        """Expose Tutor Mode without forcing a model call on the fast path."""
        result = self._tutor.teach(topic, level=level, mode=mode, session=session)
        return result.to_dict()

    def _check_reminders(self) -> bool:
        """Проверка сработавших напоминаний для proactor.

        Returns:
            True если есть сработавшие (TaskManager callback уже вывел текст).
        """
        # TaskManager использует callbacks, поэтому просто проверяем список
        reminders = self._task_manager.list_reminders()
        now = time.time()
        for r in reminders:
            if r["remaining_sec"] <= 0:
                return True
        return False

    def _nightly_consolidation(self) -> None:
        """Bounded local sleep-time consolidation; no external actions."""
        log.info("Ночная консолидация: запуск...")
        try:
            report = self._agent.executive.sleep()
            log.info("Ночная консолидация завершена: %s", report)
        except Exception as exc:
            log.warning("Ночная консолидация пропущена: %s", exc)

    # --------------------------------------------------------------------- #
    #  Свойства для доступа к компонентам
    # --------------------------------------------------------------------- #

    @property
    def council(self) -> CouncilRouter:
        return self._council

    @property
    def memory(self) -> MemoryRetriever:
        return self._memory

    @property
    def session(self):
        return self._session

    @property
    def tts_queue(self) -> TTSQueue:
        return self._tts_queue

    @property
    def proactor(self) -> Proactor:
        return self._proactor
