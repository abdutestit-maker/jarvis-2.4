"""Конфигурация Джарвиса.

Публичный контракт::

    from config import load_config, Settings, ConfigError

    settings = load_config()
    settings.ensure_directories()
    settings.warn_about_missing_keys()
"""

from __future__ import annotations

from config.settings import (
    LOCAL_PROVIDER,
    ConfigError,
    Settings,
    default_config_path,
    example_config_path,
    load_config,
)

__all__ = [
    "Settings",
    "ConfigError",
    "load_config",
    "default_config_path",
    "example_config_path",
    "LOCAL_PROVIDER",
]
