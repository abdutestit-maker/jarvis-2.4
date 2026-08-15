"""Фабрика LLM-бэкендов с кэшированием инстансов.

Зачем кэш: локальная Qwen 4B держит веса в ОЗУ (несколько ГБ), а удалённые
бэкенды — открытую HTTP-сессию. Пересоздавать их на каждый запрос нельзя.
Ключ кэша — ``(provider, model_id)``, поэтому два тира с одной и той же
моделью переиспользуют один объект.

Использование::

    from core.llm.factory import get_llm_backend, warm_up_backends

    backend = get_llm_backend(settings, "fast")     # LocalQwenBackend
    analyst = get_llm_backend(settings, "analyst")  # RemoteAPIBackend
"""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional, Tuple, Union

from config.settings import LOCAL_PROVIDER, Settings
from core.llm.backend import BackendConfigError, BackendUnavailable, LLMBackend
from core.llm.local_qwen import LocalQwenBackend
from core.llm.remote_api import RemoteAPIBackend
from core.llm.tiers import Tier, resolve_tier, tier_to_backend_key
from core.utils.logger import get_logger

__all__ = [
    "get_llm_backend",
    "get_embedding_backend",
    "clear_backend_cache",
    "warm_up_backends",
    "available_backends",
]

log = get_logger(__name__)

#: Кэш: (provider, model_id, mode) -> backend
_cache: Dict[Tuple[str, str, str], LLMBackend] = {}
_cache_lock = threading.RLock()

#: Ключ кэша для эмбеддингов, чтобы не путать с чат-режимом той же модели.
_MODE_CHAT = "chat"
_MODE_EMBED = "embed"


def _cache_key(provider: str, model_id: str, mode: str) -> Tuple[str, str, str]:
    return (provider.strip().lower(), (model_id or "").strip(), mode)


def _build_backend(settings: Settings, provider: str, model_id: str,
                   mode: str) -> LLMBackend:
    """Создаёт новый бэкенд без обращения к кэшу.

    Raises:
        BackendConfigError: конфигурация неполна.
    """
    if provider == LOCAL_PROVIDER:
        # Определяем тир по model_id (если это локальный тир)
        # model_id содержит логическое имя (например, "qwen-4b-local" или "qwen-coder-local")
        # Нужно найти, какому тиру соответствует этот model_id
        from core.llm.tiers import resolve_tier, tier_to_backend_key
        # Ищем тир, у которого model_tiers[key] == model_id
        tier_for_model = None
        for tier_key in ("fast", "analyst", "coder", "architect"):
            if settings.model_tiers.get(tier_key) == model_id:
                tier_for_model = tier_key
                break

        # П1 §1.1: тяжёлую локальную модель (7B-coder/architect) БОЛЬШЕ НЕ
        # грузим «просто так» на локальном железе. Локальный провайдер
        # разрешён ТОЛЬКО для FAST-тира (лицо Qwen 4B). Любая попытка
        # поднять coder/architect локально — жёсткая ошибка конфигурации,
        # чтобы совет мудрецов честно деградировал до FAST, а не грузил 7B.
        if tier_for_model is not None and tier_for_model != "fast":
            raise BackendConfigError(
                f"Локальный провайдер для тира '{tier_for_model}' запрещён (П1 §1.1): "
                f"тяжёлые локальные модели удалены из эскалации. Используйте "
                f"удалённого провайдера для coder/architect."
            )

        local_cfg = settings.get_local_config(tier_for_model) if tier_for_model else settings.local_model
        
        return LocalQwenBackend(
            gguf_path=local_cfg.resolved_gguf_path,
            model_id=model_id,
            n_gpu_layers=local_cfg.n_gpu_layers,
            n_ctx=local_cfg.n_ctx,
            n_threads=local_cfg.effective_threads,
            n_batch=local_cfg.n_batch,
            temperature=local_cfg.temperature,
            max_tokens=local_cfg.max_tokens,
            chat_format=local_cfg.chat_format,
            verbose=local_cfg.verbose,
            embedding=(mode == _MODE_EMBED),
        )
    return RemoteAPIBackend.from_settings(settings, provider, model_id=model_id)


