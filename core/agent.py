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
    get_llm_backend,
)
from core.model_router import ModelRouter, RoutingDecision
from core.repair import RepairLoop
from core.research import ResearchEngine, is_research_goal
from core.router.intent_router import resolve_keyword_tool
from core.safety import RiskAssessment, assess_risk
from core.redact import redact_args
from core.skill_forge import SkillForge, SkillManifest, SkillStatus
from core.structured import PLAN_SCHEMA_HINT, parse_structured, validate_tool_call
from core.task_runtime import (
    EVENT_CONFIRMATION_REQUIRED,
    EVENT_PLAN_READY,
    EVENT_REPAIR_COMPLETED,
    EVENT_REPAIR_STARTED,
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
            f"Ты — Джарвис. Пользователь только что дал команду: \"{goal}\". "
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
    ) -> None:
        """
        Args:
            settings: конфигурация проекта.
            council: существующий ``CouncilRouter`` (переиспользуем §26).
                Если None — создаётся лениво при первой необходимости.
            config: настройки поведения агента.
        """
        self._settings = settings
        self._config = config or AgentConfig()
        self._council = council
        self._registry = DEFAULT_REGISTRY
        self._model_router = ModelRouter(settings)
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
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ #
    #  Публичный вход: исполнение миссии
    # ------------------------------------------------------------------ #

    def run_mission(self, mission: Mission, cancel: threading.Event) -> str:
        """Исполняет миссию целиком. Возвращает финальный текст ответа.

        Вызывается ``TaskRuntime`` в отдельном потоке. Никаких ограничений
        на длительность (§4) — только реальная отмена через ``cancel``.
        """
        outcome = self.execute(mission.goal, mission=mission, cancel=cancel)
        mission.verification = outcome.verification.to_dict() if outcome.verification else None
        mission.metadata["mode"] = outcome.mode
        mission.metadata["verified"] = outcome.verified
        if outcome.needs_confirmation:
            mission.metadata["needs_confirmation"] = True
        return outcome.text

    def execute(self, goal: str, mission: Optional[Mission] = None,
                cancel: Optional[threading.Event] = None) -> AgentOutcome:
        """Главный цикл: intent -> risk -> mode -> plan -> execute -> verify -> repair.

        Цикл сокращается автоматически (§3): тривиальный разговор и простые
        команды не проходят через планирование.
        """
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
            # Модель недоступна/не смогла — это НЕ повод сказать "не умею" (§29).
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

    def _backend_for_routing(self, routing: Optional[RoutingDecision]):
        """Возвращает (backend, tier) по решению ModelRouter (cloud-first).

        Идёт по цепочке [routing.tier] + fallback_chain, берёт первый
        реально доступный тир. Если ни один внешний не доступен — честный
        офлайн-фолбэк на локальную FAST (§17). Решение роутера обязано
        дойти до реального вызова модели (иначе выбор бессмыслен).
        """
        chain: List[Any] = []
        if routing is not None:
            chain = [routing.tier] + list(routing.fallback_chain)
        else:
            chain = [Tier.FAST]

        for tier in chain:
            try:
                if not self._settings.is_tier_available(tier):
                    continue
                backend = get_llm_backend(self._settings, tier)
                return backend, tier
            except (BackendUnavailable, BackendConfigError) as exc:
                log.debug("Тир %s недоступен для планирования: %s", tier, exc)
                continue

        # Graceful offline fallback на локальную модель.
        try:
            return self._get_local_backend(), Tier.FAST
        except Exception as exc:
            log.warning("Локальный фолбэк недоступен: %s", exc)
            return None, None

    def _fallback_backend(self, routing: Optional[RoutingDecision], tried):
        """Следующий доступный бэкенд после ``tried`` (для повтора при сбое)."""
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
            try:
                if not self._settings.is_tier_available(tier):
                    continue
                return get_llm_backend(self._settings, tier), tier
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
        backend, used_tier = self._backend_for_routing(routing)
        if backend is None:
            return None, "ни одна модель недоступна (ни облачная, ни локальный фолбэк)"
        if mission is not None and used_tier is not None:
            mission.model_used = used_tier.value

        known = [c.name for c in caps]
        tools_desc = describe_tools_for_model(caps, self._registry) or "(нет подходящих инструментов)"

        memory_block = ""
        if memory_ctx:
            memory_block = (
                "\n\nКонтекст из памяти (используй при ответе, если релевантно):\n"
                f"{memory_ctx}\n"
            )

        system = (
            "Ты — J.A.R.V.I.S., операционная интеллектуальная система на компьютере "
            "пользователя. Твоя задача — решить, КАК выполнить цель.\n"
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
                raw = backend.chat([{"role": "user", "content": prompt}], system=system)
            except (BackendUnavailable, BackendConfigError) as exc:
                # Попробуем следующий тир из цепочки фолбэка (cloud->...->local).
                log.warning("Модель недоступна (%s), пробуем фолбэк: %s", used_tier, exc)
                fb_backend, fb_tier = self._fallback_backend(routing, tried=used_tier)
                if fb_backend is None:
                    return None, f"модель недоступна: {exc}"
                backend, used_tier = fb_backend, fb_tier
                if mission is not None:
                    mission.model_used = used_tier.value
                try:
                    raw = backend.chat([{"role": "user", "content": prompt}], system=system)
                except Exception as exc2:
                    return None, f"модель недоступна: {exc2}"
            except Exception as exc:
                log.warning("Модель не ответила на планирование: %s", exc)
                return None, f"модель недоступна: {exc}"

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
            repair = self._repair.run(
                tool_name=tool,
                args=args,
                context=context,
                mission=mission,
                verification=lambda r: verify_action_result(r).verified,
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
                # §11 — исчерпали разумные пути: честно сообщаем, БЕЗ "готово" (§14).
                return self._handle_unknown(
                    goal, caps, mission, trace,
                    reason=result.error or verification.detail,
                    attempted_tool=tool,
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
    #  §8, §9, §29 — UNKNOWN != IMPOSSIBLE
    # ------------------------------------------------------------------ #

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

        text = (
            f"Готового способа для этой задачи у меня пока нет — я ещё этому не научен.{attempted}{why}\n"
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
        """Локальная Qwen3-4B — быстрый мозг (§16). None, если недоступна."""
        try:
            from core.llm import Tier, get_llm_backend
            backend = get_llm_backend(self._settings, Tier.FAST)
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
