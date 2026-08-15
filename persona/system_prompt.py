"""Сборка системного промпта для LLM.

``build_system_prompt`` комбинирует:
1. Базовую персону (``persona/persona.md``)
2. Профиль пользователя (``get_profile_context``)
3. Найденный контекст памяти (``RetrievedContext``)
в единый system prompt для передачи в LLM.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from config.settings import Settings
from core.memory.profile import get_profile_context
from core.state import RetrievedContext
from core.utils.logger import get_logger
from core.utils.paths import PROJECT_ROOT

__all__ = ["build_system_prompt", "load_persona_text"]

log = get_logger(__name__)

# Путь к файлу персоны
PERSONA_PATH = PROJECT_ROOT / "persona" / "persona.md"

# Кэш персоны
_PERSONA_CACHE: Optional[str] = None


def load_persona_text() -> str:
    """Загружает текст персоны из markdown-файла (с кэшированием)."""
    global _PERSONA_CACHE
    if _PERSONA_CACHE is not None:
        return _PERSONA_CACHE

    try:
        text = PERSONA_PATH.read_text(encoding="utf-8")
        _PERSONA_CACHE = text
        log.debug("Персона загружена из %s (%d символов)", PERSONA_PATH, len(text))
        return text
    except Exception as exc:
        log.error("Не удалось загрузить персону из %s: %s", PERSONA_PATH, exc)
        # Фоллбэк — минимальная персона
        fallback = (
            "Ты — Джарвис, локальный ИИ-ассистент. Обращение: «сёр». "
            "Стиль: саркастичный, лояльный, лаконичный. Отвечай кратко, по делу."
        )
        _PERSONA_CACHE = fallback
        return fallback


def build_system_prompt(
    settings: Settings,
    retrieved_context: Optional[RetrievedContext] = None,
) -> str:
    """Собирает полный системный промпт.

    Args:
        settings: конфигурация (для имени/обращения).
        retrieved_context: контекст из памяти (профиль, долгая память, документы, граф).

    Returns:
        Готовый system prompt строка.
    """
    parts: list[str] = []

    # 1. Базовая персона
    persona_text = load_persona_text()
    parts.append(persona_text.strip())

    # 2. Имя и обращение из настроек
    persona_name = getattr(getattr(settings, "persona", None), "name", "Джарвис")
    address = getattr(getattr(settings, "persona", None), "address", "сёр")
    language = getattr(getattr(settings, "persona", None), "language", "ru")

    parts.append(f"\n---\nИмя: {persona_name}. Обращение: «{address}». Язык ответа: {language}.")

    # 3. Профиль пользователя
    if retrieved_context and retrieved_context.get("profile"):
        profile_ctx = retrieved_context["profile"].strip()
        if profile_ctx:
            parts.append(f"\n---\nПрофиль пользователя:\n{profile_ctx}")

    # 4. Долгая память (релевантные факты)
    if retrieved_context and retrieved_context.get("long_term"):
        lt = retrieved_context["long_term"]
        if lt:
            parts.append("\n---\nРелевантные факты из долгой памяти:")
            for i, item in enumerate(lt, 1):
                parts.append(f"  {i}. {item}")

    # 5. Документы (RAG)
    if retrieved_context and retrieved_context.get("documents"):
        docs = retrieved_context["documents"]
        if docs:
            parts.append("\n---\nРелевантные фрагменты из документов:")
            for i, doc in enumerate(docs, 1):
                preview = doc[:300] + ("…" if len(doc) > 300 else "")
                parts.append(f"  [{i}] {preview}")

    # 6. Граф знаний
    if retrieved_context and retrieved_context.get("graph"):
        graph = retrieved_context["graph"]
        if graph:
            parts.append("\n---\nСвязи из графа знаний:")
            for node in graph:
                parts.append(f"  • {node}")

    # 7. Направляющие для ответа
    parts.append(
        "\n---\n"
        "ПРАВИЛА ОТВЕТА:\n"
        "1. Обращайся «сёр».\n"
        "2. Отвечай кратко (1-3 предложения или список). Никаких эссе.\n"
        "3. Используй контекст выше — не выдумывай факты.\n"
        "4. Если не знаешь — скажи «не знаю, сёр» или «проверю».\n"
        "5. Предупреждай перед опасными действиями.\n"
        "6. Можешь отказать, если запрос небезопасен или абсурден.\n"
        "7. Юмор сухой, по месту. Не спамь."
    )

    return "\n".join(parts)