def get_llm_backend(settings: Settings, tier: Union[str, Tier] = Tier.FAST) -> LLMBackend:
    """Возвращает бэкенд для указанного тира совета мудрецов.

    Инстансы кэшируются: повторный вызов с тем же тиром отдаёт тот же объект.

    Args:
        settings: конфигурация проекта.
        tier: тир ('fast' / 'analyst' / 'coder' / 'architect' или ``Tier``).

    Returns:
        Реализация :class:`LLMBackend`.

    Raises:
        BackendConfigError: для тира не хватает настроек (ключ, endpoint, model-id,
            путь к GGUF). Роутер должен ловить это и переходить к другому тиру.
    """
    resolved = resolve_tier(str(tier))
    tier_key = tier_to_backend_key(resolved)
    provider = settings.get_provider(resolved)
    model_id = settings.get_model_id(resolved) or ""

    if not model_id:
        raise BackendConfigError(
            f"Для тира '{tier_key}' не задан model-id "
            f"(settings.json -> model_tiers.{tier_key})"
        )

    key = _cache_key(provider, model_id, _MODE_CHAT)
    with _cache_lock:
        cached = _cache.get(key)
        if cached is not None:
            return cached

        backend = _build_backend(settings, provider, model_id, _MODE_CHAT)
        _cache[key] = backend
        log.info("Создан бэкенд для тира '%s': %s", tier_key, backend.name)
        return backend


def get_embedding_backend(settings: Settings) -> LLMBackend:
    """Возвращает бэкенд для построения эмбеддингов.

    Приоритет:
        1. отдельная локальная GGUF-модель эмбеддингов
           (``local_model.embedding_gguf_path``);
        2. основная локальная модель в режиме ``embedding=True``.

    Обратите внимание: штатный путь векторной памяти — встроенный эмбеддер
    ChromaDB (Часть 3). Эта функция нужна, когда пользователь хочет считать
    эмбеддинги локальной GGUF-моделью.

    Raises:
        BackendConfigError: путь к локальной модели не задан.
    """
    local = settings.local_model
    path = local.resolved_embedding_path or local.resolved_gguf_path
    if path is None:
        raise BackendConfigError(
            "Не задан путь к локальной модели "
            "(settings.json -> local_model.gguf_path / embedding_gguf_path)"
        )

    model_id = f"embed:{path.name}"
    key = _cache_key(LOCAL_PROVIDER, model_id, _MODE_EMBED)
    with _cache_lock:
        cached = _cache.get(key)
        if cached is not None:
            return cached

        backend = LocalQwenBackend.from_settings(settings, model_id=model_id, embedding=True)
        _cache[key] = backend
        log.info("Создан бэкенд эмбеддингов: %s", backend.name)
        return backend


def available_backends(settings: Settings) -> Dict[str, Optional[LLMBackend]]:
    """Пытается собрать бэкенды по всем тирам.

    Недоступные тиры получают значение ``None`` — исключения не поднимаются.
    Роутер использует это, чтобы знать, куда можно эскалировать.
    """
    result: Dict[str, Optional[LLMBackend]] = {}
    for tier in Tier:
        tier_key = tier_to_backend_key(tier)
        if not settings.is_tier_available(tier):
            result[tier_key] = None
            continue
        try:
            result[tier_key] = get_llm_backend(settings, tier)
        except (BackendConfigError, BackendUnavailable) as exc:
            log.warning("Тир '%s' недоступен: %s", tier_key, exc)
            result[tier_key] = None
    return result


def warm_up_backends(settings: Settings, tiers: Optional[List[Union[str, Tier]]] = None,
                     fail_fast: bool = False) -> Dict[str, bool]:
    """Прогревает бэкенды перед началом работы.

    По умолчанию греется только локальный тир: удалённые прогревать не нужно
    (это лишние платные вызовы), достаточно проверки конфигурации.

    Args:
        settings: конфигурация.
        tiers: какие тиры греть. По умолчанию — ``[Tier.FAST]``.
        fail_fast: если True — поднять исключение при первом провале.

    Returns:
        Словарь «тир -> успех прогрева».

    Raises:
        BackendUnavailable: если ``fail_fast=True`` и прогрев не удался.
    """
    targets = tiers if tiers is not None else [Tier.FAST]
    report: Dict[str, bool] = {}

    for tier in targets:
        tier_key = tier_to_backend_key(resolve_tier(str(tier)))
        try:
            backend = get_llm_backend(settings, tier)
            backend.warm_up()
            report[tier_key] = True
            log.info("Тир '%s' прогрет: %s", tier_key, backend.name)
        except (BackendConfigError, BackendUnavailable, ValueError) as exc:
            report[tier_key] = False
            log.error("Прогрев тира '%s' не удался: %s", tier_key, exc)
            if fail_fast:
                raise
    return report


def clear_backend_cache() -> None:
    """Закрывает и удаляет все кэшированные бэкенды.

    Вызывать при смене конфигурации (пользователь поменял путь к модели или
    ключи в настройках) и при завершении работы приложения.
    """
    with _cache_lock:
        for key, backend in list(_cache.items()):
            try:
                backend.close()
            except (OSError, RuntimeError) as exc:
                log.debug("Ошибка закрытия бэкенда %s: %s", key, exc)
        _cache.clear()
        log.info("Кэш LLM-бэкендов очищен")


def cached_backend_names() -> List[str]:
    """Имена бэкендов, находящихся в кэше (для диагностики и HUD)."""
    with _cache_lock:
        return [backend.name for backend in _cache.values()]
