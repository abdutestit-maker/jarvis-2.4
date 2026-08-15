"""Совет мудрецов — оркестратор выбора и вызова моделей.

``CouncilRouter.route(state)`` — единая точка входа для одного витка
обработки запроса пользователя:

    1. keyword-роутер определяет категорию намерения (мгновенно, офлайн);
    2. «лицо» (локальная Qwen 4B) решает: ответить самой (``self``) или
       эскалировать (``escalate``) к более сильной модели;
    3. при ``self`` — генерируем ответ локально;
    4. при ``escalate`` — ищем первый доступный тир выше запрошенного и
       зовём его; при сбое (нет ключа / сеть / лимит) шаг за шагом
       поднимаемся выше, а если доступных моделей нет вообще — деградируем
       до локальной с честным сообщением.

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
    resolve_tier,
    Tier,
)
from core.router.intent_router import resolve_keyword_tool
from core.router.local_face import LocalFace
from core.router.tier_resolver import resolve_next_available_tier
from core.state import JarvisState, Message
from core.utils.logger import get_logger

__all__ = ["CouncilRouter"]


def _find_heavier_available_tier(settings: Settings, current: Tier) -> Optional[Tier]:
    """Первый доступный тир СТРОГО выше ``current`` по цепочке эскалации.

    Возвращает ``None``, если выше ``current`` нет ни одного доступного тира.
    """
    resolved = resolve_tier(current)
    try:
        start_index = ESCALATION_ORDER.index(resolved)
    except ValueError:
        start_index = 0
    for tier in ESCALATION_ORDER[start_index + 1:]:
        if settings.is_tier_available(tier):
            return tier
    return None


log = get_logger(__name__)

#: Фраза, с которой Джарвис сообщает о падении внешних моделей.
_OFFLINE_FALLBACK = (
    "Сэр, внешние модели сейчас недоступны. Отвечаю в меру своих локальных "
    "возможностей, но могу быть неполон."
)


class CouncilRouter:
    """Диспетчер «совета мудрецов»."""

    def __init__(self, settings: Settings) -> None:
        """
        Args:
            settings: конфигурация проекта.
        """
        self._settings = settings
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

            # 2) Решение «лица»: self или escalate.
            t1 = time.perf_counter()
            face = self._get_local_face()
            decision = face.classify(_CLASSIFY_SYSTEM, user_input, intent)
            state["latency"]["classify"] = round(time.perf_counter() - t1, 4)
            log.info(
                "Классификация: scope=%s tier=%s | %s",
                decision.scope, decision.tier, decision.reason,
            )

            if decision.scope == "self":
                response = self._handle_self(face, state)
            else:
                response = self._handle_escalate(state, decision.tier, intent)

            state["response"] = response
            state["error"] = None

        except (BackendUnavailable, BackendConfigError) as exc:
            # Неожиданная недоступность на этапе классификации/лица.
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
    #  Ветка «self» — отвечает локальная модель
    # ------------------------------------------------------------------ #

    def _handle_self(self, face: LocalFace, state: JarvisState) -> str:
        """Генерирует ответ локальной моделью.

        Raises:
            BackendUnavailable / BackendConfigError: если локальная модель
                недоступна (например, нет GGUF-файла) — поймёт route().
        """
        self._settings  # используется для построения системного промпта позже
        system = _build_system_prompt(state, self._settings)
        messages = _state_to_messages(state)
        state["tier"] = "fast"
        log.info("Отвечает локальная модель (FAST)")
        return face.respond(system, messages)

    # ------------------------------------------------------------------ #
    #  Ветка «escalate» — идём к более сильной модели
    # ------------------------------------------------------------------ #

    def _handle_escalate(self, state: JarvisState, requested_tier: Optional[str],
                         intent: str) -> str:
        """Эскалирует запрос к более сильной УДАЛЁННОЙ модели (П1 §1.1).

        Локальной тяжёлой модели (7B-coder) БОЛЬШЕ НЕТ в цепочке эскалации —
        решение владельца: J.A.R.V.I.S. не грузит 7B «просто так» на локальном
        железе. Эскалация идёт ТОЛЬКО к удалённым провайдерам (Kimi/DeepSeek/
        Claude). Если удалённый тир недоступен (нет ключа/сети) — честная
        деградация до локальной FAST-модели (Qwen 4B) с сообщением о сбое
        внешних моделей. Никакой загрузки 7B ради «голос добавить».

        Raises:
            BackendConfigError / BackendUnavailable: только если и локальный
                fallback недоступен (поймает route()).
        """
        start = resolve_tier(requested_tier or "analyst")

        # 1) Прямая попытка запрошенного удалённого тира.
        if self._settings.is_tier_available(start):
            return self._call_tier(state, start)

        # 2) Запрошенный тир недоступен. Поднимаемся выше ПО ЦЕПОЧКЕ эскалации,
        #    но ТОЛЬКО к реально доступным (удалённым) тирам. Локальных
        #    тяжёлых моделей в цепочке больше нет (П1 §1.1).
        heavier = _find_heavier_available_tier(self._settings, start)
        if heavier is not None:
            return self._call_tier(state, heavier)

        log.warning(
            "Эскалация '%s' невозможна (нет доступных удалённых тиров выше). "
            "Деградация до локальной FAST.",
            start.value,
        )
        return self._degrade_to_local(state, intent)

    def _call_tier(self, state: JarvisState, tier: Tier) -> str:
        """Вызывает конкретный тир и возвращает ответ (или кидает при сбое)."""
        backend = get_llm_backend(self._settings, tier)
        state["tier"] = tier.value
        log.info("Эскалация -> тир '%s' (%s)", tier.value, backend.name)
        system = _build_system_prompt(state, self._settings)
        messages = _state_to_messages(state)
        return backend.chat(messages, system=system)

    def _degrade_to_local(self, state: JarvisState, intent: str) -> str:
        """Последняя линия обороны: отвечаем локальной моделью.

        Raises:
            BackendUnavailable / BackendConfigError: если и локальная модель
                недоступна (поймает route()).
        """
        face = self._get_local_face()
        state["tier"] = "fast"
        log.info("Деградация: отвечает локальная модель (FAST)")
        try:
            system = _build_system_prompt(state, self._settings)
            messages = _state_to_messages(state)
            local_response = face.respond(system, messages)
            return f"{_OFFLINE_FALLBACK}\n\n{local_response}"
        except (BackendUnavailable, BackendConfigError) as exc:
            log.error("Локальная деградация не удалась: %s", exc)
            raise


# --------------------------------------------------------------------------- #
#  Вспомогательные функции модуля
# --------------------------------------------------------------------------- #

_CLASSIFY_SYSTEM = (
    "Ты — диспетчер запросов ИИ-ассистента Джарвиса. "
    "Верни строго JSON без пояснений."
)


def _state_to_messages(state: JarvisState) -> List[Message]:
    """Собирает историю сообщений для LLM из краткой памяти состояния.

    Если в краткой памяти пусто — добавляем текущий запрос пользователя.
    """
    messages = list(state.get("short_memory") or [])
    if not messages and state.get("user_input"):
        messages = [{"role": "user", "content": state["user_input"]}]
    return messages


def _build_system_prompt(state: JarvisState, settings: Settings) -> str:
    """Системный промпт для генерации ответа (единый стиль для ВСЕХ запросов).

    Не только для приветствий — работает для любого запроса: вопрос,
    объяснение, инструкция, анализ. Задаёт роль, тон и правила ответа, чтобы
    генерация была естественной и в характере J.A.R.V.I.S. (а не
    «Привет, сэр. Готов к действию» на всё подряд).
    """
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
