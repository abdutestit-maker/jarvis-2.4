"""Автоизвлечение ключевых фактов о пользователе (Sprint 4, STEP 2.2).

Детектор работает ОФЛАЙН (регулярки, без LLM) и ловит только ЯВНЫЕ
самопрезентации — «меня зовут X», «я люблю X», «зови меня X». Всё
сомнительное игнорируется: лучше не знать факта, чем записать ложный.

Найденное пишется в существующий JSON-профиль (``core.memory.profile``),
с дедупликацией. Никакой vector DB ради двадцати фактов — по спринту.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from config.settings import Settings
from core.memory.profile import load_profile, save_profile
from core.utils.logger import get_logger

__all__ = ["extract_facts", "learn_facts", "detect_tone"]

log = get_logger(__name__)


# --------------------------------------------------------------------------- #
#  Извлечение фактов
# --------------------------------------------------------------------------- #

#: Явные паттерны самопрезентации. Группы в скобках — значение факта.
_NAME_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(?:меня зовут|моё имя|мое имя|зови меня|i am|i'm|my name is)\s+([A-ZА-ЯЁ][\w-]{0,30})", re.IGNORECASE),
    re.compile(r"\b(?:я)\s+—\s+([A-ZА-ЯЁ][\w-]{0,30})\s*[.!]?", re.IGNORECASE),
]
_LIKE_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(?:я люблю|я обожаю|мне нравится|i love|i like)\s+([^,.!?;]{2,60})", re.IGNORECASE),
]
_DISLIKE_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(?:я не люблю|я ненавижу|терпеть не могу|i hate)\s+([^,.!?;]{2,60})", re.IGNORECASE),
]

#: Слова, которые точно НЕ являются именами/фактами (служебные/мусор).
_NOT_A_NAME = {
    "просто", "очень", "уже", "тут", "здесь", "такой", "такая", "твой",
    "твоя", "мой", "моя", "он", "она", "они", "мы", "вы", "ты", "я",
    "хочу", "могу", "буду", "делаю", "пишу", "думаю", "спрашиваю",
}


def _clean_value(raw: str) -> str:
    """Нормализует вытащенное значение: пробелы, регистр, мусор."""
    value = (raw or "").strip().strip("\"'“”‘’(),.")
    value = re.sub(r"\s+", " ", value)
    return value


def _match_first(text: str, patterns: List[re.Pattern]) -> Optional[str]:
    for pattern in patterns:
        m = pattern.search(text)
        if not m:
            continue
        value = _clean_value(m.group(1))
        if not value or len(value) < 2:
            continue
        if value.lower() in _NOT_A_NAME:
            continue
        return value
    return None


def extract_facts(text: str) -> Dict[str, Optional[str]]:
    """Достаёт явные факты из реплики пользователя (офлайн).

    Returns:
        Словарь с ключами ``name`` / ``like`` / ``dislike``; значение
        ``None`` = факт не найден. Ложноположительные паттерны («я люблю
        погулять» — тоже факт, ок; «я» без продолжения — нет).
    """
    text = (text or "").strip()
    if not text:
        return {"name": None, "like": None, "dislike": None}
    return {
        "name": _match_first(text, _NAME_PATTERNS),
        "like": _match_first(text, _LIKE_PATTERNS),
        "dislike": _match_first(text, _DISLIKE_PATTERNS),
    }


def learn_facts(settings: Settings, text: str) -> List[Tuple[str, str]]:
    """Извлекает факты из ``text`` и дописывает их в профиль (с дедупом).

    Returns:
        Список фактически добавленных пар ``(поле, значение)``.
    """
    facts = extract_facts(text)
    added: List[Tuple[str, str]] = []
    try:
        profile = load_profile(settings)
    except Exception as exc:  # noqa: BLE001
        log.debug("Профиль недоступен, факты не записаны: %s", exc)
        return added

    changed = False

    name = facts.get("name")
    if name and not (profile.get("name") or "").strip():
        profile["name"] = name
        changed = True
        added.append(("name", name))

    like = facts.get("like")
    if like:
        likes = [str(x).strip().lower() for x in (profile.get("interests") or [])]
        if like.lower() not in likes:
            profile.setdefault("interests", []).append(like)
            changed = True
            added.append(("interests", like))

    dislike = facts.get("dislike")
    if dislike:
        current = [str(x).strip().lower() for x in (profile.get("dislikes") or [])]
        if dislike.lower() not in current:
            profile.setdefault("dislikes", []).append(dislike)
            changed = True
            added.append(("dislikes", dislike))

    if changed:
        try:
            save_profile(settings, profile)
            log.info("Из разговора извлечены факты: %s", added)
        except Exception as exc:  # noqa: BLE001
            log.warning("Не удалось сохранить факты в профиль: %s", exc)
    return added


# --------------------------------------------------------------------------- #
#  Динамическая адаптация тона (Sprint 4, STEP 3.3)
# --------------------------------------------------------------------------- #

_CASUAL_RE = re.compile(
    r"(хаха|ахах|лол(ик)?|кек|:d|xd|прикольно|красава|краш|топчик|ржу|смеюсь|"
    r"гифк[иу]|мем|шутк|прикол)", re.IGNORECASE)
_SERIOUS_RE = re.compile(
    r"(срочно|важно|не работает|ошибка|баг|падает|critical|работа|дедлайн|"
    r"проблема|сломал|нужно срочно|помоги разобраться|urgent|error|exception)",
    re.IGNORECASE)


def detect_tone(last_user_text: str) -> str:
    """Лёгкая оценка настроения последней реплики: casual/serious/default.

    Тон НЕ меняет персону кардинально — только подсказка модели, где
    уместен юмор, а где лучше собраться (Sprint 4 STEP 3.3).
    """
    text = (last_user_text or "").strip()
    if not text:
        return "default"
    if _CASUAL_RE.search(text):
        return "casual"
    if _SERIOUS_RE.search(text):
        return "serious"
    return "default"
