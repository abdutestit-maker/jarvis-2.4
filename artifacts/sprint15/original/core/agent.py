"""Agent — контроллер миссии J.A.R.V.I.S. (§3, §8, §9, §10, §11, §14).

Полный цикл ОДНОЙ задачи пользователя:

    USER GOAL -> INTENT -> RISK -> CONTEXT -> MODE -> PLAN
              -> TOOL RETRIEVAL -> EXECUTION -> VERIFICATION
              -> REPAIR (если ошибка) -> RESULT -> MEMORY / SKILL

Ключевые принципы ТЗ:

    * §3  Цикл САМ СОКРАЩАЕТСЯ для простых задач. "Открой Telegram" не
          запускает multi-agent workflow — идёт FAST PATH.
    * §4  НЕТ искусственного лимита мышления. В этом модуле нет ни одной
          проверки вида "elapsed > N -> fail". Реальные таймауты живут
          только внутри инструментов (сеть/процесс).
    * §5  ACKNOWLEDGING — отдельная быстрая стадия, без тяжёлой модели.
    * §8  UNKNOWN != IMPOSSIBLE. Нет инструмента -> исследуем и строим метод.
    * §10 Ошибка -> диагноз -> патч -> retry, а не капитуляция.
    * §14 "Готово" говорим ТОЛЬКО после фактической верификации.
    * §21 HIGH risk -> запрос подтверждения, а не тихое выполнение.

Модуль переиспользует существующие компоненты (§26 — эволюция, не reset):
    core.actions      — инструменты и исполнитель
    core.router       — CouncilRouter / keyword intent
    core.task_runtime — Mission / события / статусы
    core.repair       — RepairLoop
    core.verifier     — фактические проверки
    core.skill_forge  — навыки
    core.ingest       — большие входы
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import uuid

from config.settings import Settings
from core.actions import DEFAULT_REGISTRY
from core.actions.base import ActionResult, ToolContext
from core.actions.executor import execute_tool
from core.capabilities import CAPABILITIES, Capability, describe_tools_for_model
from core.ingest import ingest_text
from core.memory.knowledge_graph import GraphMemoryStore
from core.llm import (
    BackendConfigError,
    BackendUnavailable,
    Tier,
    breaker,
    get_llm_backend,
    get_offline_backend,
)
from core.memory.budget import fit_messages_to_budget
from core.memory.facts import detect_tone, learn_facts
from core.memory.profile import get_profile_context
from core.memory.relationship import MemoryHierarchy, PreferenceLearner, RelationshipMemoryStore
from core.memory.short_term import SessionManager
from core.model_router import ModelRouter, RoutingDecision, classify_conversation
from core.personality import PersonalityEngine
from core.repair import RepairLoop
from core.research import ResearchEngine, is_research_goal
from core.router.intent_router import resolve_keyword_tool
from core.safety import RiskAssessment, assess_risk
from core.redact import redact_args
from core.skill_forge import SkillForge, SkillManifest, SkillStatus
from core.structured import PLAN_SCHEMA_HINT, AnswerStreamExtractor, parse_structured, validate_tool_call
from core.task_runtime import (
    EVENT_CONFIRMATION_REQUIRED,
    EVENT_PLAN_READY,
    EVENT_REPAIR_COMPLETED,
    EVENT_REPAIR_STARTED,
    EVENT_STREAM_CHUNK,
    EVENT_STEP_COMPLETED,
    EVENT_STEP_STARTED,
    EVENT_TASK_FAILED,
    EVENT_TOOL_CALLED,
    EVENT_TOOL_RESULT,
    EVENT_VERIFICATION,
    Mission,
    MissionStatus,
)
from core.utils.logger import get_logger
from core.verifier import VerificationResult, verify_action_result

__all__ = ["Agent", "AgentConfig", "AgentOutcome", "ACK_PHRASES", "pick_acknowledgement"]

log = get_logger(__name__)

#: Префикс ошибки планирования «модель недоступна» (сеть/провайдер/ключ).
#: Такая ошибка — НЕ «не умею» (§29): это временный сбой инфраструктуры,
#: и пользователь должен получить короткую честную фразу без сырых деталей
#: и без создания черновика навыка.
MODEL_ERROR_PREFIX = "model_error:"

#: Текст для пользователя при сбое модели (голос/чат). Технические детали —
#: только в лог. Тон согласован с TTS-санитайзером (core/voice/tts_sanitizer.py).
MODEL_UNAVAILABLE_TEXT = "Сэр, сейчас не отвечает. Попробуйте ещё раз."


def _hide_reasoning_stream(cumulative: str) -> str:
    """Прячет служебные ``<think>``-блоки из НАРАСТАЮЩЕГО текста стрима.

    Закрытый блок вырезается целиком; незакрытый (модель ещё думает) —
    скрывает всё после его начала. Применяется только в прямом разговорном
    режиме (Sprint 2), где пользователю идёт сырой текст модели.
    """
    out = re.sub(r"<think>.*?</think>", "", cumulative, flags=re.DOTALL | re.IGNORECASE)
    if "<think>" in out.lower():
        idx = out.lower().rfind("<think>")
        out = out[:idx]
    return out


# --------------------------------------------------------------------------- #
#  §5 — FIRST ACKNOWLEDGEMENT (быстро, без тяжёлой модели)
# --------------------------------------------------------------------------- #

ACK_PHRASES: Dict[str, str] = {
    "app": "Принято, сэр.",
    "file": "Сейчас проверю.",
    "web": "Разбираюсь.",
    "browser": "Понял, сэр.",
    "system": "Принято.",
    "media": "Понял, сэр.",
    "none": "Понял, сэр. Разбираюсь.",
}


def pick_acknowledgement(intent: str, goal: str = "",
                          settings: Optional["Settings"] = None) -> str:
    """Мгновенное, ЖИВОЕ подтверждение приёма задачи (§5, П1 §1.2).

    Базовая фраза выбирается по намерению (как раньше — мгновенно),
    затем, если доступна ЛОКАЛЬНАЯ модель (Qwen 4B на лице) и задан
    контекст цели, фраза ОБОГАЩАЕТСЯ коротким контекстным вариантом
    от модели (чтобы ACK звучал как живая сущность, а не робот-заглушка).

    ЖЁСТКИЙ FALLBACK (критично для офлайн-тестов и надёжности): при
    любой ошибке/недоступности локальной модели, таймауте или пустом
    ответе — возвращается базовая canned-фраза по intent. Стадия
    ACKNOWLEDGING остаётся мгновенной и НИКОГДА не падает.
    """
    base = ACK_PHRASES.get(intent, ACK_PHRASES["none"])

    # Без контекста цели или без настроек — мгновенно отдаём базу.
    if not goal or not goal.strip() or settings is None:
        return base

    try:
        from core.llm import get_llm_backend, Tier
        from core.llm.backend import BackendUnavailable, BackendConfigError

        backend = get_llm_backend(settings, Tier.FAST)
        prompt = (
            f"Ты — АТЛАС. Пользователь только что дал команду: \"{goal}\". "
            f"Сгенерируй ОДНУ короткую (до 5 слов) фразу подтверждения приёма "
            f"в стиле живого дворецкого, без приветствий и пояснений. "
            f"Не начинай выполнять задачу. Только подтверди, что понял. "
            f"Примеры стиля: \"{base}\", \"Есть, сэр.\", \"Слушаюсь.\""
        )
        ack = backend.direct(prompt, max_tokens=24, temperature=0.4)
        ack = (ack or "").strip().strip('"\'‘’“”')
        # Фильтруем сырьё: если модель вернула мусор/JSON/слишком длинно —
        # откатываемся на базу (чтобы голос не читал сырьё).
        if not ack or len(ack) > 40 or ack.startswith("{") or "\n" in ack:
            return base
        return ack
    except (BackendUnavailable, BackendConfigError, Exception) as _exc:  # noqa: BLE001
        # Любой сбой локальной модели — мгновенный откат на базовую фразу.
        log.debug("ACK LLM-генерация недоступна, fallback на canned: %s", _exc)
        return base


# --------------------------------------------------------------------------- #
#  Конфигурация и результат
# --------------------------------------------------------------------------- #

@dataclass
class AgentConfig:
    """Настройки поведения агента (без единого лимита на время §4)."""

    max_tool_retrieval: int = 5        # сколько инструментов показываем модели (§12)
    max_plan_steps: int = 8            # разумный потолок шагов плана
    max_repair_attempts: int = 3       # §11 — ограниченный, но не единичный repair
    max_structured_retries: int = 2    # §13 — повторный запрос при плохом JSON
    large_input_chars: int = 6000      # §7 — выше порога включаем ingest
    auto_confirm_high_risk: bool = False   # §21 — HIGH требует человека
    enable_skill_forge: bool = True    # §9
    confirmation_timeout_sec: float = 30.0  # П1 §1.3: таймаут ожидания подтверждения -> авто-reject


@dataclass
class AgentOutcome:
    """Итог работы агента по миссии."""

    text: str
    verified: bool = False
    verification: Optional[VerificationResult] = None
    tool_used: Optional[str] = None
    needs_confirmation: bool = False
    confirmation_id: Optional[str] = None
    risk: Optional[RiskAssessment] = None
    mode: str = "conversation"
    trace: List[str] = field(default_factory=list)
    #: Sprint 3 STEP 5: ответ пришёл с фолбэк-модели, а не с основной
    #: (quality indicator для UI/TTS — не маскируем деградацию).
    degraded: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "verified": self.verified,
            "verification": self.verification.to_dict() if self.verification else None,
            "tool_used": self.tool_used,
            "needs_confirmation": self.needs_confirmation,
            "confirmation_id": self.confirmation_id,
            "risk": self.risk.to_dict() if self.risk else None,
            "mode": self.mode,
            "trace": list(self.trace),
            "degraded": self.degraded,
        }


# --------------------------------------------------------------------------- #
#  Агент
# --------------------------------------------------------------------------- #

class Agent:
    """Контроллер одной миссии (§3).

    Агент НЕ владеет потоками: его ``run_mission`` вызывается из
    ``TaskRuntime`` в фоновом потоке. Отмена приходит через ``cancel``.
    """

    def __init__(
        self,
        settings: Settings,
        council: Optional[Any] = None,
        config: Optional[AgentConfig] = None,
        model_router: Optional[Any] = None,
    ) -> None:
        """
        Args:
            settings: конфигурация проекта.
            council: существующий ``CouncilRouter`` (переиспользуем §26).
                Если None — создаётся лениво при первой необходимости.
            config: настройки поведения агента.
            model_router: ЕДИНЫЙ ``ModelRouter`` (P5 §5.7). Если передан —
                переиспользуется (общий с CouncilRouter), иначе создаётся свой.
        """
        self._settings = settings
        self._config = config or AgentConfig()
        self._council = council
        self._registry = DEFAULT_REGISTRY
        # Sprint 8: Shadow Engine observes only when explicitly enabled in
        # local settings. It is separate from the active request path.
        from core.shadow import ShadowEngine
        shadow_cfg = getattr(settings, "shadow", None)
        shadow_data_dir = settings.paths.resolved("data_dir")
        self._shadow = ShadowEngine(
            data_dir=shadow_data_dir or "data", registry=self._registry, settings=settings,
            enabled=bool(getattr(shadow_cfg, "enabled", False)),
        )
        from core.capability_engine import CapabilityCatalog, CapabilityPlanner
        capability_dir = (shadow_data_dir or self._settings.data_dir) / "capabilities"
        self._capability_catalog = CapabilityCatalog(capability_dir)
        self._capability_planner = CapabilityPlanner(
            self._capability_catalog, self._registry,
        )
        # P5 §5.7: делим ЕДИНЫЙ роутер моделей с CouncilRouter, чтобы оба
        # пути (REPL/WebSocket и агентная миссия) маршрутизировались одинаково.
        self._model_router = model_router if model_router is not None else ModelRouter(settings)
        self._forge = SkillForge(settings) if self._config.enable_skill_forge else None
        self._repair = RepairLoop(
            self._registry,
            reasoner=None,
            fallback_tools=CAPABILITIES.fallbacks_map(),
            max_attempts=self._config.max_repair_attempts,
        )
        # Лёгкая офлайн-память на графе (SQLite, без эмбеддингов) —
        # даёт реальный вертикальный путь store/retrieve/use даже без
        # chromadb/сети (P0-5).
        try:
            self._graph = GraphMemoryStore(settings)
        except Exception as exc:
            log.warning("Граф памяти недоступен: %s", exc)
            self._graph = None
        self._pending_confirmations: Dict[str, Dict[str, Any]] = {}
        self._confirmation_timers: Dict[str, "threading.Timer"] = {}
        self._lock = threading.RLock()
        # Sprint 1: стриминг sync-ответов. Sink устанавливается ПОТОКОМ,
        # обрабатывающим конкретный запрос (thread-local), поэтому параллельные
        # запросы друг друга не видят и не перемешивают.
        self._stream_tls = threading.local()
        # Sprint 4: bounded session memory — последние N сообщений диалога
        # (10 пар user/assistant, FIFO). Подаётся ТОЛЬКО в разговорный путь;
        # tool-промпты остаются чистыми (спринт, STEP 2.4).
        session_size = int(getattr(getattr(settings, "limits", None),
                                   "session_memory_messages", 20))
        self._session = SessionManager(max_size=session_size)
        # Sprint 12: identity and relationship preferences are typed local
        # state. The resulting compact prompt fragment is only one consumer;
        # personality itself is not represented by a free-form prompt.
        self._relationship_memory = RelationshipMemoryStore(
            (shadow_data_dir or self._settings.data_dir) / "relationship",
        )
        try:
            self._relationship_memory.prune()
        except Exception as exc:
            log.debug("Очистка устаревшей relationship memory пропущена: %s", exc)
        self._preference_learner = PreferenceLearner(self._relationship_memory)
        self._personality = PersonalityEngine()
        self._memory_hierarchy = MemoryHierarchy(
            self._relationship_memory, session=self._session,
        )
        self._user_context: Dict[str, Any] = {}

    @property
    def personality(self) -> PersonalityEngine:
        return self._personality

    @property
    def relationship_memory(self) -> RelationshipMemoryStore:
        return self._relationship_memory

    @property
    def preference_learner(self) -> PreferenceLearner:
        return self._preference_learner

    def set_user_context(self, context: Any) -> None:
        """Updates privacy-minimal attention state used for response style."""
        if isinstance(context, dict):
            source = context
        else:
            source = vars(context) if context is not None and hasattr(context, "__dict__") else {}
        allowed = {
            "busy", "user_busy", "typing_active", "meeting_active", "fullscreen",
            "active_application", "probable_activity", "active_mission",
        }
        self._user_context = {key: source[key] for key in allowed if key in source}
        self._memory_hierarchy.working.update(self._user_context)

    # ------------------------------------------------------------------ #
    #  Sprint 1 — stream sink (прогрессивный ответ в UI)
    # ------------------------------------------------------------------ #

    def install_stream_sink(self, sink) -> None:
        """Регистрирует приёмник кумулятивного текста ответа для ТЕКУЩЕГО потока.

        ``sink(visible_text_so_far: str)`` вызывается по мере реальной
        генерации модели (SSE-дельты). Если бэкенд не поддерживает
        streaming — sink просто не вызывается, поведение не меняется.
        """
        self._stream_tls.sink = sink

    def clear_stream_sink(self) -> None:
        self._stream_tls.sink = None

    def _stream_consume(self, backend, messages: List[Dict[str, Any]], system: str,
                        extract_answer: bool = True) -> str:
        """chat() со стримингом, если установлен sink и бэкенд умеет streaming.

        Возвращает ПОЛНЫЙ сырой ответ (как chat). Видимый кумулятивный текст
        уходит в sink по мере прихода дельт — это реальный стриминг провайдера,
        не фейк-чанкинг готовой строки. ``extract_answer=True`` (план-JSON)
        извлекает поле ``answer``; ``False`` (прямой разговор) отдаёт сырой
        текст с скрытием служебных ``<think>``-блоков.
        Сбой сети/провайдера (BackendUnavailable/BackendConfigError)
        пробрасывается наружу — существующая логика фолбэка тиров (§15)
        сохранена без изменений.
        """
        sink = getattr(self._stream_tls, "sink", None)
        stream = getattr(backend, "streaming", None)
        if sink is None or stream is None:
            return backend.chat(messages, system=system)

        extractor = AnswerStreamExtractor() if extract_answer else None
        parts: List[str] = []
        try:
            for piece in stream(messages, system=system):
                if not piece:
                    continue
                parts.append(piece)
                if extractor is not None:
                    visible = extractor.feed(piece)
                else:
                    visible = _hide_reasoning_stream("".join(parts))
                if visible:
                    sink(visible)
        except (BackendUnavailable, BackendConfigError):
            raise  # наружу -> фолбэк тира / model_error (Sprint 1 STEP 5)
        except Exception as exc:
            # Неожиданная ошибка стриминга (бэкенд-специфика): честно
            # деградируем до обычного chat() того же тира.
            log.warning("streaming() упал (%s) — fallback на chat()", exc)
            return backend.chat(messages, system=system)

        raw = "".join(parts)
        if not raw.strip():
            return backend.chat(messages, system=system)
        return raw

    # ------------------------------------------------------------------ #
    #  Публичный вход: исполнение миссии
    # ------------------------------------------------------------------ #

    def run_mission(self, mission: Mission, cancel: threading.Event) -> str:
        """Исполняет миссию целиком. Возвращает финальный текст ответа.

        Вызывается ``TaskRuntime`` в отдельном потоке. Никаких ограничений
        на длительность (§4) — только реальная отмена через ``cancel``.

        Sprint 1 STEP 2: кумулятивный текст реального SSE-потока транслируется
        в события миссии (EVENT_STREAM_CHUNK, correlation = task_id), а
        финальный _output_callback того же потока закрывает стримленный
        пузырь (см. consume_streamed_mission).
        """
        tls = self._stream_tls
        tls.streamed_rid = None

        def _mission_sink(visible: str) -> None:
            if getattr(tls, "streamed_rid", None) is None:
                tls.streamed_rid = mission.task_id
            try:
                mission.emit(EVENT_STREAM_CHUNK, payload={"text": visible})
            except Exception:  # pragma: no cover - события не ломают генерацию
                pass

        self.install_stream_sink(_mission_sink)
        try:
            outcome = self.execute(mission.goal, mission=mission, cancel=cancel)
        finally:
            self.clear_stream_sink()
        mission.verification = outcome.verification.to_dict() if outcome.verification else None
        mission.metadata["mode"] = outcome.mode
        mission.metadata["verified"] = outcome.verified
        if outcome.needs_confirmation:
            mission.metadata["needs_confirmation"] = True
        return outcome.text

    def consume_streamed_mission(self) -> Optional[str]:
        """Отдаёт и сбрасывает task_id миссии, стримленной в ТЕКУЩЕМ потоке.

        Вызывается ws-мостом в output_callback: финальный текст должен
        закрыть УЖЕ открытый стрименный пузырь (тот же task_id), а не
        создавать второй.
        """
        tls = self._stream_tls
        rid = getattr(tls, "streamed_rid", None)
        tls.streamed_rid = None
        return rid

    def execute(self, goal: str, mission: Optional[Mission] = None,
                cancel: Optional[threading.Event] = None) -> AgentOutcome:
        """Главный цикл: intent -> risk -> mode -> plan -> execute -> verify -> repair.

        Цикл сокращается автоматически (§3): тривиальный разговор и простые
        команды не проходят через планирование.

        Sprint 4: перед генерацией из реплики извлекаются явные факты
        («меня зовут X») в профиль; после — пара (goal, ответ) попадает в
        bounded session memory для контекста следующих вопросов.
        """
        goal = (goal or "").strip()
        if goal:
            try:
                self._preference_learner.observe_user_message(goal)
            except Exception as exc:  # Relationship learning never blocks execution.
                log.debug("Обучение предпочтений пропущено: %s", exc)
            try:
                learn_facts(self._settings, goal)
            except Exception as exc:  # noqa: BLE001 — память не ломает миссию
                log.debug("Извлечение фактов не удалось: %s", exc)

        outcome = self._execute_core(goal, mission, cancel)
        try:
            task_type = self._personality.infer_task_type(goal, mode=outcome.mode)
            outcome.text = self._personality.naturalize(
                outcome.text, verified=outcome.verified, task_type=task_type,
            )
            # Streaming has already exposed cumulative text. Apply the hard
            # brevity bound only at a non-streaming conversational boundary.
            if outcome.mode == "conversation" and getattr(self._stream_tls, "sink", None) is None:
                outcome.text = self._personality.adapt_response(
                    outcome.text,
                    self._personality.style_for(
                        user_context=self._user_context, task_type=task_type,
                        user_preference=self._preference_learner.profile(),
                    ),
                )
        except Exception as exc:  # Personality wording never changes mission state.
            log.debug("Адаптация ответа пропущена: %s", exc)
        try:
            shadow_outcome = "success" if outcome.verified else (
                "unfulfilled" if outcome.mode == "unknown_task" else "failure"
            )
            self._shadow.observe_command(goal, outcome=shadow_outcome)
        except Exception as exc:  # Shadow mode must never affect Active mode.
            log.debug("Shadow command observation skipped: %s", exc)
        self._remember_exchange(goal, outcome)
        return outcome

    def _remember_exchange(self, goal: str, outcome: AgentOutcome) -> None:
        """Записывает пару (user, assistant) в bounded session memory.

        Пустые, отменённые и «пустой ввод» реплики не пишутся. Служебный
        префикс [degraded] из ответа убирается (пользовательская память
        хранит чистый текст).
        """
        try:
            if not goal or outcome.mode in ("empty", "cancelled"):
                return
            text = (outcome.text or "").strip()
            if text.startswith("[degraded] "):
                text = text[len("[degraded] "):]
            self._session.push("user", goal)
            if text:
                self._session.push("assistant", text)
        except Exception as exc:  # noqa: BLE001
            log.debug("Запись в session memory не удалась: %s", exc)

    def _execute_core(self, goal: str, mission: Optional[Mission] = None,
                      cancel: Optional[threading.Event] = None) -> AgentOutcome:
        cancel = cancel or threading.Event()
        goal = (goal or "").strip()
        if not goal:
            return AgentOutcome(text="Сэр, я не расслышал команду.", mode="empty")

        trace: List[str] = []

        # ---- 1. INTENT (мгновенно, офлайн) ----
        intent = resolve_keyword_tool(goal, goal)
        trace.append(f"intent={intent}")
        if mission is not None:
            mission.acknowledgement = pick_acknowledgement(intent, goal=goal, settings=self._settings)
            mission.metadata["intent"] = intent
            mission.set_status(MissionStatus.ANALYZING, "определение намерения и риска")
            mission.set_progress(0.1, "анализ намерения")

        # ---- 2. RISK (§21) ----
        risk = assess_risk(goal)
        trace.append(f"risk={risk.level.value}")
        if mission is not None:
            mission.metadata["risk"] = risk.to_dict()

        # ---- 3. CONTEXT: большой ввод -> ingest (§7) ----
        context_tokens = 0
        if len(goal) > self._config.large_input_chars:
            task_id = mission.task_id if mission else "adhoc"
            ingested = ingest_text(task_id, goal, self._settings)
            context_tokens = ingested.estimated_tokens
            trace.append(f"ingest: {ingested.chunk_count} чанков, ~{context_tokens} токенов")
            if mission is not None:
                mission.metadata["ingest"] = {
                    "chunks": ingested.chunk_count,
                    "tokens": context_tokens,
                    "chars": ingested.raw_char_count,
                }

        if cancel.is_set():
            return AgentOutcome(text="Задача отменена.", mode="cancelled", trace=trace)

        # ---- 4. SKILL: есть ли готовый навык под эту цель (§9) ----
        skill = self._match_skill(goal)
        if skill is not None:
            trace.append(f"найден навык '{skill.name}' ({skill.status.value})")
            if mission is not None:
                mission.metadata["skill"] = skill.name

        # ---- 5. MODE + ROUTING (§15) ----
        routing = self._model_router.route(goal, context_tokens=context_tokens)
        trace.append(f"route -> {routing.tier.value} ({routing.reason})")
        if mission is not None:
            mission.model_used = routing.tier.value
            mission.metadata["routing"] = routing.to_dict()

        # ---- 5b. MEMORY: извлечение релевантного контекста (P0-5) ----
        memory_ctx = self._retrieve_context(goal)
        if memory_ctx and mission is not None:
            mission.metadata["memory_context"] = memory_ctx[:600]

        # ---- 6. RESEARCH MODE (§18): исследование — отдельный конвейер ----
        if is_research_goal(goal):
            trace.append("режим: research workflow")
            return self._handle_research(goal, mission, cancel, trace)

        # ---- 7. FAST PATH (§3): простая команда — без тяжёлого планирования ----
        fast = self._try_fast_path(goal, intent, mission, cancel, risk)
        if fast is not None:
            fast.trace = trace + fast.trace
            return fast

        # ---- 7b. CONVERSATION GATE (Sprint 2): разговор без действия ----
        # Офлайн-роутер уверенно распознал разговор: модель НЕ получает список
        # инструментов и НЕ генерирует JSON-план — слабая fast-модель физически
        # не может «позвать» list_files. Настоящие действия идут мимо гейта
        # (явные глаголы/интент файлов/приложений/системы) в planner ниже.
        is_conversation, conv_reason = classify_conversation(goal, intent)
        if is_conversation:
            trace.append(f"conversation gate: {conv_reason}")
            if mission is not None:
                mission.metadata["conversation_gate"] = conv_reason
            return self._answer_conversation(
                goal, mission, cancel, trace, routing, memory_ctx,
            )

        if cancel.is_set():
            return AgentOutcome(text="Задача отменена.", mode="cancelled", trace=trace)

        # ---- 7. TOOL RETRIEVAL (§12): модели идут ТОЛЬКО релевантные тулзы ----
        caps = CAPABILITIES.retrieve(goal, top_k=self._config.max_tool_retrieval)
        trace.append(f"tool retrieval -> {[c.name for c in caps]}")

        if mission is not None:
            mission.set_status(MissionStatus.PLANNING, "выбор способа выполнения")
            mission.set_progress(0.3, "планирование")

        # ---- 8. PLAN: структурированное решение модели (§13) ----
        decision, plan_error = self._decide_with_model(
            goal, caps, mission, cancel,
            routing=routing, memory_ctx=memory_ctx,
        )

        if cancel.is_set():
            return AgentOutcome(text="Задача отменена.", mode="cancelled", trace=trace)

        if decision is None:
            # Сбой модели (сеть/провайдер/ключ) — временная ошибка инфраструктуры,
            # а НЕ «не умею» (§29): никаких черновиков навыков и сырых ошибок
            # в чат — короткая честная фраза, детали только в лог.
            if plan_error.startswith(MODEL_ERROR_PREFIX):
                return self._handle_model_unavailable(goal, mission, trace, plan_error)
            trace.append(f"planning failed: {plan_error}")
            return self._handle_unknown(goal, caps, mission, trace, plan_error)

        if not decision.needs_tool:
            # Модель решила ответить текстом — обычный диалог.
            text = decision.answer.strip() or "Готов, сэр."
            # §29 — но если модель ФАКТИЧЕСКИ отказалась (для задачи, требующей
            # действия) — это НЕ "я не умею" (§29). Перенаправляем на путь
            # неизвестной задачи: исследовать и научиться.
            if _is_model_refusal(text, goal):
                trace.append("модель отказалась/не смогла — путь неизвестной задачи (§29)")
                return self._handle_unknown(goal, caps, mission, trace,
                                            reason="модель не предложила способа")
            trace.append("режим: разговор без инструмента")
            if mission is not None:
                mission.set_progress(1.0, "ответ сформирован")
            return AgentOutcome(text=text, verified=True, mode="conversation", trace=trace)

        # ---- 9. RISK GATE перед выполнением (§21) ----
        exec_risk = assess_risk(goal, decision.tool, decision.arguments)
        if exec_risk.needs_confirmation and not self._config.auto_confirm_high_risk:
            trace.append(f"HIGH risk -> требуется подтверждение: {exec_risk.reasons}")
            conf_id = uuid.uuid4().hex
            if mission is not None:
                mission.emit(EVENT_CONFIRMATION_REQUIRED, payload={
                    "confirmation_id": conf_id,
                    "tool": decision.tool,
                    "arguments": decision.arguments,
                    "risk": exec_risk.to_dict(),
                    "prompt": exec_risk.confirmation_prompt(),
                })
                mission.set_status(MissionStatus.PAUSED, "ожидание подтверждения пользователя")
            # Регистрируем ожидающее подтверждение, чтобы позже можно
            # было ответить (confirm/reject) и продолжить или отменить.
            with self._lock:
                self._pending_confirmations[conf_id] = {
                    "goal": goal,
                    "tool": decision.tool,
                    "args": decision.arguments,
                    "risk": exec_risk,
                    "caps": caps,
                    "mission": mission,
                    "cancel": cancel,
                    "trace": trace,
                }
            # П1 §1.3 (voice-first): если пользователь не ответит в голос/текст
            # за confirmation_timeout_sec — безопасный авто-reject (отказ).
            self._start_confirmation_watchdog(conf_id)
            return AgentOutcome(
                text=exec_risk.confirmation_prompt(),
                verified=False,
                needs_confirmation=True,
                confirmation_id=conf_id,
                risk=exec_risk,
                tool_used=decision.tool,
                mode="confirmation",
                trace=trace,
            )

        # ---- 10. EXECUTION + VERIFICATION + REPAIR ----
        return self._execute_verified(
            goal=goal,
            tool=decision.tool,
            args=decision.arguments,
            mission=mission,
            cancel=cancel,
            trace=trace,
            risk=exec_risk,
            caps=caps,
        )

    # ------------------------------------------------------------------ #
    #  Роутинг модели (P0-2) + память (P0-5) + подтверждение (P0-3)
    # ------------------------------------------------------------------ #

    def _tier_breaker_open(self, tier) -> bool:
        """Sprint 3 STEP 5: breaker модели тира разомкнут (серии сбоев).

        Ключ — ``provider:model``, а не просто провайдер: несколько тиров
        могут сидеть на одном провайдере (anymodel), и падение одной
        модели (am/free) не должно блокировать остальные (cx/gpt-5.5).
        """
        try:
            provider = self._settings.get_provider(tier)
            model_id = self._settings.get_model_id(tier) or ""
            return breaker.is_open(f"{provider}:{model_id}")
        except Exception:  # noqa: BLE001 — конфиг может быть урезан в тестах
            return False

    def _backend_for_routing(self, routing: Optional[RoutingDecision]):
        """Возвращает (backend, tier) по решению ModelRouter (cloud-first).

        Идёт по цепочке [routing.tier] + fallback_chain, берёт первый
        реально доступный тир. Тиры с разомкнутым circuit breaker'ом
        (Sprint 3: 3 подряд сбоя провайдера) пропускаются до конца
        cooldown. Если ни один внешний не доступен — честный офлайн-фолбэк
        на ЛОКАЛЬНУЮ модель TIER 4 (§17). Решение роутера обязано дойти
        до реального вызова модели (иначе выбор бессмыслен).
        """
        chain: List[Any] = []
        if routing is not None:
            chain = [routing.tier] + list(routing.fallback_chain)
        else:
            chain = [Tier.FAST]

        skipped_breakers: List[str] = []
        for tier in chain:
            if self._tier_breaker_open(tier):
                skipped_breakers.append(str(tier))
                continue
            try:
                if not self._settings.is_tier_available(tier):
                    continue
                backend = get_llm_backend(self._settings, tier)
                return backend, tier
            except (BackendUnavailable, BackendConfigError) as exc:
                log.debug("Тир %s недоступен для планирования: %s", tier, exc)
                continue
        if skipped_breakers:
            log.info("Circuit breaker: тиры %s пропущены (недавние сбои провайдеров)",
                     ", ".join(skipped_breakers))

        # Graceful offline fallback на локальную модель (TIER 4, без сети).
        try:
            return get_offline_backend(self._settings), Tier.FAST
        except Exception as exc:
            log.warning("Локальный фолбэк недоступен: %s", exc)
            return None, None

    def _fallback_backend(self, routing: Optional[RoutingDecision], tried,
                          policy_override=None):
        """Следующий доступный бэкенд после ``tried`` (для повтора при сбое).

        ``policy_override`` — короткая «разговорная» политика для простых
        задач: фолбэк не должен ждать полный бюджет аналитического тира.
        Тиры с разомкнутым breaker'ом пропускаются (Sprint 3).
        """
        chain: List[Any] = []
        if routing is not None:
            chain = [routing.tier] + list(routing.fallback_chain)
        else:
            chain = [Tier.FAST]
        if tried is not None:
            try:
                idx = chain.index(tried)
                chain = chain[idx + 1:]
            except ValueError:
                pass
        for tier in chain:
            if self._tier_breaker_open(tier):
                continue
            try:
                if not self._settings.is_tier_available(tier):
                    continue
                return get_llm_backend(self._settings, tier,
                                       policy_override=policy_override), tier
            except (BackendUnavailable, BackendConfigError):
                continue
        return None, None

    def _retrieve_context(self, goal: str) -> str:
        """Извлекает релевантный контекст из локальной памяти (граф, офлайн)."""
        if self._graph is None:
            return ""
        try:
            nodes = self._graph.search_nodes(goal, top_k=3)
            if not nodes:
                return ""
            parts: List[str] = []
            for n in nodes:
                label = (n.get("label") or "").strip()
                props = n.get("properties") or {}
                detail = (
                    props.get("detail") or props.get("value")
                    or props.get("text") or ""
                )
                if detail:
                    parts.append(f"- {detail}")
                elif label:
                    parts.append(f"- {label}")
            return "\n".join(parts)
        except Exception as exc:
            log.debug("Извлечение памяти не удалось: %s", exc)
            return ""

    def _store_fact(self, label: str, detail: str = "") -> None:
        """Сохраняет факт в локальную память (граф). Не роняет выполнение."""
        if self._graph is None:
            return
        try:
            self._graph.create_node(label, {"detail": detail, "source": "agent"})
        except Exception as exc:
            log.debug("Сохранение факта не удалось: %s", exc)

    def answer_confirmation(self, confirmation_id: str, approved: bool) -> Optional[AgentOutcome]:
        """Отвечает на ожидающее подтверждение HIGH-risk операции (§21).

        Args:
            confirmation_id: id, выданный при запросе подтверждения.
            approved: True — выполнить операцию, False — отклонить.

        Returns:
            AgentOutcome с результатом, либо None если подтверждение не найдено.
        """
        with self._lock:
            pending = self._pending_confirmations.pop(confirmation_id, None)
            # Отменяем таймер ожидания — человек уже ответил (П1 §1.3).
            timer = self._confirmation_timers.pop(confirmation_id, None)
            if timer is not None:
                timer.cancel()
        if pending is None:
            return None

        goal = pending["goal"]
        tool = pending["tool"]
        args = pending["args"]
        risk = pending["risk"]
        caps = pending["caps"]
        mission = pending["mission"]
        cancel = pending["cancel"]
        trace = pending["trace"]

        if not approved:
            if mission is not None:
                mission.set_status(MissionStatus.CANCELLED, "отклонено пользователем")
                mission.emit(EVENT_TASK_FAILED, payload={"reason": "confirmation_rejected"})
            return AgentOutcome(
                text="Понял, сэр. Действие отменено.",
                verified=False,
                mode="confirmation_rejected",
                risk=risk,
                tool_used=tool,
                trace=trace,
            )

        # Подтверждено — выполняем.
        if mission is not None:
            mission.set_status(MissionStatus.EXECUTING, "подтверждено, выполняю")
        return self._execute_verified(
            goal=goal, tool=tool, args=args, mission=mission,
            cancel=cancel, trace=trace, risk=risk, caps=caps,
        )

    # ------------------------------------------------------------------ #
    #  П1 §1.3 — voice-first confirmation watchdog
    # ------------------------------------------------------------------ #

    def _start_confirmation_watchdog(self, confirmation_id: str) -> None:
        """Запускает таймер ожидания подтверждения (П1 §1.3).

        Если пользователь не ответит голосом/текстом за
        ``confirmation_timeout_sec`` — безопасный авто-reject (отказ).
        Таймаут отключается значением <= 0.
        """
        timeout = float(getattr(self._config, "confirmation_timeout_sec", 30.0))
        if timeout <= 0:
            return

        def _on_timeout() -> None:
            with self._lock:
                if confirmation_id not in self._pending_confirmations:
                    return  # уже ответили или отменили
            # Авто-reject: таймаут = молчаливый отказ (безопаснее).
            self.answer_confirmation(confirmation_id, approved=False)

        with self._lock:
            old = self._confirmation_timers.pop(confirmation_id, None)
            if old is not None:
                old.cancel()
            timer = threading.Timer(timeout, _on_timeout)
            timer.daemon = True
            self._confirmation_timers[confirmation_id] = timer
            timer.start()

    # ------------------------------------------------------------------ #
    #  §18 — Research workflow
    # ------------------------------------------------------------------ #

    def _handle_research(self, goal: str, mission: Optional[Mission],
                         cancel: threading.Event,
                         trace: List[str]) -> AgentOutcome:
        """Отдельный конвейер исследования (§18).

        Верификация здесь особая: «готово» только если собраны и
        перекрёстно проверены источники (§14).
        """
        engine = ResearchEngine(self._settings)
        report = engine.run(goal, mission=mission, cancel=cancel)
        trace.append(
            f"research: прочитано {len(report.sources_read)}, "
            f"недоступно {len(report.sources_failed)}, находок {len(report.findings)}"
        )
        if mission is not None:
            mission.metadata["research"] = {
                "sources_read": report.sources_read,
                "sources_failed": report.sources_failed,
                "findings": len(report.findings),
                "verified": report.verified,
            }

        verification = VerificationResult(
            verified=report.verified,
            method="research_cross_check",
            detail=(
                f"источников прочитано: {len(report.sources_read)}, "
                f"подтверждённых находок: "
                f"{sum(1 for f in report.findings if f.claim_type.value == 'verified_fact')}"
            ),
            strict=True,
        )
        if mission is not None:
            mission.emit(EVENT_VERIFICATION, payload=verification.to_dict())

        return AgentOutcome(
            text=report.to_text(),
            verified=report.verified,
            verification=verification,
            mode="research",
            trace=trace,
        )

    # ------------------------------------------------------------------ #
    #  §3 — FAST PATH: короткий цикл для простых задач
    # ------------------------------------------------------------------ #

    def _try_fast_path(self, goal: str, intent: str, mission: Optional[Mission],
                       cancel: threading.Event,
                       risk: RiskAssessment) -> Optional[AgentOutcome]:
        """Детерминированный быстрый путь без планирования (§3).

        Срабатывает только когда retrieval даёт ОДИН очевидный инструмент
        с LOW риском и аргументы извлекаются тривиально.
        """
        if risk.needs_confirmation:
            return None
        if intent not in ("app", "system"):
            return None

        caps = CAPABILITIES.retrieve(goal, top_k=2)
        if not caps:
            return None
        cap = caps[0]

        args = self._extract_simple_args(goal, cap)
        if args is None:
            return None

        exec_risk = assess_risk(goal, cap.name, args)
        if exec_risk.needs_confirmation:
            return None

        log.info("FAST PATH: %s(%s)", cap.name, redact_args(args))
        outcome = self._execute_verified(
            goal=goal, tool=cap.name, args=args, mission=mission, cancel=cancel,
            trace=[f"fast path -> {cap.name}"], risk=exec_risk, caps=caps,
        )
        outcome.mode = "fast_path"
        return outcome

    def _extract_simple_args(self, goal: str, cap: Capability) -> Optional[Dict[str, Any]]:
        """Тривиальное извлечение аргументов для fast path (без модели)."""
        text = goal.strip().rstrip(".!?")
        lowered = text.lower()

        if cap.name in ("open_app", "close_app"):
            for verb in ("открой", "открыть", "запусти", "запустить", "включи",
                         "закрой", "закрыть", "заверши", "open", "launch", "close", "start"):
                if lowered.startswith(verb):
                    name = text[len(verb):].strip(" ,:—-")
                    # отбрасываем служебные слова
                    for filler in ("приложение ", "программу ", "app "):
                        if name.lower().startswith(filler):
                            name = name[len(filler):]
                    if name:
                        return {"name": name}
            return None

        if cap.name == "system_status":
            return {}

        if cap.name == "volume":
            if any(w in lowered for w in ("выключи звук", "mute", "без звука")):
                return {"action": "mute"}
            if any(w in lowered for w in ("тише", "убавь", "down")):
                return {"action": "down"}
            if any(w in lowered for w in ("громче", "прибавь", "up")):
                return {"action": "up"}
            return None

        return None

    # ------------------------------------------------------------------ #
    #  §13 — Структурированное решение модели
    # ------------------------------------------------------------------ #

    def _decide_with_model(self, goal: str, caps: List[Capability],
                           mission: Optional[Mission],
                           cancel: threading.Event,
                           routing: Optional[RoutingDecision] = None,
                           memory_ctx: str = ""):
        """Спрашивает модель, что делать, и валидирует ответ (§13).

        При плохом JSON — повторный запрос с текстом ошибки (repair, §13).
        Использует backend, выбранный ``ModelRouter`` (§15, cloud-first):
        решение роутера ДОЛЖНО доходить до реального вызова модели, иначе
        выбор тира бессмыслен (P0-2). Локальная FAST-модель — только
        офлайн-фолбэк.

        Args:
            goal: цель пользователя.
            caps: отобранные релевантные инструменты.
            mission: опциональная миссия (для событий/статуса).
            cancel: флаг отмены.
            routing: решение ModelRouter (требуемый тир + цепочка фолбэков).
            memory_ctx: релевантный контекст памяти (P0-5), вставляется в промпт.

        Returns:
            ``(ToolCallDecision | None, error_text)``.
        """
        # Sprint 3 TIER 2: JSON-план строит минимум внешний тир (analyst):
        # надёжный tool calling важнее скорости планирования. Разговорный
        # путь сюда не доходит (conversation gate Sprint 2).
        if routing is not None:
            routing = self._model_router.route_for_planning(routing)
        backend, used_tier = self._backend_for_routing(routing)
        if backend is None:
            return None, MODEL_ERROR_PREFIX + "ни одна модель недоступна (ни облачная, ни локальный фолбэк)"
        if mission is not None and used_tier is not None:
            mission.model_used = used_tier.value
            if routing is not None and used_tier is not routing.tier:
                mission.metadata["degraded"] = True

        known = [c.name for c in caps]
        tools_desc = describe_tools_for_model(caps, self._registry) or "(нет подходящих инструментов)"

        memory_block = ""
        if memory_ctx:
            memory_block = (
                "\n\nКонтекст из памяти (используй при ответе, если релевантно):\n"
                f"{memory_ctx}\n"
            )

        # Sprint 4 TIER 2: persona + фокус на точность tool calling.
        # История/факты в tool-промпт НЕ идут (спринт STEP 2.4).
        from persona.system_prompt import build_agent_system_prompt
        persona_line = build_agent_system_prompt(self._settings, tier="plan")
        system = (
            f"{persona_line}\n"
            "Твоя задача — решить, КАК выполнить цель.\n"
            "Верни СТРОГО ОДИН JSON-объект без markdown и пояснений:\n"
            f"{PLAN_SCHEMA_HINT}\n"
            "Правила:\n"
            "- Если для цели подходит инструмент — укажи его имя в 'tool' и заполни 'arguments'.\n"
            "- Если инструмент не нужен (обычный разговор) — 'tool': null и заполни 'answer'.\n"
            "- Никогда не выдумывай инструменты, которых нет в списке.\n"
            "- 'verification' — как фактически проверить, что цель достигнута."
        )
        user = (
            f"Доступные инструменты:\n{tools_desc}\n\n"
            f"Цель пользователя: {goal}\n"
            f"{memory_block}\n"
            "Верни только JSON."
        )

        last_error = ""
        for attempt in range(1, self._config.max_structured_retries + 2):
            if cancel.is_set():
                return None, "отменено"

            prompt = user if attempt == 1 else (
                f"{user}\n\nПредыдущий ответ был отклонён: {last_error}\n"
                "Исправь и верни ТОЛЬКО валидный JSON."
            )
            try:
                raw = self._stream_consume(backend, [{"role": "user", "content": prompt}], system)
            except (BackendUnavailable, BackendConfigError) as exc:
                # Попробуем следующий тир из цепочки фолбэка (cloud->...->local).
                log.warning("Модель недоступна (%s), пробуем фолбэк: %s", used_tier, exc)
                # Простая (разговорная) задача: фолбэк тоже короткий — нечего
                # ждать полный бюджет аналитического тира ради «привет».
                fb_policy = (
                    {"timeout": getattr(self._settings.limits, "fast_tier_timeout_sec", None),
                     "max_retries": getattr(self._settings.limits, "fast_tier_max_retries", None)}
                    if routing is not None and routing.tier is Tier.FAST else None
                )
                fb_backend, fb_tier = self._fallback_backend(routing, tried=used_tier,
                                                             policy_override=fb_policy)
                if fb_backend is None:
                    return None, MODEL_ERROR_PREFIX + f"модель недоступна: {exc}"
                backend, used_tier = fb_backend, fb_tier
                if mission is not None:
                    mission.model_used = used_tier.value
                    mission.metadata["degraded"] = True
                try:
                    raw = self._stream_consume(backend, [{"role": "user", "content": prompt}], system)
                except Exception as exc2:
                    return None, MODEL_ERROR_PREFIX + f"модель недоступна: {exc2}"
            except Exception as exc:
                log.warning("Модель не ответила на планирование: %s", exc)
                return None, MODEL_ERROR_PREFIX + f"модель недоступна: {exc}"

            parsed = parse_structured(raw, required_keys=None)
            if not parsed.ok:
                last_error = parsed.error
                log.info("Плохой JSON от модели (попытка %d): %s", attempt, last_error)
                continue

            decision, err = validate_tool_call(
                parsed.data or {},
                known,
                schema_lookup=lambda n: getattr(self._registry.get(n), "input_schema", None),
            )
            if decision is None:
                last_error = err
                log.info("Невалидный tool call (попытка %d): %s", attempt, err)
                continue

            if mission is not None:
                mission.metadata["decision"] = decision.to_dict()
                if decision.needs_tool:
                    mission.add_step(
                        description=decision.reason or f"вызов {decision.tool}",
                        tool=decision.tool,
                        args=decision.arguments,
                    )
                    mission.emit(EVENT_PLAN_READY, payload={"plan": mission.plan})
            return decision, ""

        return None, last_error or "модель не смогла вернуть валидное решение"

    # ------------------------------------------------------------------ #
    #  §14 + §10/§11 — Выполнение с фактической проверкой и самоисправлением
    # ------------------------------------------------------------------ #

    def _execute_verified(self, goal: str, tool: str, args: Dict[str, Any],
                          mission: Optional[Mission], cancel: threading.Event,
                          trace: List[str], risk: RiskAssessment,
                          caps: List[Capability]) -> AgentOutcome:
        """EXECUTE -> VERIFY -> (REPAIR) -> RESULT.

        «Готово» произносится ТОЛЬКО при ``verification.verified`` (§14).
        """
        context = ToolContext(user_id="default", settings=self._settings, state=None)

        if mission is not None:
            mission.set_status(MissionStatus.EXECUTING, f"выполняю {tool}")
            mission.set_progress(0.5, f"выполнение: {tool}")
            mission.note_tool(tool)
            mission.emit(EVENT_STEP_STARTED, payload={"tool": tool, "args": args})
            mission.emit(EVENT_TOOL_CALLED, payload={"tool": tool, "args": args})

        result = execute_tool(self._registry, tool, args, context)
        trace.append(f"execute {tool}({args}) -> ok={result.ok}")

        if mission is not None:
            mission.emit(EVENT_TOOL_RESULT, payload={
                "tool": tool, "ok": result.ok,
                "output": str(result.output)[:500] if result.output else None,
                "error": result.error,
            })

        # ---- VERIFY (§14) ----
        if mission is not None:
            mission.set_status(MissionStatus.VERIFYING, "фактическая проверка результата")
            mission.set_progress(0.75, "проверка результата")

        verification = verify_action_result(result)
        trace.append(f"verify -> {verification.verified} ({verification.method}: {verification.detail})")
        if mission is not None:
            mission.emit(EVENT_VERIFICATION, payload=verification.to_dict())

        # ---- REPAIR (§10, §11) ----
        if not verification.verified:
            if mission is not None:
                mission.note_error(result.error or verification.detail)
                mission.set_status(MissionStatus.REPAIRING, "первый способ не сработал")
                mission.set_progress(0.6, "исправление")
                mission.emit(EVENT_REPAIR_STARTED, payload={
                    "tool": tool, "reason": result.error or verification.detail,
                })

            log.info("Verification не прошла — вход в repair loop (%s)", tool)
            # Sprint 3 STEP 4: повторный риск-гейт. Каждый retry (патч
            # аргументов / fallback-инструмент / повтор) проходит ТУ ЖЕ
            # проверку §21, что и первый вызов: переформулировкой нельзя
            # обойти подтверждение HIGH-risk операции.
            def _repair_risk_gate(call_tool: str, call_args: Dict[str, Any]) -> Optional[str]:
                gate_risk = assess_risk(goal, call_tool, call_args)
                if gate_risk.needs_confirmation and not self._config.auto_confirm_high_risk:
                    return "; ".join(gate_risk.reasons) or "повышенный риск операции"
                return None

            repair = self._repair.run(
                tool_name=tool,
                args=args,
                context=context,
                mission=mission,
                verification=lambda r: verify_action_result(r).verified,
                risk_gate=_repair_risk_gate,
            )
            trace.extend(f"repair: {t}" for t in repair.trace)

            if mission is not None:
                mission.emit(EVENT_REPAIR_COMPLETED, payload={
                    "ok": repair.ok, "attempts": repair.attempts,
                    "needs_human": repair.needs_human,
                })

            if repair.ok and repair.final_result is not None:
                result = repair.final_result
                verification = verify_action_result(result)
                if mission is not None:
                    mission.emit(EVENT_VERIFICATION, payload=verification.to_dict())

            elif repair.needs_human:
                if mission is not None:
                    mission.set_status(MissionStatus.PAUSED, "нужно решение пользователя")
                return AgentOutcome(
                    text=repair.human_message, verified=False, needs_confirmation=True,
                    risk=risk, tool_used=tool, verification=verification,
                    mode="needs_human", trace=trace,
                )
            else:
                # A known provider that temporarily failed is still a known
                # capability.  Do not misclassify infrastructure trouble as an
                # unknown task or generate a duplicate skill.
                trace.append("known capability provider failed after repair budget")
                self._shadow.backlog.add(
                    f"repair_{tool}", priority=0.85,
                    reason=result.error or verification.detail,
                )
                return AgentOutcome(
                    text="Источник временно не ответил. Задача сохранена для повторной попытки.",
                    verified=False, verification=verification, tool_used=tool,
                    risk=risk, mode="tool", trace=trace,
                )

        # ---- RESULT ----
        if mission is not None:
            mission.set_progress(1.0, "готово")
        text = self._format_success(result, verification)
        # P0-5: сохраняем успешный факт в локальную память (store/use).
        if verification.verified:
            try:
                self._store_fact(
                    label=f"выполнено: {tool}",
                    detail=f"{goal} -> {str(result.output)[:300]}",
                )
            except Exception as exc:
                log.debug("store_fact не удался: %s", exc)
        return AgentOutcome(
            text=text,
            verified=verification.verified,
            verification=verification,
            tool_used=tool,
            risk=risk,
            mode="tool",
            trace=trace,
        )

    @staticmethod
    def _format_success(result: ActionResult, verification: VerificationResult) -> str:
        """Формирует честный ответ пользователю (§14)."""
        body = str(result.output).strip() if result.output else "Выполнено."
        if not verification.strict:
            # Не врём, что проверили фактически.
            return f"{body}\n\n(Проверка: {verification.detail}.)"
        return body

    # ------------------------------------------------------------------ #
    #  Sprint 2 — прямой разговор (без инструментов и без JSON-плана)
    # ------------------------------------------------------------------ #

    def _answer_conversation(self, goal: str, mission: Optional[Mission],
                             cancel: threading.Event, trace: List[str],
                             routing: Optional[RoutingDecision],
                             memory_ctx: str = "") -> AgentOutcome:
        """Разговорный ответ напрямую: БЕЗ списка инструментов и JSON-плана.

        Гейт ``classify_conversation`` уже уверенно определил, что действия
        нет. Модель получает простой диалоговый промпт — она физически не
        может «позвать» инструмент, потому что их имена ей не показаны.
        Стриминг и фолбэк тиров — те же механизмы, что и в planner-пути.
        """
        if cancel.is_set():
            return AgentOutcome(text="Задача отменена.", mode="cancelled", trace=trace)

        backend, used_tier = self._backend_for_routing(routing)
        if backend is None:
            return self._handle_model_unavailable(
                goal, mission, trace,
                MODEL_ERROR_PREFIX + "ни одна модель недоступна (ни облачная, ни локальный фолбэк)",
            )
        # Sprint 3 STEP 5.2: ответил не тот тир, что роутер выбрал изначально
        # (breaker/недоступность) — это деградация, не маскируем её.
        degraded = routing is not None and used_tier is not None and used_tier is not routing.tier
        if mission is not None and used_tier is not None:
            mission.model_used = used_tier.value
            if degraded:
                mission.metadata["degraded"] = True
            mission.set_status(MissionStatus.ANALYZING, "разговорный ответ")

        # Sprint 4: персона + факты профиля + память графа + тон — в system;
        # bounded-история сессии — в messages (под бюджет TIER 1).
        user = goal
        system = self._build_conversation_prompt(memory_ctx, goal, backend)
        history = self._session.get_recent()
        budget = int(getattr(self._settings.limits, "context_budget_fast_tokens", 2000))
        messages = fit_messages_to_budget(system, history, user, budget)

        try:
            text = self._stream_consume(backend, messages, system, extract_answer=False)
        except (BackendUnavailable, BackendConfigError) as exc:
            log.warning("Модель недоступна (%s) в разговоре, пробуем фолбэк: %s", used_tier, exc)
            fb_policy = (
                {"timeout": getattr(self._settings.limits, "fast_tier_timeout_sec", None),
                 "max_retries": getattr(self._settings.limits, "fast_tier_max_retries", None)}
                if routing is not None and routing.tier is Tier.FAST else None
            )
            fb_backend, fb_tier = self._fallback_backend(routing, tried=used_tier,
                                                         policy_override=fb_policy)
            if fb_backend is None:
                return self._handle_model_unavailable(
                    goal, mission, trace, MODEL_ERROR_PREFIX + f"модель недоступна: {exc}")
            backend, used_tier = fb_backend, fb_tier
            degraded = True
            if mission is not None:
                mission.model_used = used_tier.value
                mission.metadata["degraded"] = True
            # Фолбэк мог привести на офлайн-модель (TIER 4) — персона
            # честно говорит про ограниченный режим.
            system = self._build_conversation_prompt(memory_ctx, goal, backend)
            messages = fit_messages_to_budget(system, history, user, budget)
            try:
                text = self._stream_consume(backend, messages, system, extract_answer=False)
            except Exception as exc2:
                return self._handle_model_unavailable(
                    goal, mission, trace, MODEL_ERROR_PREFIX + f"модель недоступна: {exc2}")

        text = (text or "").strip() or "Я вас слушаю, сэр."
        trace.append("режим: прямой разговор (без инструментов)")
        if degraded:
            trace.append(f"degraded: ответил {used_tier} вместо {routing.tier if routing else '?'}")
            text = f"[degraded] {text}"
        if mission is not None:
            mission.set_progress(1.0, "ответ сформирован")
        return AgentOutcome(text=text, verified=True, mode="conversation",
                            trace=trace, degraded=degraded)

    # ------------------------------------------------------------------ #
    #  Sprint 4 — persona + memory сборка промпта
    # ------------------------------------------------------------------ #

    def _is_offline_backend(self, backend) -> bool:
        """True, если бэкенд — локальная GGUF-модель (TIER 4, офлайн)."""
        try:
            from core.llm.local_qwen import LocalQwenBackend
            return isinstance(backend, LocalQwenBackend)
        except Exception:  # noqa: BLE001
            return False

    def _build_conversation_prompt(self, memory_ctx: str, goal: str,
                                   backend) -> str:
        """System prompt разговорного пути: персона + факты + тон + память.

        Собирается ``persona.build_agent_system_prompt`` (Sprint 4 STEP 3).
        Диалоговая природа пути дописывается явно: никаких инструментов.
        """
        from persona.system_prompt import build_agent_system_prompt

        profile_ctx = ""
        try:
            profile_ctx = get_profile_context(self._settings)
        except Exception as exc:  # noqa: BLE001
            log.debug("Профиль недоступен: %s", exc)

        prompt = build_agent_system_prompt(
            self._settings,
            tier="fast",
            profile_ctx=profile_ctx,
            memory_ctx=(memory_ctx or "")[:400],
            tone=detect_tone(goal),
            offline=self._is_offline_backend(backend),
            personality_context=self._personality_prompt_context(goal),
        )
        return (
            f"{prompt}\n"
            "Это обычный диалог: никаких инструментов, файлов и команд — "
            "просто ответь текстом. Не упоминай инструменты."
        )

    def _personality_prompt_context(self, goal: str) -> str:
        """Retrieves only the few relationship memories relevant now."""
        try:
            profile = self._preference_learner.profile()
            style = self._personality.style_for(
                user_context=self._user_context,
                urgency="high" if bool(self._user_context.get("user_busy")
                                       or self._user_context.get("busy")) else "normal",
                task_type=self._personality.infer_task_type(goal, mode="conversation"),
                user_preference=profile,
            )
            relevant = self._relationship_memory.retrieve(goal, limit=4)
            return self._personality.prompt_fragment(
                style, memories=(item.fact for item in relevant),
            )
        except Exception as exc:
            log.debug("Relationship context недоступен: %s", exc)
            return ""

    # ------------------------------------------------------------------ #
    #  §8, §9, §29 — UNKNOWN != IMPOSSIBLE
    # ------------------------------------------------------------------ #

    def _handle_model_unavailable(self, goal: str, mission: Optional[Mission],
                                  trace: List[str], plan_error: str) -> AgentOutcome:
        """Сбой модели (таймаут/провайдер/ключ) — НЕ «не умею» и НЕ навык.

        Это временная ошибка инфраструктуры: пользователю — короткая
        дружелюбная фраза (без HTTP-кодов и трейсбеков), сырые детали —
        только в лог. Черновик навыка (SkillForge) НЕ создаётся: навыки
        фиксируются только для реальных «не умею», а не для сетевых сбоев.
        """
        detail = plan_error[len(MODEL_ERROR_PREFIX):].strip() or "модель недоступна"
        log.warning("Модель недоступна при обработке цели: %s", detail)
        trace.append(f"model unavailable: {detail}")
        if mission is not None:
            mission.note_error(detail)
            mission.set_progress(1.0, "модель недоступна — ответ не сформирован")
        return AgentOutcome(
            text=MODEL_UNAVAILABLE_TEXT,
            verified=False,
            mode="model_error",
            trace=trace,
        )

    def _handle_unknown(self, goal: str, caps: List[Capability],
                        mission: Optional[Mission], trace: List[str],
                        reason: str = "", attempted_tool: Optional[str] = None) -> AgentOutcome:
        """Путь неизвестной задачи (§8): не «не умею», а «ещё не научен» (§29).

        Здесь мы:
            1. фиксируем, чего не хватило;
            2. создаём черновик навыка в Skill Forge (draft, НЕ stable §9);
            3. возвращаем честный ответ с планом исследования.
        """
        trace.append(f"unknown task path: {reason}")
        # Sprint 9: a task class is resolved before generating another Python
        # tool. Existing primitives are composed into a DAG and verified
        # against desired state; only verified trajectories are learned.
        try:
            from core.capability_engine import (
                CapabilityDefinition, CapabilityEngine, CapabilityKind,
            )
            capability_plan = self._capability_planner.plan(goal)
            trace.append(f"capability acquisition={capability_plan.acquisition}")
            if capability_plan.steps:
                capability_engine = CapabilityEngine(
                    self._capability_catalog, self._registry,
                    context=ToolContext(settings=self._settings),
                )
                capability_report = capability_engine.execute(capability_plan, max_repairs=2)
                trace.extend(f"capability: {item}" for item in capability_report.action_trace)
                if capability_report.needs_confirmation:
                    return AgentOutcome(
                        text="Сэр, для следующего системного изменения требуется подтверждение.",
                        verified=False, needs_confirmation=True,
                        risk=assess_risk(goal), mode="confirmation_required", trace=trace,
                    )
                if capability_report.completed:
                    return AgentOutcome(
                        text="Готово. Проверяйте, сэр.", verified=True,
                        tool_used=capability_plan.capability_id,
                        mode="capability", trace=trace,
                    )
                self._shadow.backlog.add(
                    capability_plan.capability_id or _skill_name_from_goal(goal),
                    priority=0.95,
                    reason="reactive capability execution or verification failed",
                )
                trace.append("failed capability queued for shadow repair")
            elif capability_plan.acquisition == "research":
                experimental_id = _skill_name_from_goal(goal)
                self._capability_catalog.save(CapabilityDefinition(
                    id=experimental_id, description=goal,
                    kind=CapabilityKind.EXPERIMENTAL, confidence=0.3,
                    success_criteria=list(capability_plan.requirements),
                ))
                self._shadow.backlog.add(
                    experimental_id, priority=0.9,
                    reason="reactive unknown request needs capability research",
                )
                trace.append("structured capability research queued")
        except Exception as exc:
            trace.append(f"capability engine skipped: {type(exc).__name__}")

        # Sprint 8: for a low-risk novel request, Shadow Engine may already
        # have a verified local tool ready (or create one with Qwen3-1.7B).
        # The generated-tool sandbox permits only side-effect-free stdlib code;
        # anything risky remains on the ordinary confirmation path below.
        on_demand_risk = assess_risk(goal)
        if not on_demand_risk.needs_confirmation:
            try:
                prepared = self._shadow.prepare_on_demand(goal)
                if prepared is not None:
                    trace.append(f"shadow on-demand: {prepared.name} ({prepared.status}, {prepared.confidence}%)")
                    if prepared.status == "registered":
                        result = execute_tool(
                            self._registry, prepared.name, {"request": goal},
                            ToolContext(settings=self._settings), max_retries=0,
                        )
                        if result.ok:
                            return AgentOutcome(
                                text=str(result.output or "Сейчас разберусь — способ подготовлен."),
                                verified=True, tool_used=prepared.name, mode="tool", trace=trace,
                            )
            except Exception as exc:  # Generated tools never break Active mode.
                trace.append(f"shadow on-demand skipped: {type(exc).__name__}")
        if mission is not None:
            mission.note_error(reason or "нет готового способа")
            mission.metadata["unknown_task"] = True
            # Задача завершена (пусть и без успеха) — прогресс не должен
            # застревать на промежуточном значении.
            mission.set_progress(1.0, "способ не найден — требуется обучение")

        skill_note = ""
        if self._forge is not None:
            try:
                name = _skill_name_from_goal(goal)
                draft = self._forge.create_draft(
                    name=name,
                    goal=goal,
                    task_id=mission.task_id if mission else None,
                    triggers=[goal.strip()[:80].lower()],
                )
                draft.description = (
                    f"Требуется способ для цели: {goal[:160]}. "
                    f"Причина отсутствия готового пути: {reason or 'нет подходящего инструмента'}"
                )
                draft.tools = [c.name for c in caps]
                draft.status = SkillStatus.DRAFT
                self._forge.save(draft)
                trace.append(f"создан черновик навыка '{draft.name}' (draft, не проверен)")
                skill_note = (
                    f"\nЗафиксировал пробел в навыках как черновик «{draft.name}» — "
                    f"он не считается рабочим, пока я его не проверю."
                )
                if mission is not None:
                    mission.metadata["skill_draft"] = draft.name
            except Exception as exc:
                log.warning("Skill Forge не смог создать черновик: %s", exc)

        attempted = f" Пробовал через «{attempted_tool}», не сработало." if attempted_tool else ""
        why = f" Причина: {reason}." if reason else ""
        available = ", ".join(c.name for c in caps) if caps else "нет подходящих"

        from core.shadow import active_mode_message
        text = (
            f"{active_mode_message(goal)}{attempted}{why}\n"
            f"Доступные сейчас инструменты: {available}.\n"
            f"Что я могу сделать дальше: изучить документацию и способ решения, "
            f"собрать процедуру, проверить её на безопасном примере и сохранить как навык."
            f"{skill_note}"
        )
        return AgentOutcome(text=text, verified=False, mode="unknown_task", trace=trace)

    def _match_skill(self, goal: str) -> Optional[SkillManifest]:
        """Ищет готовый навык под цель (§9)."""
        if self._forge is None:
            return None
        try:
            return self._forge.match(goal)
        except Exception as exc:
            log.debug("SkillForge.match упал: %s", exc)
            return None

    # ------------------------------------------------------------------ #
    #  Доступ к модели
    # ------------------------------------------------------------------ #

    def _get_local_backend(self):
        """Локальная Qwen3-4B — офлайн-мозг TIER 4 (§16, Sprint 3).

        Строится НАПРЯМУЮЮ из ``settings.local_model`` (GGUF), а не через
        FAST-тир: провайдер FAST теперь внешний (am/free), и старый путь
        молча возвращал ту же удалённую модель вместо офлайн-фолбэка.
        None, если GGUF недоступна.
        """
        try:
            backend = get_offline_backend(self._settings)
            if not backend.is_available():
                log.warning("Локальная модель недоступна: %s", backend.unavailable_reason())
                return None
            return backend
        except Exception as exc:
            log.warning("Не удалось получить локальный бэкенд: %s", exc)
            return None


def _is_model_refusal(text: str, goal: str) -> bool:
    """§29 — распознаёт, что модель ФАКТИЧЕСКИ отказалась/не смогла (для
    задачи, которая требует действия), а не просто вежливо ответила.

    Для тривиальных целей («привет», «спасибо») отказом это НЕ считается.
    """
    low = (text or "").lower().strip()
    if not low:
        return True  # пустой ответ = не справилась

    refusal_markers = [
        "у меня нет", "я не умею", "я не могу", "не могу выполнить",
        "не имею доступа", "нет такого инструмента", "не располагаю",
        "я физически", "это невозможно", "к сожалению, не могу",
        "i can't", "i cannot", "i don't have", "i am unable", "i'm unable",
        "no tool", "нет подходящ", "требуется специализированн",
        "требуется доступ", "необходим доступ", "необходимо специализирован",
    ]
    if any(m in low for m in refusal_markers):
        return True

    # «Я не умею» часто замаскировано под «для этого нужна программа/сервис».
    need_markers = ["требуется программное обеспечение", "требуется специальн",
                    "нужен специальн", "требуется доступ к", "нет возможности"]
    if any(m in low for m in need_markers):
        return True

    return False


def _skill_name_from_goal(goal: str) -> str:
    """Короткое имя навыка из цели пользователя."""
    words = [w for w in goal.strip().split() if w.isalnum() or w.isalpha()]
    base = "_".join(words[:5]).lower() if words else "unknown_task"
    return base[:60] or "unknown_task"
