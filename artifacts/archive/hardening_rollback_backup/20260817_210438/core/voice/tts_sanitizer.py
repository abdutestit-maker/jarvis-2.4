"""TTS-санитайзер — фильтрует сырые ошибки/JSON перед озвучкой (П1 §1.2).

J.A.R.V.I.S. НЕ должен читать вслух:
    * сырые traceback / исключения («TypeError: ...»);
    * внутренний JSON плана/решения («{"tool": "write_file", ...}»);
    * служебные маркерки пайплайна («EVENT_...», «[mission-...]»);
    * ключи/токены/пароли;
    * незаконченные обрывки мысли.

Это отдельный чистый модуль (без состояния), чтобы его можно было
покрыть unit-тестом без запуска piper/моделей. Голос должен звучать
как живая сущность, а не как лог ошибок.
"""

from __future__ import annotations

import json
import re
from typing import Optional
from core.security.redaction import SECRET_VALUE_RE

# Сырые ошибки/исключения. Bare ``Error 455`` включён намеренно: раньше
# эта строка проходила фильтр и выбирала английский Piper voice.
_RE_TRACEBACK = re.compile(
    r"(?i)(traceback\s*\(most\s+recent\s+call\s+last\)|"
    r"\b(?:error|exception)\b(?:\s*[:#-]?\s*\d{3})?|"
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
_RE_SECRET = SECRET_VALUE_RE
# Обрывки мысли (многоточие в конце / незакрытая скобка / начало <think>).
_RE_FRAGMENT = re.compile(r"(?i)(^\s*<\s*think\s*>|…\s*$|[\(\[]\s*$|\[\.\.\.\]\s*$)")
# HTTP-коды (401/403/404/429/500/503 и т.п.) и фразы ошибок провайдера/связи.
# Намеренно ЛОВИМ только технические сигналы — живой язык модели (вопросы,
# цифры в ответах) не должен глушиться этим правилом.
_RE_PROVIDER_ERR = re.compile(
    r"(?i)("
    r"http\s*/?\s*\d{3}|"            # "HTTP 401" / "http 429"
    r"verнул\s+http|"               # "вернул HTTP 401"
    r"authentication\s+fails|"       # "Authentication Fails"
    r"unauthor|invalid\s+(api_?key|token|api key)|"  # 401-причины
    r"quota|rate\s*limit|too\s+many\s+requests|"     # 429/квота
    r"service\s+unavailable|bad\s+gateway|gateway\s+timeout|"  # 503/502
    r"не\s+задан\s+endpoint|endpoint\s+провайдера|"  # ошибки конфигурации бэкенда
    r"модель\s+недоступна|провайдер\s+\w+\s+вернул|"  # "Провайдер X вернул HTTP ..."
    r"could\s+not\s+connect|connection\s+(refused|error|reset)|"  # сетевые сбои
    r"timed?\s*out|timeout|время\s+ожидания"          # таймауты
    r")"
)

_RE_CODE_BLOCK = re.compile(r"```[\s\S]*?```|~~~[\s\S]*?~~~", re.MULTILINE)
_RE_INLINE_CODE = re.compile(r"`[^`\n]+`")
_RE_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\((?:https?://|file:)[^)]+\)", re.I)
_RE_URL = re.compile(r"(?i)\b(?:https?://|www\.)\S+")
_RE_WINDOWS_PATH = re.compile(r"(?i)(?:[a-z]:\\(?:[^\s\\]+\\)*[^\s]*|\\\\[^\s]+)")
_RE_UNIX_PATH = re.compile(r"(?<!\w)/(?:home|Users|var|tmp|etc|opt|usr)/\S+")
_RE_UUID = re.compile(r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b")
_RE_REQUEST_ID = re.compile(r"(?i)\b(?:request|correlation|trace)[_-]?id\s*[:=]\s*\S+")
_RE_LOG_LINE = re.compile(r"(?im)^\s*\d{4}-\d{2}-\d{2}[^\n]*(?:ERROR|WARNING|DEBUG|INFO)[^\n]*$")
_RE_MARKDOWN = re.compile(r"(?:\*\*|__|~~|(?<!\w)[*_#>]+)")

__all__ = ["sanitize_for_tts", "looks_unsafe_for_tts"]


def looks_unsafe_for_tts(text: str) -> bool:
    """True, если строка содержит сырые ошибки/JSON/секреты/служебное."""
    if not text or not text.strip():
        return False
    for rx in (
        _RE_SECRET, _RE_JSON, _RE_EVENT, _RE_TRACEBACK, _RE_FRAGMENT,
        _RE_PROVIDER_ERR, _RE_CODE_BLOCK, _RE_URL, _RE_WINDOWS_PATH,
        _RE_UNIX_PATH, _RE_UUID, _RE_REQUEST_ID, _RE_LOG_LINE,
    ):
        if rx.search(text):
            return True
    # Попытка распарсить как JSON — если это чистый JSON, озвучивать нельзя.
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            json.loads(stripped)
            return True
        except (ValueError, json.JSONDecodeError):
            pass
    return False


def sanitize_for_tts(text: str, *, fallback: str = "") -> str:
    """Возвращает безопасный для озвучки текст.

    Если в исходнике есть сырые ошибки/JSON/секреты — возвращает
    ``fallback`` (честное, но не сырое сообщение). Иначе возвращает
    исходник, очищенный от служебного мусора (маркерки, лишние
    теги), но сохраняя живой язык.

    Args:
        text: текст, который собираемся озвучить.
        fallback: что сказать, если текст небезопасен для голоса.
    """
    if not text or not text.strip():
        return ""

    stripped = text.strip()
    if stripped.startswith(("{", "[")):
        try:
            json.loads(stripped)
            return fallback
        except (ValueError, json.JSONDecodeError):
            pass

    # Ошибки, traceback, secrets, JSON и логи блокируются целиком. Естественная
    # terminal-failure реплика создаётся ErrorMapper до этого слоя.
    if any(rx.search(text) for rx in (
        _RE_SECRET, _RE_JSON, _RE_EVENT, _RE_TRACEBACK, _RE_FRAGMENT,
        _RE_PROVIDER_ERR, _RE_REQUEST_ID, _RE_LOG_LINE,
    )):
        return fallback

    # Представление, а не переозвучивание UI: code удаляется, markdown links
    # оставляют только понятную подпись, identifiers/paths/URLs исчезают.
    cleaned = _RE_CODE_BLOCK.sub(" ", text)
    cleaned = _RE_INLINE_CODE.sub(" ", cleaned)
    cleaned = _RE_MARKDOWN_LINK.sub(r"\1", cleaned)
    cleaned = _RE_URL.sub(" ", cleaned)
    cleaned = _RE_WINDOWS_PATH.sub(" ", cleaned)
    cleaned = _RE_UNIX_PATH.sub(" ", cleaned)
    cleaned = _RE_UUID.sub(" ", cleaned)
    cleaned = _RE_EVENT.sub("", cleaned)
    cleaned = _RE_MARKDOWN.sub("", cleaned)
    # Sprint 3: визуальный индикатор деградации ответа не читаем вслух.
    cleaned = re.sub(r"(?i)^\s*\[\s*degraded\s*\]\s*:?\s*", "", cleaned)
    cleaned = re.sub(r"^\s*<\s*think\s*>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    if not cleaned:
        return ""
    return cleaned
