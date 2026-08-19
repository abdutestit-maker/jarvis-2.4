"""Совет мудрецов — оркестратор выбора и вызова моделей.

``CouncilRouter.route(state)`` — единая точка входа для одного витка
обработки запроса пользователя:

    1. keyword-роутер определяет категорию намерения (мгновенно, офлайн);
    2. **ЕДИНЫЙ** выбор тира делегируется ``ModelRouter`` — именно он
       решает, отвечает ли локальная модель (FAST) или нужна эскалация
       к более сильной (analyst/coder/architect). Это устраняет второй,
       параллельный путь классификации (P5 §5.7: REPL/CouncilRouter и
       submit_goal → Agent.run_mission теперь используют один и тот же
       ModelRouter, поэтому любой ввод — консольный или через WebSocket —
       маршрутизируется одинаково);
    3. генерируем ответ выбранным бэкендом (или честный fallback на
       локальную FAST при недоступности внешних).

Метод НЕ бросает необработанных исключений наружу: любая ошибка ловится,
логируется и записывается в ``state["error"]`` + ``state["response"]``.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from config.settings import Settings
from core.llm import (
    BackendConfigError,
    BackendUnavailable,
    get_llm_backend,
    LLMBackend,
    Tier,
)
from core.model_router import ModelRouter
from core.router.intent_router import resolve_keyword_tool
from core.router.local_face import LocalFace
from core.state import JarvisState, Message
from core.utils.logger import get_logger

__all__ = ["CouncilRouter"]


log = get_logger(__name__)

#: Фраза, с которой Джарвис сообщает о падении внешних моделей.
_OFFLINE_FALLBACK = (
    "Сэр, внешние модели сейчас недоступны. Отвечаю в меру своих локальных "
    "возможностей, но могу быть неполон."
)


class CouncilRouter:
    """Диспетчер «совета мудрецов».

    Делегирует выбор тира единому ``ModelRouter``, оставляя за собой
    генерацию ответа выбранным бэкендом (P5 §5.7).
    """

    def __init__(self, settings: Settings, model_router: Optional[ModelRouter] = None,
                 brain_fabric: Any = None) -> None:
        """
        Args:
            settings: конфигурация проекта.
            model_router: явный экземпляр ModelRouter (чтобы НЕ создавать
                второй независимый роутер — оба пути делят один и тот же).
                Если не передан — создаётся локальный (best-effort).
        """
        self._settings = settings
        self._model_router = model_router if model_router is not None else ModelRouter(settings)
        self._brain_fabric = brain_fabric
        self._local_face: Optional[LocalFace] = None
        self._local_backend: Optional[LLMBackend] = None

    # ------------------------------------------------------------------ #
    #  Ленивая инициализация локальной модели
    # ------------------------------------------------------------------ #

    def _get_local_backend(self) -> LLMBackend:
        """Возвращает (и кэширует) локальный бэкенд FAST-тира."""
        if self._local_backend is None:
            self._local_backend = get_llm_backend(self._settings, Tier.FAST)
        return self._local_backend

    def _get_local_face(self) -> LocalFace:
        """Возвращает (и кэширует) «лицо» Джарвиса поверх локальной модели."""
        if self._local_face is None:
            self._local_face = LocalFace(self._get_local_backend(), self._settings)
        return self._local_face

    # ------------------------------------------------------------------ #
    #  Основной маршрут
    # ------------------------------------------------------------------ #

    def route(self, state: JarvisState) -> JarvisState:
        """Обрабатывает один запрос и дописывает поля состояния.

        Args:
            state: состояние витка (минимум должен быть ``user_input``).

        Returns:
            Тот же объект ``state`` с обновлёнными полями ``intent``,
            ``tier``, ``response``, ``error`` (при неудаче).
        """
        user_input = (state.get("user_input") or "").strip()
        if not user_input:
            state["error"] = "Пустой ввод пользователя"
            state["response"] = "Сэр, я не расслышал команду. Повторите, пожалуйста."
            return state

        started = time.perf_counter()
        state.setdefault("latency", {})

        try:
            # 1) Категория намерения (быстро, офлайн).
            t0 = time.perf_counter()
            intent = resolve_keyword_tool(user_input, user_input)
            state["intent"] = intent
            state["latency"]["intent"] = round(time.perf_counter() - t0, 4)
            log.info("Намерение: '%s' | запрос: %r", intent, user_input[:80])

            # 2) ЕДИНЫЙ выбор тира — делегируем ModelRouter (P5 §5.7).
            t1 = time.perf_counter()
            decision = self._model_router.route(user_input)
            state["latency"]["route"] = round(time.perf_counter() - t1, 4)
            log.info(
                "Роутинг (ModelRouter): tier=%s | %s",
                decision.tier.value, decision.reason,
            )

            response = self._generate(state, decision)
            state["response"] = response
            state["error"] = None

        except (BackendUnavailable, BackendConfigError) as exc:
            # Неожиданная недоступность на этапе генерации.
            log.error("Сбой совета мудрецов: %s", exc)
            state["error"] = str(exc)
            state["response"] = _OFFLINE_FALLBACK
            try:
                local = self._get_local_backend()
                state["tier"] = "fast"
                state["response"] = _OFFLINE_FALLBACK + "\n\n" + local.direct(
                    f"Кратко, по-русски, без извинений ответь на вопрос: {user_input}"
                )
            except (BackendUnavailable, BackendConfigError) as inner:
                log.error("Даже локальный fallback не сработал: %s", inner)
                state["tier"] = "fast"
        except Exception as exc:  # noqa: BLE001 — верхний уровень маршрутизатора
            log.exception("Непредвиденная ошибка совета мудрецов: %s", exc)
            state["error"] = f"internal: {exc}"
            state["response"] = (
                "Сэр, произошла внутренняя ошибка при обработке запроса. "
                "Детали в журнале."
            )

        state["latency"]["total"] = round(time.perf_counter() - started, 4)
        log.info(
            "Виток завершён: tier=%s | время=%.2f с",
            state.get("tier"), state["latency"]["total"],
        )
        return state

    # ------------------------------------------------------------------ #
    #  Генерация ответа выбранным тиром
    # ------------------------------------------------------------------ #

    def _generate(self, state: JarvisState, decision: Any) -> str:
        """Генерирует ответ через выбранный тир (с graceful fallback)."""
        tier = decision.tier if hasattr(decision, "tier") else decision
        state["tier"] = tier.value
        try:
            if (self._brain_fabric is not None
                    and getattr(decision, "brain_route", None) is not None):
                from core.brain import BrainFabricBackend, BrainRequest, BrainRole, PrivacyClass
                template = BrainRequest(
                    user_request=str(state.get("user_input", "")),
                    role=BrainRole(decision.role),
                    privacy=(PrivacyClass.LOCAL_ONLY if decision.forced_local
                             else PrivacyClass.PERSONAL),
                    context_tokens=decision.complexity.context_tokens,
                )
                backend = BrainFabricBackend(
                    self._brain_fabric, decision.brain_route, template=template,
                )
                state["brain_provider"] = decision.provider
                state["brain_model"] = decision.model
                state["brain_reason_code"] = decision.reason_code
            else:
                backend = get_llm_backend(self._settings, tier)
            log.info("Отвечает тир '%s' (%s)", tier.value,
                     "local" if str(getattr(decision, "provider", "")).casefold() == "local" else "remote")
            system = _build_system_prompt(state, self._settings)
            messages = _state_to_messages(state)
            return backend.chat(messages, system=system)
        except (BackendUnavailable, BackendConfigError) as exc:
            log.warning("Тир '%s' недоступен (%s), деградация до локальной FAST", tier.value, exc)
            return self._degrade_to_local(state)

    def _degrade_to_local(self, state: JarvisState) -> str:
        """Последняя линия обороны: отвечаем локальной моделью."""
        face = self._get_local_face()
        state["tier"] = "fast"
        log.info("Деградация: отвечает локальная модель (FAST)")
        system = _build_system_prompt(state, self._settings)
        messages = _state_to_messages(state)
        local_response = face.respond(system, messages)
        return f"{_OFFLINE_FALLBACK}\n\n{local_response}"


# --------------------------------------------------------------------------- #
#  Вспомогательные функции модуля
# --------------------------------------------------------------------------- #


def _state_to_messages(state: JarvisState) -> List[Message]:
    """Собирает историю сообщений для LLM из краткой памяти состояния.

    Если в краткой памяти пусто — добавляем текущий запрос пользователя.
    """
    messages = list(state.get("short_memory") or [])
    if not messages and state.get("user_input"):
        messages = [{"role": "user", "content": state["user_input"]}]
    return messages


def _build_system_prompt(state: JarvisState, settings: Settings) -> str:
    """Системный промпт для генерации ответа (единый стиль для ВСЕХ запросов)."""
    persona_name = settings.persona.name
    address = settings.persona.address
    context = state.get("retrieved_context") or {}
    parts = [
        f"Ты — {persona_name}, персональная операционная система и ближайший "
        f"помощник пользователя по имени {address}.",
        "Стиль общения: уверенный, лаконичный, по делу. Обращайся к "
        f"пользователю как '{address}'.",
        "Правила ответа:\n"
        "- Отвечай на том языке, на котором обратился пользователь (русский — "
        "по-русски, английский — по-английски).\n"
        "- Будь конкретен. Без лишних вступлений типа 'Как языковая модель...'.\n"
        "- Если задача требует действия на компьютере — кратко скажи, что "
        "сделаешь, и сделай.\n"
        "- Если не знаешь — честно скажи, но предложи путь решения.\n"
        "- НЕ упоминай свою внутреннюю архитектуру, модели, тиры и роутинг.",
    ]
    persona_text = (context.get("persona") or "").strip()
    if persona_text:
        parts.append(persona_text)
    profile_text = (context.get("profile") or "").strip()
    if profile_text:
        parts.append(f"Профиль пользователя:\n{profile_text}")
    time_text = (context.get("time_context") or "").strip()
    if time_text:
        parts.append(time_text)
    return "\n\n".join(parts)
