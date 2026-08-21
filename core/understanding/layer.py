"""Understanding Layer — Tier-0 классификатор (regex, ~5 мс, офлайн).

Единственная точка маршрутизации пользовательского ввода. Порядок
проверок имеет значение: более специфичные маршруты оцениваются раньше,
чем общие («сделай презентацию» — mission, хотя «сделай» — глагол действия;
«слышишь меня, открой браузер» — action, а не рефлекс на обращение).

ВНИМАНИЕ (кириллица): ``\\b`` в Python-regex не считает кириллические
границы слов — ``\\b(презентаци)\\b`` не матчит «презентацию». Поэтому все
маркеры собираются БЕЗ ``\\b``; вместо этого корни слов режутся до устойчивой
основы («презентаци», «доклад») и матчатся как подстроки. Обратная сторона —
ложные срабатывания на редких омонимах; их разруливает порядок проверок и
confidence, а в Фазе 2 — Tier-1 LLM-классификатор для спорных случаев.
"""

from __future__ import annotations

import re
from typing import Optional

from core.router.intent_router import (
    INTENT_APP,
    INTENT_BROWSER,
    INTENT_FILE,
    INTENT_MEDIA,
    INTENT_NONE,
    INTENT_SYSTEM,
    INTENT_WEB,
    resolve_keyword_tool,
    split_compound_commands,
)
from core.understanding.models import Route, Understanding

__all__ = ["UnderstandingLayer"]

_INTENT_BY_ROUTE = {Route.REFLEX: "dialog", Route.QUICK_ANSWER: INTENT_WEB}

# --- Маркеры маршрутов (подстроки, без \b — см. docstring модуля) ----------

#: Рефлексы: приветствия, здоровье, время. Проверяются ПЕРВЫМИ, но только
#: если ввод короткий и не содержит глагола действия — иначе «слышишь меня,
#: открой браузер» уехал бы в reflex (баг A2).
_REFLEX_MARKERS = re.compile(
    r"(привет|здравствуй|добрый\s+(день|вечер|утро)|как\s+дела|как\s+ты|"
    r"как\s+жизнь|который\s+час|сколько\s+времени|какое\s+сегодня\s+число|"
    r"какой\s+сегодня\s+день|спасибо|благодарю|повтори)",
    re.IGNORECASE,
)

#: Голосовое обращение-проверка связи («слышишь меня», «ты тут»). Само по
#: себе — reflex, но в составе команды лишь префикс: срезается перед
#: дальнейшей маршрутизацией.
_ADDRESS_MARKERS = re.compile(
    r"(слышишь\s+меня|ты\s+меня\s+слыш|ты\s+тут|ты\s+здесь|джарвис|jarvis|эй[,\s]+джарвис)",
    re.IGNORECASE,
)

#: Вопрос о мире/знаниях → quick_answer. Включает «объясни/расскажи» и
#: математику «объясни как» — по контракту quick-answer путь обязан брать
#: любой вопрос, НЕ уходя в mission.
_QUESTION_MARKERS = re.compile(
    r"(что\s+такое|почему|зачем|как\s+(найти|решить|сделать|работает|устроен|"
    r"посчитать|вычислить)|сколько\s+(будет|стоит|весит)|кто\s+такой|"
    r"кто\s+такая|чем\b.{0,40}?отлича\w*|в\s+чём\s+разница|в\s+чем\s+разница|"
    r"объясни|расскажи\s+(про|о|об)|помоги\s+решить|реши\s+задачу|"
    r"what\s+is|why\s+|how\s+to|who\s+is)",
    re.IGNORECASE,
)

#: Многошаговые артефакты → mission. Проверяются РАНЬШЕ глаголов действия:
#: «сделай презентацию» — миссия, а не один инструмент.
_MISSION_MARKERS = re.compile(
    r"(презентаци|слайд|доклад|отч[её]т|реферат|исследовани|анализ\s+рынка|"
    r"собери\s+(информаци|материал|данные)|подготовь\s+(доклад|отч[её]т|"
    r"презентаци|материал)|напиши\s+(статью|эссе|книгу|курсов)|"
    r"presentation|slides|report|research)",
    re.IGNORECASE,
)

#: Глаголы действия → action (1-3 инструмента синхронно). «сделай/напиши»
#: намеренно общие — специфичные миссии уже отобраны выше.
_ACTION_VERBS = re.compile(
    r"(открой|запусти|закрой|сверни|разверни|набери|напечатай|введи|создай|"
    r"удали|переименуй|скопируй|перемести|сохрани|поставь|включи|выключи|"
    r"проиграй|перейди|найди\s+и\s+открой|загугли|сделай|напиши|"
    r"open|launch|close|create|delete|rename|play)",
    re.IGNORECASE,
)

#: Приватность: такое не уходит в облачную модель (Фаза 2, Hybrid Council).
_PRIVACY_MARKERS = re.compile(
    r"(парол|паспорт|карта\s+\d|номер\s+карты|снилс|инн\b|секрет|приватн|"
    r"личн(ое|ый|ая)|password|passwd|secret)",
    re.IGNORECASE,
)

#: Длина, после которой «рефлексные» маркеры перестают быть рефлексом:
#: «привет, а теперь собери отчёт на 40 страниц» — не приветствие.
_REFLEX_MAX_WORDS = 6


