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
    "get_offline_backend",
    "get_embedding_backend",
    "clear_backend_cache",
    "warm_up_backends",
    "available_backends",
]

log = get_logger(__name__)

#: Кэш: (provider, model_id, mode, timeout, retries) -> backend
_cache: Dict[Tuple[str, str, str, Any, Any], LLMBackend] = {}
_cache_lock = threading.RLock()

#: Ключ кэша для эмбеддингов, чтобы не путать с чат-режимом той же модели.
_MODE_CHAT = "chat"
_MODE_EMBED = "embed"


def _cache_key(provider: str, model_id: str, mode: str) -> Tuple[str, str, str]:
    return (provider.strip().lower(), (model_id or "").strip(), mode)


def _build_backend(settings: Settings, provider: str, model_id: str,
                   mode: str, policy: Optional[Dict[str, Any]] = None,
                   task_role: Tier = Tier.FAST) -> LLMBackend:
    """Создаёт новый бэкенд без обращения к кэшу.

    ``policy`` — опциональные переопределения таймаута/попыток для
    удалённых бэкендов (см. :func:`_tier_policy`).

    Raises:
        BackendConfigError: конфигурация неполна.
    """
    if provider == LOCAL_PROVIDER:
        role = resolve_tier(task_role)
        local_cfg = settings.get_local_config(role)
        local_path = local_cfg.resolved_gguf_path

        # In online mode a local heavy tier is still an invalid legacy
        # configuration. Offline mode is different: the role remains CODER
        # while the best existing local model provides that role.
        if role is not Tier.FAST and not bool(getattr(settings, "offline_mode", False)):
            raise BackendConfigError(
                f"Локальный провайдер для тира '{role.value}' запрещён (П1 §1.1): "
                f"тяжёлые локальные модели удалены из эскалации. Используйте "
                f"удалённого провайдера для coder/architect."
            )
        if local_path is None or not local_path.is_file():
            local_cfg = settings.local_model
        
        backend = LocalQwenBackend(
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
        backend.task_role = role.value
        return backend
    return RemoteAPIBackend.from_settings(settings, provider, model_id=model_id,
                                          **(policy or {}))


def _tier_policy(settings: Settings, resolved_tier: Tier) -> Dict[str, Any]:
    """Политика таймаута/попыток для тира.

    FAST-тир обслуживает разговорные задачи: сбой провайдера должен
    признаваться быстро (короткий таймаут, минимум попыток), а не
    3×15 c ожидания перед честным фолбэком. CODER/ARCHITECT — глубокая
    работа (код/архитектура, Sprint 3 TIER 3): им наоборот нужен щедрый
    бюджет. ANALYST работает на общих ``limits.response_timeout_sec``.
    """
    limits = getattr(settings, "limits", None)
    if resolved_tier is Tier.FAST and limits is not None:
        return dict(
            timeout=getattr(limits, "fast_tier_timeout_sec", None),
            max_retries=getattr(limits, "fast_tier_max_retries", None),
        )
    if resolved_tier in (Tier.CODER, Tier.ARCHITECT) and limits is not None:
        return dict(
            timeout=getattr(limits, "deep_tier_timeout_sec", None),
        )
    return {}


def get_llm_backend(settings: Settings, tier: Union[str, Tier] = Tier.FAST,
                    *, policy_override: Optional[Dict[str, Any]] = None) -> LLMBackend:
    """Возвращает бэкенд для указанного тира совета мудрецов.

    Инстансы кэшируются: повторный вызов с тем же тиром отдаёт тот же объект.

    Args:
        settings: конфигурация проекта.
        tier: тир ('fast' / 'analyst' / 'coder' / 'architect' или ``Tier``).
        policy_override: принудительная политика таймаута/попыток для
            удалённого бэкенда (например, короткая «разговорная» политика
            для фолбэка простой задачи). ``None`` — политика тира.

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

    if provider == LOCAL_PROVIDER and bool(getattr(settings, "offline_mode", False)):
        selected = settings.get_local_config(resolved).resolved_gguf_path
        if selected is None or not selected.is_file():
            selected = settings.local_model.resolved_gguf_path
        if selected is not None:
            # One local GGUF instance is shared by all logical roles.  Keeping
            # the tier in ``task_role`` avoids loading the same 1.7B file more
            # than once during startup while preserving routing telemetry.
            model_id = f"local:{selected.stem}"

    if not model_id:
        raise BackendConfigError(
            f"Для тира '{tier_key}' не задан model-id "
            f"(settings.json -> model_tiers.{tier_key})"
        )

    policy = _tier_policy(settings, resolved)
    if policy_override:
        policy = {k: v for k, v in policy_override.items() if v is not None}
    # Политика входит в ключ кэша: одна и та же модель в разных тирах
    # может работать с разными таймаутами/попытками.
    # Local GGUF objects are shared across logical tiers and timeout policies;
    # otherwise startup loads the same 1.7B file twice (offline fallback key
    # versus FAST policy key) and the first user request pays a second load.
    cache_timeout = None if provider == LOCAL_PROVIDER else policy.get("timeout")
    cache_retries = None if provider == LOCAL_PROVIDER else policy.get("max_retries")
    key = (provider.strip().lower(), (model_id or "").strip(), _MODE_CHAT,
           cache_timeout, cache_retries)
    with _cache_lock:
        cached = _cache.get(key)
        if cached is not None:
            try:
                cached.task_role = resolved.value
            except Exception:
                pass
            return cached

        backend = _build_backend(settings, provider, model_id, _MODE_CHAT, policy,
                                 task_role=resolved)
        _cache[key] = backend
        log.info("Создан бэкенд для тира '%s': %s", tier_key, backend.name)
        return backend


def get_offline_backend(settings: Settings) -> LLMBackend:
    """Настоящий офлайн-бэкенд TIER 4: локальная Qwen 4B (Sprint 3).

    В отличие от ``get_llm_backend(settings, Tier.FAST)``, НЕ зависит от
    того, какой провайдер сейчас обслуживает FAST-тир (ам/bitnet/...):
    локальная GGUF-модель строится напрямую из ``settings.local_model`` и
    работает без сети. Это гарантированный последний фолбэк, когда все
    внешние провайдеры лежат или разомкнуты circuit breaker'ом.

    Raises:
        BackendConfigError: файл GGUF не задан или не существует.
    """
    local_cfg = settings.local_model
    gguf = local_cfg.resolved_gguf_path
    if gguf is None or not gguf.is_file():
        raise BackendConfigError(
            f"Офлайн-фолбэк недоступен: файл GGUF не найден "
            f"({gguf or 'путь не задан'}; settings.json -> local_model.gguf_path)"
        )
    model_id = f"local:{gguf.stem}"
    key = (LOCAL_PROVIDER, model_id, _MODE_CHAT, None, None)
    with _cache_lock:
        cached = _cache.get(key)
        if cached is not None:
            return cached
        backend = LocalQwenBackend(
            gguf_path=gguf,
            model_id=model_id,
            n_gpu_layers=local_cfg.n_gpu_layers,
            n_ctx=local_cfg.n_ctx,
            n_threads=local_cfg.effective_threads,
            n_batch=local_cfg.n_batch,
            temperature=local_cfg.temperature,
            max_tokens=local_cfg.max_tokens,
            chat_format=local_cfg.chat_format,
            verbose=local_cfg.verbose,
        )
        _cache[key] = backend
        log.info("Создан офлайн-бэкенд TIER 4: %s", backend.name)
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
