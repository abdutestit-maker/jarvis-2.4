"""Утилиты проекта: логирование и работа с путями.

Модули этого пакета не зависят от остального кода Джарвиса (кроме случаев,
оговорённых ниже), поэтому их можно импортировать из любого места без
риска циклических импортов.

ВАЖНО: ``ModelManager`` НЕ импортируется здесь на верхнем уровне — он тянет
``config.settings``, а ``config.settings`` при загрузке импортирует
``core.utils.logger``. Прямой импорт ModelManager в __init__ создаёт цикл:
config.settings -> core.utils -> model_manager -> config.settings.
Поэтому ModelManager импортируется лениво там, где нужен (см. функцию ниже).
"""

from __future__ import annotations

from core.utils.logger import get_logger, set_level, setup_logging
from core.utils.paths import (
    PROJECT_ROOT,
    default_paths,
    ensure_dirs,
    ensure_parent,
    project_root,
    resolve_path,
)

__all__ = [
    "get_logger",
    "setup_logging",
    "set_level",
    "ModelManager",
    "PROJECT_ROOT",
    "project_root",
    "default_paths",
    "resolve_path",
    "ensure_dirs",
    "ensure_parent",
]


def ModelManager(*args, **kwargs):  # noqa: N802 — фабрика, чтобы не тянуть класс при импорте пакета
    """Ленивый конструктор ModelManager (разрывает цикл импортов).

    Использование::

        from core.utils import ModelManager
        mm = ModelManager(settings)   # класс импортируется только здесь
    """
    from core.utils.model_manager import ModelManager as _MM
    return _MM(*args, **kwargs)
