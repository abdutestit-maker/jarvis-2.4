"""Task / Mission Runtime — сердце асинхронной жизни J.A.R.V.I.S.

Один из центральных модулей J.A.R.V.I.S. 3.0 (см. ТЗ §3, §4, §30, §33, §35, §36).

Главная идея ТЗ:
    USER REQUEST  ->  БЫСТРОЕ ПОДТВЕРЖДЕНИЕ (ACK)
                 ->  ДОЛГАЯ ЗАДАЧА ПРОДОЛЖАЕТСЯ АСИНХРОННО
                 ->  progress / activity updates
                 ->  result
                 ->  verification

Задача (``Mission``) живёт ОТДЕЛЬНО от HTTP/UI request lifecycle. Пользователь
не обязан ждать, пока один synchronous function call закончится.

КРИТИЧЕСКОЕ ПРАВИЛО (§33 — НЕТ ИСКУССТВЕННОГО "3-SECOND THINKING LIMIT"):
    В этом рантайме НЕТ и НЕ БУДЕТ политики
        if reasoning_time > N:  fail_task()
    Единственные ограничения по времени — РЕАЛЬНЫЕ:
        * network timeout        (инструмент не отвечает в сеть)
        * tool / process timeout (внешняя программа зависла)
        * явная cancellation     (пользователь отменил)
        * опциональный mission watchdog (реальный потолок на ВСЮ задачу,
          задаваемый явно, по умолчанию — НЕТ, то есть безлимит).
    "Долго выполняется" != "невозможно выполнить".

Lifecycle (§4):
    queued -> acknowledging -> analyzing -> planning -> executing
           -> verifying -> repairing -> completed
    а также: paused / cancelled / failed

События (§35, §36) — типизированные, чтобы будущий UI мог подписаться:
    task_started, plan_ready, step_started, step_completed, tool_called,
    tool_result, stream_chunk, stream_end, confirmation_required, error,
    task_completed, task_progress.
"""

from __future__ import annotations

import collections
import itertools
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from core.utils.logger import get_logger
from core.security.atomic import atomic_json_write, load_json

__all__ = [
    "MissionStatus",
    "TaskEvent",
    "EventBus",
    "Mission",
    "TaskRuntime",
    "new_mission_id",
    "ALL_EVENT_TYPES",
    "EVENT_TASK_STARTED",
    "EVENT_ACKNOWLEDGED",
    "EVENT_PLAN_READY",
    "EVENT_STEP_STARTED",
    "EVENT_STEP_COMPLETED",
    "EVENT_TOOL_CALLED",
    "EVENT_TOOL_RESULT",
    "EVENT_VERIFICATION",
    "EVENT_REPAIR_STARTED",
    "EVENT_REPAIR_COMPLETED",
    "EVENT_DELEGATED",
    "EVENT_STREAM_CHUNK",
    "EVENT_STREAM_END",
    "EVENT_CONFIRMATION_REQUIRED",
    "EVENT_ERROR",
    "EVENT_TASK_COMPLETED",
    "EVENT_TASK_FAILED",
    "EVENT_TASK_PROGRESS",
]

log = get_logger(__name__)


# --------------------------------------------------------------------------- #
#  Жизненный цикл задачи
# --------------------------------------------------------------------------- #

class MissionStatus(str, Enum):
    """Состояния жизненного цикла миссии (§4)."""

    QUEUED = "queued"
    ACKNOWLEDGING = "acknowledging"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    REPAIRING = "repairing"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in (MissionStatus.COMPLETED, MissionStatus.CANCELLED, MissionStatus.FAILED)

    @property
    def is_active(self) -> bool:
        return not self.is_terminal and self != MissionStatus.PAUSED


# Типы событий (§23, §36)
EVENT_TASK_STARTED = "task_started"
EVENT_ACKNOWLEDGED = "acknowledged"
EVENT_PLAN_READY = "plan_ready"
EVENT_STEP_STARTED = "step_started"
EVENT_STEP_COMPLETED = "step_completed"
EVENT_TOOL_CALLED = "tool_called"
EVENT_TOOL_RESULT = "tool_result"
EVENT_VERIFICATION = "verification"
EVENT_REPAIR_STARTED = "repair_started"
EVENT_REPAIR_COMPLETED = "repair_completed"
EVENT_DELEGATED = "delegated"
EVENT_STREAM_CHUNK = "stream_chunk"
EVENT_STREAM_END = "stream_end"
EVENT_CONFIRMATION_REQUIRED = "confirmation_required"
EVENT_ERROR = "error"
EVENT_TASK_COMPLETED = "task_completed"
EVENT_TASK_FAILED = "task_failed"
EVENT_TASK_PROGRESS = "task_progress"

