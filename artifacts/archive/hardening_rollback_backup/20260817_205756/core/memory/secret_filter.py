"""Фильтрация секретов/сырых данных перед записью в память (П1 §1.5, §1.8).

J.A.R.V.I.S. НЕ должен сохранять в долгую память/профиль:
    * сырые ключи/токены/пароли (sk-, pk-, Bearer, api_key=..., password=...);
    * внутренний JSON плана/решения агента;
    * сырые traceback / исключения;
    * служебные маркерки пайплайна.

Это отдельный чистый модуль (без состояния) — покрывается unit-тестом.
Память должна хранить СМЫСЛ диалога, а не лог ошибок и не секреты.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from core.security.redaction import SECRET_VALUE_RE, redact_text

# Сырые ошибки/исключения.
_RE_TRACEBACK = re.compile(
    r"(?i)(traceback\s*\(most\s+recent\s+call\s+last\)|"
    r"\b\w+(error|exception)\b\s*[:\(]|"
    r"line\s+\d+,\s+in\s+\w+|"
    r"raise\s+\w+|"
    r"^\s*File\s+\".*?\",\s*line\s+\d+)"
)
# Внутренний JSON (план/решение агента).
_RE_JSON = re.compile(r"\{[^{}]*\"(tool|arguments|reason|verification|risk)\"[^{}]*\}", re.DOTALL)
# Служебные маркерки пайплайна.
_RE_EVENT = re.compile(r"(?i)\b(event_|mission-|task_id|task_started|confirmation_required)\b")
# Секреты: ключи/токены/пароли (sk-, pk-, Bearer, api_key=...).
# Compatibility alias for older callers; pattern ownership lives in the
# canonical security service.
_RE_SECRET = SECRET_VALUE_RE

__all__ = ["contains_secret_or_raw", "sanitize_for_memory"]


def contains_secret_or_raw(text: str) -> bool:
    """True, если строка содержит секреты/сырые ошибки/JSON/служебное."""
    if not text or not text.strip():
        return False
    for rx in (_RE_SECRET, _RE_JSON, _RE_EVENT, _RE_TRACEBACK):
        if rx.search(text):
            return True
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            json.loads(stripped)
            return True
        except (ValueError, json.JSONDecodeError):
            pass
    return False


def sanitize_for_memory(text: str) -> str:
    """Возвращает текст, очищенный от секретов/сырых данных для записи в память.

    Секретные куски МАСКИРУЮТСЯ (не удаляются целиком, чтобы сохранить
    контекст фразы), сырые маркерки/теги вырезаются. Если вся строка —
    чистый сырой JSON/traceback, возвращается пустая строка (не пишем мусор).
    """
    if not text or not text.strip():
        return ""

    # Если вся строка — сырой JSON/traceback целиком, не сохраняем её.
    if _RE_TRACEBACK.search(text) and not any(c.isalpha() for c in text.replace("traceback", "")):
        return ""
    if _RE_EVENT.search(text) and not _RE_JSON.search(text) and len(text.strip()) < 200:
        # короткая служебная метка — не пишем в память
        if not any(w in text.lower() for w in ("сэр", "jarvis", "готов", "принят")):
            return ""

    # Маскируем секреты: оставляем префикс + звёздочки.
    cleaned = redact_text(text).replace("[redacted]", "***")
    # Вырезаем внутренний JSON плана (но оставляем обычный текст вокруг).
    cleaned = _RE_JSON.sub("[внутренний план]", cleaned)
    # Вырезаем служебные маркерки.
    cleaned = _RE_EVENT.sub("", cleaned)
    # Убираем сырые traceback-фрагменты.
    cleaned = _RE_TRACEBACK.sub("", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned


def is_safe_to_store(text: str) -> bool:
    """True, если текст можно сохранять в память как есть (без маскировки)."""
    return not contains_secret_or_raw(text)
