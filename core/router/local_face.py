"""«Лицо» Джарвиса — локальная Qwen 4B как первичный классификатор.

Локальная модель всегда под рукой и отвечает за две вещи:
    1. ``respond``   — сгенерировать обычный ответ пользователю;
    2. ``classify``  — решить, может ли она ответить сама (``scope="self"``)
       или запрос надо отдать более сильной модели (``scope="escalate"``).

Классификация дешёвая и офлайн: модель просят вернуть строго JSON.
Если JSON не распарсился — безопасный fallback: эскалировать к аналитику.

Модуль НЕ зависит от config на верхнем уровне проблемно — но здесь это
безопасно, потому что ``config`` сам не импортирует ``core`` на верхнем
уровне (только лениво внутри методов). Импорт ``Settings`` используется
только для аннотации типа и чтения бюджета задержки.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional

from config.settings import Settings
from core.llm import BackendConfigError, BackendUnavailable, LLMBackend, Tier
from core.state import Message
from core.utils.logger import get_logger

__all__ = ["LocalFace", "ClassifyDecision"]

log = get_logger(__name__)

#: Системный промпт для задачи классификации.
#
# ВАЖНО (философия latency, ТЗ §4): локальная Qwen 4B — это "самая быстрая
# доступная модель для обычных задач", а НЕ "модель, обязанная уложиться в
# N секунд". Поэтому классификатор НЕ должен эскалировать только потому, что
# запрос кажется "непростым" или модели нужно подумать. Эскалация оправдана
# ЛИШЬ когда задача объективно требует capability, которой fast tier не
# обладает (написание/отладка кода, архитектурное ревью, тяжёлый анализ
# объёмных данных). В сомнительных случаях НЕ эскалируем — fast tier
# справляется с большинством обычных запросов (приветствия, вопросы,
# короткие объяснения, управление системой).
_CLASSIFY_SYSTEM_PROMPT = (
    "Ты — диспетчер запросов цифрового разума АТЛАС. Реши, может ли локальная "
    "модель Qwen 4B (быстрая, локальная) ответить сама, или запрос объективно "
    "требует более мощной модели.\n"
    "Верни СТРОГО ОДИН JSON-объект без пояснений и без markdown-разметки:\n"
    '{"scope": "self" | "escalate", '
    '"tier": "analyst" | "coder" | "architect" | null, '
    '"reason": "кратко по-русски"}\n'
    "Правила:\n"
    '- scope="self" — ПО УМОЛЧАНИЮ. Приветствия, прощания, простые бытовые '
    "команды, факты из памяти, короткие ответы, обычные вопросы и объяснения, "
    "управление системой/приложениями, а также всё, что Qwen 4B решит уверенно. "
    "Не эскалируй только потому, что запрос длинный или требует рассуждения — "
    "локальная модель справляется с обычными задачами.\n"
    '- scope="escalate" и tier="analyst" — ТОЛЬКО если задача объективно '
    "требует глубокого анализа больших объёмов данных, сравнения множества "
    "источников или серьёзного рассуждения, которое fast tier не потянет.\n"
    '- tier="coder" — написание, отладка или рефакторинг кода, скриптов, '
    "фронтенда (это требует отдельной код-модели).\n"
    '- tier="architect" — архитектура систем, сложные многошаговые задачи, '
    "ревью.\n"
    'Если сомневаешься — выбирай "self".'
)

#: Регулярка для извлечения первого JSON-объекта из произвольного текста.
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class ClassifyDecision(Dict[str, Any]):
    """Результат классификации (dict с гарантированными ключами)."""

    @property
    def scope(self) -> str:
        return str(self.get("scope", "escalate"))

    @property
    def tier(self) -> Optional[str]:
        value = self.get("tier")
        if value in (None, "null", "none", ""):
            return None
        return str(value)

    @property
    def reason(self) -> str:
        return str(self.get("reason", ""))


class LocalFace:
    """Обёртка над локальной моделью (лицо Джарвиса)."""

    def __init__(self, backend: LLMBackend, settings: Settings) -> None:
        """
        Args:
            backend: локальный LLM-бэкенд (обычно ``get_llm_backend(settings, Tier.FAST)``).
            settings: конфигурация (для чтения soft-цели задержки телеметрии).
        """
        self._backend = backend
        self._settings = settings
        # SOFT PERFORMANCE TARGET / TELEMETRY ONLY (ТЗ §4).
        # Это НЕ hard-timeout и НЕ условие эскалации. Превышение этого
        # значения никогда не влияет на выбор тира или на то, справилась ли
        # модель. Используется исключительно для логов/метрик.
        self._latency_target = float(settings.limits.local_latency_target_sec)

    # ------------------------------------------------------------------ #
    #  Генерация ответа
    # ------------------------------------------------------------------ #

    def respond(self, system: str, messages: List[Message]) -> str:
        """Генерирует ответ пользователю через локальную модель.

        Просто проксирует вызов в ``backend.chat()``. Исключения
        (``BackendUnavailable`` при отсутствии GGUF, ``BackendConfigError``)
        пробрасываются наверх — их ловит ``CouncilRouter``.

        Args:
            system: системный промпт (persona + контекст памяти).
            messages: история диалога (включая текущий запрос пользователя).

        Returns:
            Текст ответа.
        """
        return self._backend.chat(messages, system=system)

    # ------------------------------------------------------------------ #
    #  Классификация: self или escalate
    # ------------------------------------------------------------------ #

    def classify(self, system: str, user_input: str, intent: str) -> ClassifyDecision:
        """Решает, отвечает ли локальная модель сама или эскалирует.

        Алгоритм:
            1. Быстрый shortcut по ``intent``: ``app`` / ``media`` / ``system`` —
               почти всегда простые команды, отвечает локальная модель.
            2. ``none`` / ``web`` / ``browser`` / ``file`` — по умолчанию тоже
               отвечает локальная модель (self), потому что большинство таких
               запросов (приветствие, обычный вопрос, короткий запрос) fast tier
               решает уверенно. Модель-классификатор спрашивается ТОЛЬКО когда
               нужно отличить задачу, объективно требующую другого тира
               (код/архитектура/тяжёлый анализ).
            3. При любой ошибке разбора JSON — безопасный fallback:
               ``self`` (локальная модель), НЕ эскалация. Локальная Qwen 4B
               справляется с обычными запросами; эскалация только при
               осмысленной причине, а НЕ из-за сомнения/латентности.

        Замеряет время работы и логирует INFO/WARNING только как телеметрию
        (параметр ``settings.limits.local_latency_target_sec``). Превышение
        цели НИКОГДА не меняет решение об эскалации — latency != capability.

        Args:
            system: системный промпт для классификации.
            user_input: текст пользователя.
            intent: категория от :func:`resolve_keyword_tool`.

        Returns:
            :class:`ClassifyDecision` с ключами ``scope`` / ``tier`` / ``reason``.
        """
        # 1) Быстрый shortcut для локальных запросов.
        #    intent "none" (общие вопросы/приветствия/болтовня) и простые
        #    команды (app/media/system) отвечает локальная Qwen 4B сама —
        #    отдельный вызов классификатора НЕ нужен (это был бы второй лишний
        #    проход LLM, +~5 с задержки). Эскалация для "none" всё равно
        #    возможна позже, если сам ответ покажет нужду во внешней модели.
        if intent in (INTENT_LOCAL_DEFAULT := ("app", "media", "system", "none")):
            return ClassifyDecision({
                "scope": "self",
                "tier": None,
                "reason": f"локальный запрос категории '{intent}', отвечает локальная модель",
            })

        # 2) Для web / browser / file — локальная модель тоже ПЕРВИЧНЫЙ
        #    ответчик, но классификатор может поднять запрос к
        #    analyst/coder/архитектору, если задача объективно требует
        #    другой capability. Эскалация — только при явном указании модели,
        #    НЕ из-за сомнения/латентности (ТЗ §4).
        #    Классификатор ДЁШЕВ: ~24 токена, temperature=0.
        user_message = (
            f"Категория запроса: {intent}\n"
            f"Текст пользователя: {user_input}\n"
            "Верни только JSON."
        )
        started = time.perf_counter()
        try:
            raw = self._backend.chat(
                [{"role": "user", "content": user_message}],
                system=system,
                max_tokens=24,
                temperature=0.0,
            )
        except (BackendUnavailable, BackendConfigError) as exc:
            # Локальная модель недоступна — не можем классифицировать,
            # безопасно уходим на эскалацию (внешнюю, если доступна).
            log.error("Классификация не удалась (локальная модель недоступна): %s", exc)
            return ClassifyDecision({
                "scope": "escalate",
                "tier": "analyst",
                "reason": "локальная модель недоступна, пробуем внешнюю",
            })

        elapsed = time.perf_counter() - started
        # TELEMETRY ONLY (ТЗ §4): замер задержки classify() — чисто
        # наблюдательная метрика, НЕ условие роутинга/эскалации.
        # Медленный ответ != «модель не справилась». Результат замера
        # НИКОГДА не попадает в scope/tier. Цель
        # settings.limits.local_latency_target_sec используется только
        # для формирования строки лога (информативно, без ветвления).
        log.info(
            "classify latency: %.2f s (цель %.2f s — телеметрия, не влияет на роутинг)",
            elapsed, self._latency_target,
        )

        decision = _parse_classify_json(raw)
        if decision is None:
            # Не удалось распарсить — отвечает локальная модель (self),
            # НЕ эскалация. Локальная Qwen 4B справляется с обычным запросом;
            # эскалируем только при явной, осмысленной причине.
            log.warning("Не удалось распарсить JSON классификации, безопасный fallback -> self (локальная модель)")
            return ClassifyDecision({
                "scope": "self",
                "tier": None,
                "reason": "ответ классификатора не распознан, отвечает локальная модель",
            })

        # Нормализуем/валидируем поля. Явное "escalate" только при прямом
        # указании; всё остальное (в т.ч. пустота/self) — локальная модель.
        scope = "escalate" if decision.get("scope") == "escalate" else "self"
        tier = decision.get("tier")
        if tier in (None, "null", "none", ""):
            tier = None if scope == "self" else "analyst"
        reason = str(decision.get("reason", ""))
        return ClassifyDecision({"scope": scope, "tier": tier, "reason": reason})


def _parse_classify_json(text: str) -> Optional[Dict[str, Any]]:
    """Извлекает и парсит JSON-объект из ответа модели.

    Модель может обернуть JSON в markdown-забор (```json ... ```) или добавить
    пояснения вокруг. Ищем первый фигурный объект и пробуем ``json.loads``.

    Returns:
        Словарь при успехе, иначе ``None``.
    """
    if not text:
        return None
    cleaned = text.strip()
    # Снимаем markdown-забор, если есть.
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()
    match = _JSON_RE.search(cleaned)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data