#: Полный словарь событий задачи (§23) — для подписчиков и UI.
ALL_EVENT_TYPES: tuple[str, ...] = (
    EVENT_TASK_STARTED,
    EVENT_ACKNOWLEDGED,
    EVENT_PLAN_READY,
    EVENT_STEP_STARTED,
    EVENT_STEP_COMPLETED,
    EVENT_TOOL_CALLED,
    EVENT_TOOL_RESULT,
    EVENT_VERIFICATION,
    EVENT_REPAIR_STARTED,
    EVENT_REPAIR_COMPLETED,
    EVENT_DELEGATED,
    EVENT_STREAM_CHUNK,
    EVENT_STREAM_END,
    EVENT_CONFIRMATION_REQUIRED,
    EVENT_ERROR,
    EVENT_TASK_COMPLETED,
    EVENT_TASK_FAILED,
    EVENT_TASK_PROGRESS,
)


# --------------------------------------------------------------------------- #
#  События и шина событий
# --------------------------------------------------------------------------- #

@dataclass
class TaskEvent:
    """Одно наблюдаемое событие миссии (§35, §36)."""

    task_id: str
    event_type: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    phase: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "phase": self.phase,
            "payload": self.payload,
        }


class EventBus:
    """Потокобезопасная шина событий для подписки UI / логов (§35, §36).

    Подписчики получают каждое опубликованное событие. Исключения внутри
    подписчиков НЕ должны ронять рантайм — они логируются и глотаются.
    """

    def __init__(self) -> None:
        self._subscribers: List[Callable[[TaskEvent], None]] = []
        self._lock = threading.RLock()

    def subscribe(self, callback: Callable[[TaskEvent], None]) -> Callable[[], None]:
        """Подписывает callback на все события. Возвращает unsubscribe()."""
        with self._lock:
            self._subscribers.append(callback)

        def unsubscribe() -> None:
            with self._lock:
                if callback in self._subscribers:
                    self._subscribers.remove(callback)

        return unsubscribe

    def publish(self, event: TaskEvent) -> None:
        """Публикует событие всем подписчикам (copy-on-read для безопасности)."""
        with self._lock:
            subs = list(self._subscribers)
        for cb in subs:
            try:
                cb(event)
            except Exception as exc:  # подписчик не должен ронять рантайм
                log.debug("EventBus subscriber упал на %s: %s", event.event_type, exc)


# --------------------------------------------------------------------------- #
#  Миссия
# --------------------------------------------------------------------------- #

