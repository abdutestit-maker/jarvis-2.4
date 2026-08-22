"""Каталог свободных LLM-провайдеров (бесплатные тиры, без жёстко-зашитых ключей).

Цель: дать Джарвису реальный облачный путь «ответь как DeepSeek Flash за
1-3 сек» БЕЗ платных подписок — через официальные бесплатные тиры. Ключ
пользователь при желании вводит в приватное хранилище; здесь НЕТ и не
должно быть чужих/утёкших секретов.

Провайдеры OpenAI-совместимые (base_url + api_key + model), поэтому
вписываются в существующую абстракцию ``settings.get_api_key /
get_endpoint / get_provider`` без переделки роутера.

ВАЖНО про «бесплатные ключи из GitHub»: то, что лежит в открытых репо —
это чужие утёкшие секреты или фейки. Мы их НЕ используем. Ниже — только
официальные бесплатные тиры, которые пользователь активирует сам.

Каталог (по состоянию на 2026, проверять актуальность):
    * OpenRouter     — base https://openrouter.ai/api/v1, модель с суффиксом
      ``:free`` (есть бесплатные модели, скорость хорошая).
    * Groq           — base https://api.groq.com/openai/v1, бесплатный тир,
      очень быстрый (llama-3.3-70b-versatile и др.). Нужна регистрация,
      ключ бесплатный.
    * Gemini (Flash) — base https://generativelanguage.googleapis.com/v1beta/
      openai/, бесплатный тир Flash-Lite. Ключ с aistudio.
    * DeepInfra      — base https://api.deepinfra.com/v1/openai, часть моделей
      бесплатно.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

__all__ = [
    "FreeProvider",
    "FREE_PROVIDERS",
    "resolve_free_provider",
    "as_openai_compatible",
]


@dataclass(frozen=True)
class FreeProvider:
    """Описание бесплатного провайдера (OpenAI-совместимый)."""

    name: str                     # ключ в settings.api_keys/endpoints
    base_url: str
    free_models: tuple[str, ...]  # модели бесплатного тира
    requires_key: bool = True     # False = можно без ключа (открытый эндпоинт)
    tier_default: str = ""        # 'fast'/'analyst'/... если выставлять по умолч.


#: Каталог свободных провайдеров. Ключи НЕ хранятся — только endpoint+модели.
FREE_PROVIDERS: tuple[FreeProvider, ...] = (
    FreeProvider(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        free_models=("deepseek/deepseek-chat-v3-0324:free",
                     "meta-llama/llama-3.3-70b-instruct:free",
                     "microsoft/phi-4:free"),
        requires_key=True,
        tier_default="analyst",
    ),
    FreeProvider(
        name="groq",
        base_url="https://api.groq.com/openai/v1",
        free_models=("llama-3.3-70b-versatile", "llama-3.1-8b-instant"),
        requires_key=True,
    ),
    FreeProvider(
        name="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        free_models=("gemini-2.0-flash-lite", "gemini-2.0-flash"),
        requires_key=True,
    ),
    FreeProvider(
        name="deepinfra",
        base_url="https://api.deepinfra.com/v1/openai",
        free_models=("meta-llama/Llama-3.3-70B-Instruct-Turbo",),
        requires_key=True,
    ),
)


def resolve_free_provider(settings: Any, *,
                          preferred: Optional[str] = None) -> Optional[FreeProvider]:
    """Выбрать свободного провайдера, у которого пользователь задал ключ.

    Возвращает первый провайдер из каталога (сначала ``preferred``), для
    которого ``settings.get_api_key(name)`` непустой. ``None`` — ни один не
    активирован (offline/никто не дал ключа).
    """
    order: list[FreeProvider]
    if preferred:
        order = sorted(FREE_PROVIDERS, key=lambda p: p.name != preferred)
    else:
        order = list(FREE_PROVIDERS)
    for prov in order:
        key = settings.get_api_key(prov.name)
        if prov.requires_key and not key:
            continue
        # Для провайдеров без ключа тоже проверяем, что не в offline_mode.
        if getattr(settings, "offline_mode", False) and prov.requires_key:
            continue
        return prov
    return None


def as_openai_compatible(prov: FreeProvider, model: Optional[str] = None) -> dict[str, Any]:
    """Собрать OpenAI-совместимую конфигурацию (base_url/model) для remote_api.

    Ключ НЕ подставляется сюда глобально — его добавляет caller через
    ``settings.get_api_key(prov.name)`` в момент вызова (не хранится здесь).
    """
    return {
        "provider": prov.name,
        "base_url": prov.base_url,
        "model": model or (prov.free_models[0] if prov.free_models else ""),
    }