def _normalize(text: str) -> str:
    # Регистр + схлопывание пробелов; U+00A0/U+202F и прочие юникод-пробелы
    # (их выдают STT и «неразрывный пробел» с клавиатуры) — в обычный пробел,
    # иначе «чем\s+отличается» не сматчится на «чем\u00A0отличается».
    return " ".join((text or "").casefold().replace(" ", " ").replace(" ", " ").split())


def _strip_address_prefix(text: str) -> str:
    """Убирает префикс-обращение («слышишь меня, открой браузер» → «открой браузер»)."""
    match = _ADDRESS_MARKERS.match(text)
    if match:
        rest = text[match.end():].lstrip(" ,.—-")
        if rest:
            return rest
    return text


class UnderstandingLayer:
    """Единый классификатор ввода. Tier-0: regex. Никогда не молчит.

    Tier-1 (LLM, ~200-400 мс через Flash Lite при confidence < 0.7)
    подключается в Фазе 2 — интерфейс ``understand()`` меняться не будет.
    """

    def understand(self, text: str, *, channel: str = "text") -> Understanding:
        """Классифицирует ввод и возвращает маршрут с обоснованием.

        На любой ввод — валидный ``Understanding`` (пустой/мусор → clarify).
        Исключений не бросает.
        """
        try:
            return self._classify(text)
        except Exception as exc:  # последний рубеж: лучше clarify, чем молчание
            return Understanding(
                route=Route.CLARIFY,
                confidence=0.0,
                source="fallback",
                reason=f"classifier error: {exc!r}",
            )

    # ------------------------------------------------------------------
    def _classify(self, text: str) -> Understanding:
        raw = _normalize(text)
        if not raw:
            return Understanding(
                route=Route.CLARIFY, confidence=1.0,
                reason="пустой ввод",
            )

        privacy = bool(_PRIVACY_MARKERS.search(raw))

        # 0. Составная команда: «сделай X и потом Y» — каждый фрагмент
        #    маршрутизируется отдельно (фикс A3: раньше вторая половина
        #    терялась).
        parts = split_compound_commands(raw)
        compound: list = list(parts) if parts else []

        # 1. Рефлекс — только для коротких реплик без глагола действия.
        words = raw.split()
        if len(words) <= _REFLEX_MAX_WORDS and _REFLEX_MARKERS.search(raw) \
                and not _ACTION_VERBS.search(raw):
            return Understanding(
                route=Route.REFLEX, intent="dialog", confidence=0.95,
                privacy=privacy, reason="реплика-рефлекс (приветствие/время)",
            )
        # Чистое обращение («слышишь меня?», «джарвис») — тоже рефлекс.
        if len(words) <= 4 and _ADDRESS_MARKERS.search(raw) \
                and not _ACTION_VERBS.search(raw) and not _QUESTION_MARKERS.search(raw):
            return Understanding(
                route=Route.REFLEX, intent="dialog", confidence=0.9,
                privacy=privacy, reason="обращение-проверка связи",
            )

        # 2. Срезаем префикс-обращение и работаем с командой.
        body = _strip_address_prefix(raw)

        # 3. Mission РАНЬШЕ action: «сделай презентацию» — миссия, хотя
        #    «сделай» — глагол действия (порядок — фикс прогона Фазы 1).
        if _MISSION_MARKERS.search(body):
            return Understanding(
                route=Route.MISSION, intent=INTENT_WEB, confidence=0.85,
                compound=compound, privacy=privacy,
                reason="многошаговый артефакт (презентация/отчёт/исследование)",
            )

        # 4. Вопрос о знаниях → quick_answer. Запрет уходить в mission.
        if _QUESTION_MARKERS.search(body):
            return Understanding(
                route=Route.QUICK_ANSWER, intent=INTENT_WEB, confidence=0.85,
                privacy=privacy, reason="вопрос о мире/знаниях",
            )

        # 5. Явный глагол действия.
        if _ACTION_VERBS.search(body):
            if compound:
                parts_intents = [resolve_keyword_tool(p, p) for p in compound]
                intent = next((i for i in parts_intents if i != INTENT_NONE), INTENT_APP)
                confidence = 0.85
            else:
                intent = resolve_keyword_tool(body, body)
                confidence = 0.85 if intent != INTENT_NONE else 0.6
                if intent == INTENT_NONE:
                    intent = INTENT_APP
            return Understanding(
                route=Route.ACTION, intent=intent, confidence=confidence,
                compound=compound, privacy=privacy,
                reason="глагол действия + объект",
            )

        # 6. Keyword-роутер без глагола («блокнот», «музыку погромче»).
        intent = resolve_keyword_tool(body, body)
        if intent != INTENT_NONE:
            return Understanding(
                route=Route.ACTION, intent=intent, confidence=0.7,
                compound=compound, privacy=privacy,
                reason="keyword-интент без явного глагола",
            )

        # 7. Ничего не подошло: вопросительный знак → quick_answer с низкой
        #    уверенностью (Tier-1 уточнит в Фазе 2), иначе — clarify.
        if "?" in raw:
            return Understanding(
                route=Route.QUICK_ANSWER, intent=INTENT_WEB, confidence=0.55,
                privacy=privacy, reason="вопрос по форме, без маркеров",
            )
        return Understanding(
            route=Route.CLARIFY, confidence=0.3, privacy=privacy,
            reason="маршрут неясен — нужен живой уточняющий вопрос",
        )
