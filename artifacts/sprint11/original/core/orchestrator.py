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
from core.memory import MemoryRetriever
from core.model_router import ModelRouter, estimate_complexity
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
        self._model_router = ModelRouter(settings)

        # Инициализация компонентов
        self._council = CouncilRouter(settings, model_router=self._model_router)
        self._session = None  # будет создан в start()
        self._memory = MemoryRetriever(settings)
        self._registry = DEFAULT_REGISTRY

        # --- Агентное ядро J.A.R.V.I.S. 3.0 (§3, §6) ---
        # Агент исполняет миссии, TaskRuntime даёт им асинхронную жизнь.
        # НЕТ watchdog по умолчанию: миссия живёт столько, сколько нужно (§4).
        self._agent = Agent(settings, council=self._council, model_router=self._model_router)
        # Shadow Engine is owned by Agent but its cadence belongs to the
        # orchestrator lifecycle, alongside other background services.
        self._shadow = self._agent._shadow
        self._runtime = TaskRuntime(
            default_watchdog_sec=None,
            persistence_dir=settings.data_dir / "missions",
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

            log.info("Оркестратор запущен")

    def shutdown(self) -> None:
        """Корректно останавливает всё."""
        with self._lock:
            if not self._running:
                return
            self._running = False

        self._proactor.stop()
        self._scheduler.stop()
        self._shadow.stop()
        self._tts_queue.stop(wait=True)

        log.info("Оркестратор остановлен")

    def handle_input(self, text: str) -> JarvisState:
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
        if not self._running:
            self.start()

        # Отмечаем активность для proactor
        self._proactor.mark_user_activity()

        # Единый путь (§3): тяжёлая задача -> фон (мгновенный ACK),
        # лёгкая -> синхронно в том же агентном цикле (без фоновой миссии).
        if self._should_run_background(text):
            mission = self.submit_goal(text)
            ack = mission.acknowledgement or "Принято, сэр. Работаю."
            state = new_state(text)
            self._session.push("user", text)
            self._session.to_state(state)
            state["response"] = ack
            ack_output = AssistantOutput.natural(ack, speech_mode="focused")
            rendered = self._speech_renderer.render(ack_output)
            state["tts_text"] = rendered.text if rendered else None
            state["assistant_output"] = ack_output.to_dict()
            state["mission_id"] = mission.task_id
            return state

        # Синхронный путь через единый агентный цикл
        # (intent -> risk -> MODEL SELECTION -> tool -> verify -> repair).
        outcome = self._agent.execute(text)

        output = assistant_output_from_outcome(outcome)
        response = output.display_text or "(пустой ответ, сэр)."

        state = new_state(text)
        self._session.push("user", text)
        self._session.to_state(state)

        # Memory: remember exchange (не дублируем для confirmation-шагов)
        if not outcome.needs_confirmation:
            try:
                self._memory.remember_exchange(text, response)
            except Exception as exc:
                log.warning("Не удалось сохранить обмен в память: %s", exc)

        # Short-term: push assistant
        self._session.push("assistant", response)
        self._session.to_state(state)

        spoken = self._queue_assistant_output(output)

        # Output callback (печать/тост)
        self._output_callback(response)

        state["response"] = response
        state["tts_text"] = spoken
        state["assistant_output"] = output.to_dict()
        if outcome.needs_confirmation:
            state["confirmation_id"] = getattr(outcome, "confirmation_id", None)
            state["needs_confirmation"] = True
        return state

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
        if is_research_goal(goal):
            return True
        cx = estimate_complexity(goal)
        # LOCAL_THRESHOLD из ModelRouter (0.35): выше — в фон.
        return cx.score >= 0.35

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

        state: JarvisState = new_state("")
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
            metadata={"intent": intent, "source": "user"},
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

        # Память и озвучка — только для завершённых, не отменённых задач.
        if not cancel.is_set():
            try:
                self._memory.remember_exchange(mission.goal, result_text)
            except Exception as exc:
                log.warning("Не удалось сохранить обмен в память: %s", exc)
            if self._session is not None:
                self._session.push("assistant", result_text)

            self._output_callback(result_text)
            self._queue_assistant_output(AssistantOutput.natural(result_text))

        return result_text

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
        return self._runtime.pause(task_id)

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
            show_toast("Джарвис", text[:100])

    def _proactive_output(self, text: str) -> None:
        """Вывод проактивного сообщения."""
        print(f"💡 [Проактивно] {text}")
        if self._settings.voice.tts_enabled:
            self._queue_assistant_output(
                AssistantOutput.natural(text, speech_mode="background")
            )
            show_toast("Джарвис (проактивно)", text[:100])

    def _queue_assistant_output(self, output: AssistantOutput) -> Optional[str]:
        """Single typed path into TTS; returns the final safe spoken text."""
        rendered = self._speech_renderer.render(output)
        if rendered is None:
            return None
        if self._settings.voice.tts_enabled and self._tts.is_available():
            self._tts_queue.add_output(output)
        return rendered.text

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
        """Ночная консолидация (заглушка)."""
        log.info("Ночная консолидация: запуск...")
        # TODO: анализ дня, суммаризация, дедуп памяти, утренний брифинг
        log.info("Ночная консолидация: завершена (заглушка)")

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
