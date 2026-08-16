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
_RE_SECRET = re.compile(
    r"(?i)(sk-[a-z0-9]{8,}|pk-[a-z0-9]{8,}|bearer\s+[a-z0-9._-]+|"
    r"api[_-]?key\s*[:=]\s*\S+|password\s*[:=]\s*\S+|token\s*[:=]\s*\S+)"
)
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

__all__ = ["sanitize_for_tts", "looks_unsafe_for_tts"]


def looks_unsafe_for_tts(text: str) -> bool:
    """True, если строка содержит сырые ошибки/JSON/секреты/служебное."""
    if not text or not text.strip():
        return False
    for rx in (_RE_SECRET, _RE_JSON, _RE_EVENT, _RE_TRACEBACK, _RE_FRAGMENT, _RE_PROVIDER_ERR):
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


def sanitize_for_tts(text: str, *, fallback: str = "Сэр, сейчас не могу дозвониться до модели. Попробуйте чуть позже.") -> str:
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

    if looks_unsafe_for_tts(text):
        # Сырые ошибки/ключи/JSON не должны попадать в эфир.
        return fallback

    # Очистка служебного мусора, который мог проскочить, но не опасен сам по себе.
    cleaned = _RE_EVENT.sub("", text)
    cleaned = re.sub(r"^\s*<\s*think\s*>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    if not cleaned:
        return ""
    return cleaned