@dataclass
class Mission:
    """Одна задача пользователя со своим жизненным циклом и историей событий (§6)."""

    task_id: str
    goal: str
    status: MissionStatus = MissionStatus.QUEUED
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    result: Optional[str] = None
    error: Optional[str] = None
    plan: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    events: List[TaskEvent] = field(default_factory=list)

    # --- поля состояния задачи (§6) ---
    progress: float = 0.0                                  # 0.0 .. 1.0
    current_step: Optional[str] = None
    model_used: Optional[str] = None
    tools_used: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    verification: Optional[Dict[str, Any]] = None
    acknowledgement: Optional[str] = None

    # Внутреннее: события публикуются и в шину, и сохраняются здесь.
    _bus: Optional[EventBus] = field(default=None, repr=False, compare=False)

    def _touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    @property
    def cancelled(self) -> bool:
        return self.status == MissionStatus.CANCELLED

    def set_status(self, status: MissionStatus, reason: Optional[str] = None) -> None:
        self.status = status
        self._touch()
        self.emit(EVENT_TASK_PROGRESS, phase=status.value,
                  payload={"status": status.value, "reason": reason, "progress": self.progress})

    def set_progress(self, progress: float, step: Optional[str] = None) -> None:
        """Обновляет прогресс задачи и публикует событие (§23)."""
        self.progress = max(0.0, min(1.0, float(progress)))
        if step:
            self.current_step = step
        self._touch()
        self.emit(EVENT_TASK_PROGRESS,
                  payload={"progress": self.progress, "current_step": self.current_step})

    def note_tool(self, tool_name: str) -> None:
        """Фиксирует использованный инструмент (§6)."""
        if tool_name and tool_name not in self.tools_used:
            self.tools_used.append(tool_name)

    def note_error(self, message: str) -> None:
        """Фиксирует ошибку, не прерывая задачу (§10 — ошибка не финал)."""
        if message:
            self.errors.append(message)
            self._touch()

    def add_step(self, description: str, tool: Optional[str] = None,
                 args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Добавляет шаг плана и публикует plan_ready при первом шаге."""
        step = {
            "index": len(self.plan),
            "description": description,
            "tool": tool,
            "args": args or {},
            "status": "pending",
        }
        self.plan.append(step)
        if len(self.plan) == 1:
            self.emit(EVENT_PLAN_READY, payload={"plan": self.plan})
        return step

    def emit(self, event_type: str, phase: Optional[str] = None,
             payload: Optional[Dict[str, Any]] = None) -> TaskEvent:
        event = TaskEvent(
            task_id=self.task_id,
            event_type=event_type,
            phase=phase or self.status.value,
            payload=payload or {},
        )
        self.events.append(event)
        self._touch()
        if self._bus is not None:
            self._bus.publish(event)
        return event

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "progress": self.progress,
            "current_step": self.current_step,
            "model_used": self.model_used,
            "tools_used": list(self.tools_used),
            "result": self.result,
            "error": self.error,
            "errors": list(self.errors),
            "verification": self.verification,
            "acknowledgement": self.acknowledgement,
            "plan": self.plan,
            "metadata": self.metadata,
            "events": [e.to_dict() for e in self.events],
        }


#: Счётчик задач в рамках процесса — для человекочитаемой нумерации (§6).
_MISSION_COUNTER = itertools.count(1)


def new_mission_id() -> str:
    """Генерирует человекочитаемый ID задачи (§6): JARVIS-YYYY-NNNNN."""
    year = datetime.now(timezone.utc).year
    return f"JARVIS-{year}-{next(_MISSION_COUNTER):05d}"


# --------------------------------------------------------------------------- #
#  Task Runtime
# --------------------------------------------------------------------------- #

# Функция, исполняющая миссию. Получает Mission (для публикации событий и
# установки статуса) и threading.Event отмены. Возвращает финальный результат
# (строку) или бросает исключение (рантайм ловит и помечает failed).
MissionRunner = Callable[[Mission, threading.Event], str]


class TaskRuntime:
    """Асинхронный рантайм миссий (§3, §4, §30, §33).

    Запускает ``MissionRunner`` в отдельном потоке, ведёт жизненный цикл,
    публикует события в ``EventBus`` и предоставляет управление:
    cancel / resume / wait / status / list.

    НИКАКИХ ограничений на "время размышления" модели. Единственный
    времени-ограничитель — опциональный ``default_watchdog_sec`` (реальный
    потолок на ВСЮ миссию, по умолчанию None = безлимит) + явная отмена.
    """

    def __init__(self, default_watchdog_sec: Optional[float] = None,
                 *, max_concurrent: int = 2,
                 persistence_dir: Optional[str | Path] = None) -> None:
        """
        Args:
            default_watchdog_sec: реальный потолок на ВСЮ миссию (сек).
                None = безлимит (§33). Это НЕ latency-бюджет и НЕ "3 секунды".
            max_concurrent: HARD CAP на число одновременно исполняемых
                миссий (§1.3 П1). Третья и последующие миссии встают в
                очередь (QUEUED) и НЕ отбрасываются, НЕ падают.
            ВНИМАНИЕ: ``max_concurrent`` — ТОЛЬКО keyword-аргумент, чтобы
            не сломать существующие call-сайты, передающие позиционно
            ``default_watchdog_sec`` (например TaskRuntime(30)).
        """
        if max_concurrent < 1:
            raise ValueError("max_concurrent должен быть >= 1")
        self._bus = EventBus()
        self._missions: Dict[str, Mission] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self._cancel: Dict[str, threading.Event] = {}
        self._lock = threading.RLock()
        self._default_watchdog = default_watchdog_sec
        # --- HARD CAP параллельных миссий (§1.3) ---
        self._max_concurrent = max_concurrent
        self._active_count = 0
        # Очередь ожидающих миссий: (mission, runner, cancel, watchdog)
        self._queue: "collections.deque" = collections.deque()
        self._persistence_dir = Path(persistence_dir) if persistence_dir else None
        if self._persistence_dir is not None:
            self._persistence_dir.mkdir(parents=True, exist_ok=True)
            self._restore_persisted()
            self._bus.subscribe(self._persist_event)

    # ------------------------------------------------------------------ #
    #  Доступ к шине событий
    # ------------------------------------------------------------------ #
    @property
    def bus(self) -> EventBus:
        return self._bus

    def subscribe(self, callback: Callable[[TaskEvent], None]) -> Callable[[], None]:
        return self._bus.subscribe(callback)

    # ------------------------------------------------------------------ #
    #  Создание и запуск
    # ------------------------------------------------------------------ #
    def submit(self, goal: str, runner: MissionRunner,
               watchdog_sec: Optional[float] = None,
               metadata: Optional[Dict[str, Any]] = None) -> Mission:
        """Создаёт миссию и запускает её в фоновом потоке.

        НЕ блокирует вызывающий поток — сразу возвращает ``Mission``
        (статус queued/acknowledging), пока реальная работа идёт асинхронно.

        Args:
            goal: цель пользователя.
            runner: исполнитель миссии (получает Mission + cancel Event).
            watchdog_sec: реальный потолок на миссию; None = брать дефолт.
            metadata: произвольные метаданные (risk, intent, и т.п.).

        Returns:
            Mission — немедленно (до завершения работы).
        """
        mission = Mission(task_id=new_mission_id(), goal=goal, status=MissionStatus.QUEUED)
        mission._bus = self._bus
        mission.metadata = dict(metadata or {})
        cancel = threading.Event()

        watchdog = watchdog_sec if watchdog_sec is not None else self._default_watchdog

        with self._lock:
            self._missions[mission.task_id] = mission
            self._cancel[mission.task_id] = cancel
            if self._active_count < self._max_concurrent:
                self._active_count += 1
                start_now = True
            else:
                self._queue.append((mission, runner, cancel, watchdog))
                start_now = False

        mission.emit(EVENT_TASK_STARTED, phase=MissionStatus.QUEUED.value,
                     payload={"goal": goal, "watchdog_sec": watchdog})

        if start_now:
            self._start_thread(mission, runner, cancel, watchdog)
        else:
            # HARD CAP достигнут: миссия ЖДЁТ в очереди (§1.3 П1) — НЕ падает.
            mission.set_status(MissionStatus.QUEUED, "ожидает свободного слота (HARD CAP)")
            log.info("TaskRuntime: HARD CAP=%d достигнут, миссия %s в очереди",
                     self._max_concurrent, mission.task_id)

        return mission

    # ------------------------------------------------------------------ #
    #  Служебное: старт потока миссии
    # ------------------------------------------------------------------ #

    def _start_thread(self, mission: Mission, runner: MissionRunner,
                      cancel: threading.Event, watchdog: Optional[float]) -> None:
        """Создаёт и стартует поток исполнения миссии (вне блокировки _lock)."""
        mission.set_status(MissionStatus.ACKNOWLEDGING, "mission accepted")
        thread = threading.Thread(
            target=self._run_wrapper,
            args=(mission, runner, cancel, watchdog),
            name=f"mission-{mission.task_id}",
            daemon=True,
        )
        with self._lock:
            self._threads[mission.task_id] = thread
        thread.start()

    def _run_wrapper(self, mission: Mission, runner: MissionRunner,
                     cancel: threading.Event, watchdog: Optional[float]) -> None:
        """Обертка потока: ловит всё, управляет статусом и watchdog."""
        start = time.perf_counter()
        mission.emit(EVENT_ACKNOWLEDGED, phase=MissionStatus.ACKNOWLEDGING.value,
                     payload={"ack": mission.acknowledgement or "Принято, сэр. Разбираюсь."})

        # Опциональный реальный watchdog на ВСЮ миссию (не на размышление!).
        if watchdog is not None and watchdog > 0:
            def _watcher() -> None:
                if not cancel.wait(timeout=watchdog):
                    if mission.status.is_active:
                        log.warning("Watchdog: миссия %s превысила реальный лимит %ss",
                                    mission.task_id, watchdog)
                        cancel.set()
                        mission.set_status(MissionStatus.FAILED,
                                           f"real watchdog timeout ({watchdog}s)")
            wthread = threading.Thread(target=_watcher, name=f"watchdog-{mission.task_id}",
                                       daemon=True)
            wthread.start()

        try:
            result = runner(mission, cancel)
            if cancel.is_set() and mission.status != MissionStatus.COMPLETED:
                # Отмена во время работы
                if mission.status.is_active:
                    mission.status = MissionStatus.CANCELLED
                    mission.emit(EVENT_TASK_COMPLETED, payload={"status": "cancelled"})
                    mission.error = mission.error or "Отменено пользователем."
                    return
            # Подтверждение (HIGH-risk): миссия приостановлена и ждёт ответа
            # пользователя. Финализировать НЕЛЬЗЯ — иначе confirmation
            # теряется, и никто не сможет его подтвердить/отклонить.
            if mission.status == MissionStatus.PAUSED:
                mission.result = result
                log.info("Миссия %s ожидает подтверждения пользователя", mission.task_id)
                return
            mission.result = result
            mission.set_status(MissionStatus.COMPLETED)
            mission.emit(EVENT_TASK_COMPLETED, payload={"status": "completed", "result": result})
            log.info("Миссия %s завершена за %.1fs", mission.task_id,
                     time.perf_counter() - start)
        except Exception as exc:  # верхний уровень миссии
            if cancel.is_set():
                mission.status = MissionStatus.CANCELLED
                mission.error = "Отменено пользователем."
            else:
                mission.status = MissionStatus.FAILED
                mission.error = f"{type(exc).__name__}: {exc}"
                mission.note_error(mission.error)
                mission.emit(EVENT_ERROR, payload={"error": mission.error})
                mission.emit(EVENT_TASK_FAILED, payload={"error": mission.error})
                log.exception("Миссия %s упала: %s", mission.task_id, exc)
            mission.emit(EVENT_TASK_COMPLETED,
                         payload={"status": mission.status.value, "error": mission.error})
        finally:
            # Слот освобождается СТРОГО в finally — даже при отмене/падении/
            # паузе (§1.3 П1). Иначе очередь зависнет навсегда.
            self._release_slot_and_drain()

    def _release_slot_and_drain(self) -> None:
        """Освобождает слот и стартует следующую миссию из очереди (§1.3 П1).

        Вызывается из finally каждой завершившейся миссии. Поток следующей
        миссии стартует ВНЕ блокировки, чтобы не держать _lock долго и не
        дедлокнуть подписчиков шины событий.
        """
        nxt = None
        with self._lock:
            self._active_count = max(0, self._active_count - 1)
            while self._queue:
                mission, runner, cancel, watchdog = self._queue.popleft()
                # Отменённая ещё в очереди — просто выбрасываем, не стартуем.
                if cancel.is_set() or mission.status == MissionStatus.CANCELLED:
                    continue
                self._active_count += 1
                nxt = (mission, runner, cancel, watchdog)
                break
        if nxt is not None:
            self._start_thread(*nxt)

    # ------------------------------------------------------------------ #
    #  Управление
    # ------------------------------------------------------------------ #
    def cancel(self, task_id: str) -> bool:
        """Отменяет миссию (выставляет флаг отмены исполнителю).

        Работает и для миссий, ещё ЖДУЩИХ в очереди (§1.3 П1): такие
        никогда не стартуют — выбрасываются при дренаже слота.
        """
        with self._lock:
            ev = self._cancel.get(task_id)
            mission = self._missions.get(task_id)
            # Если миссия ещё в очереди — помечаем отменённой, чтобы drain
            # её выбросил, а не запустил.
            queued = False
            if mission is not None and mission.status == MissionStatus.QUEUED:
                new_q = collections.deque()
                for item in self._queue:
                    if item[0].task_id == task_id:
                        queued = True
                        continue
                    new_q.append(item)
                self._queue = new_q
        if ev is None:
            return False
        ev.set()
        if mission is not None and mission.status.is_active:
            mission.set_status(
                MissionStatus.CANCELLED,
                "cancel requested" + (" (в очереди)" if queued else ""),
            )
        return True

    def resume(self, task_id: str) -> bool:
        """Снимает паузу (заглушка-задел: текущие миссии не поддерживают паузу)."""
        mission = self.get(task_id)
        if mission is None:
            return False
        if mission.status == MissionStatus.PAUSED:
            mission.set_status(MissionStatus.EXECUTING, "resumed")
            return True
        return False

    def pause(self, task_id: str) -> bool:
        """Marks a mission paused; cooperative runners inspect this state."""
        mission = self.get(task_id)
        if mission is None or mission.status.is_terminal:
            return False
        mission.set_status(MissionStatus.PAUSED, "paused by user")
        return True

    def skip_step(self, task_id: str) -> bool:
        """Skips only the current pending plan step and preserves the mission."""
        mission = self.get(task_id)
        if mission is None:
            return False
        for step in mission.plan:
            if step.get("status") == "pending":
                step["status"] = "skipped"
                mission._touch()
                mission.emit(EVENT_STEP_COMPLETED, payload={
                    "step": step.get("description"), "status": "skipped",
                })
                return True
        return False

    def explain_current_step(self, task_id: str) -> str:
        """Returns an action trace item, never hidden model reasoning."""
        mission = self.get(task_id)
        if mission is None:
            return "mission not found"
        for step in mission.plan:
            if step.get("status") == "pending":
                return str(step.get("description") or step.get("tool") or "pending")
        return "completed"

    def restore_mission(self, mission: Mission) -> Mission:
        """Registers an externally reconstructed mission for continuation."""
        mission._bus = self._bus
        with self._lock:
            self._missions[mission.task_id] = mission
            self._cancel.setdefault(mission.task_id, threading.Event())
        self._persist(mission)
        return mission

    def wait(self, task_id: str, timeout: Optional[float] = None) -> Optional[Mission]:
        """Блокирует до терминального статуса миссии или до timeout.

        ВАЖНО (§33): timeout здесь — это сколько ВЫЗЫВАЮЩИЙ готов ждать,
        а НЕ лимит на саму задачу. Если timeout=None — ждём сколько угодно.
        """
        mission = self.get(task_id)
        if mission is None:
            return None
        deadline = None if timeout is None else time.perf_counter() + timeout
        while mission.status.is_active:
            remaining = None if deadline is None else max(0.0, deadline - time.perf_counter())
            if remaining is not None and remaining <= 0:
                return mission
            time.sleep(0.1)
        return mission

    def get(self, task_id: str) -> Optional[Mission]:
        with self._lock:
            return self._missions.get(task_id)

    def list_missions(self, include_terminal: bool = True) -> List[Mission]:
        with self._lock:
            items = list(self._missions.values())
        if not include_terminal:
            items = [m for m in items if m.status.is_active]
        return items

    def shutdown(self) -> None:
        """Отменяет все активные и ожидающие миссии (§3, graceful exit)."""
        with self._lock:
            # Очистить очередь ожидания — миссии в ней не должны стартовать.
            self._queue.clear()
        # Отменить активные и queued.
        for tid in list(self._missions.keys()):
            self.cancel(tid)
        # Дождаться завершения потоков (best-effort).
        for tid, th in list(self._threads.items()):
            if th.is_alive():
                th.join(timeout=2.0)

    def is_alive(self, task_id: str) -> bool:
        with self._lock:
            th = self._threads.get(task_id)
        return th is not None and th.is_alive()

    # ------------------------------------------------------------------ #
    #  Sprint 9 — local mission persistence
    # ------------------------------------------------------------------ #
    def _persist_event(self, event: TaskEvent) -> None:
        mission = self.get(event.task_id)
        if mission is not None:
            self._persist(mission)

    def _persist(self, mission: Mission) -> None:
        if self._persistence_dir is None:
            return
        path = self._persistence_dir / f"{mission.task_id}.json"
        atomic_json_write(path, mission.to_dict())

    def _restore_persisted(self) -> None:
        if self._persistence_dir is None:
            return
        for path in self._persistence_dir.glob("*.json"):
            try:
                data = load_json(path, default={})
                mission = Mission(
                    task_id=data["task_id"], goal=data["goal"],
                    status=MissionStatus(data.get("status", "queued")),
                    created_at=data.get("created_at", _utcnow_iso()),
                    updated_at=data.get("updated_at", _utcnow_iso()),
                    result=data.get("result"), error=data.get("error"),
                    plan=list(data.get("plan") or []), metadata=dict(data.get("metadata") or {}),
                    progress=float(data.get("progress", 0.0)),
                    current_step=data.get("current_step"), model_used=data.get("model_used"),
                    tools_used=list(data.get("tools_used") or []),
                    errors=list(data.get("errors") or []), verification=data.get("verification"),
                    acknowledgement=data.get("acknowledgement"),
                )
                mission._bus = self._bus
                self._missions[mission.task_id] = mission
                self._cancel[mission.task_id] = threading.Event()
            except (OSError, ValueError, TypeError, KeyError):
                continue


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
