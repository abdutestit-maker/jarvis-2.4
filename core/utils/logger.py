"""Централизованная настройка логирования.

Правила проекта:
    * ``print()`` в коде запрещён — всё через ``get_logger(__name__)``;
    * файловый лог с ротацией живёт в ``data/logs/jarvis.log``;
    * консольный вывод принудительно переводится в UTF-8, иначе кириллица
      ломается в cp1251-консоли Windows.

Типовое использование::

    from core.utils.logger import get_logger, setup_logging

    setup_logging(logs_dir=settings.logs_dir, level=settings.logging.level)
    log = get_logger(__name__)
    log.info("Джарвис запущен")
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Union

from core.utils.paths import default_paths, resolve_path

__all__ = [
    "setup_logging",
    "get_logger",
    "set_level",
    "is_configured",
    "LOG_FILENAME",
]

LOG_FILENAME = "jarvis.log"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-28s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_MAX_BYTES = 5 * 1024 * 1024  # 5 МБ на файл
DEFAULT_BACKUP_COUNT = 5

#: Логгер-корень проекта. Все модули получают дочерние логгеры от него,
#: поэтому сторонние библиотеки (chromadb, httpx) не засоряют наш файл.
ROOT_LOGGER_NAME = "jarvis"

_configured: bool = False
_log_file: Optional[Path] = None

LevelType = Union[int, str]


def _coerce_level(level: LevelType) -> int:
    """Преобразует 'INFO' / 20 в числовой уровень logging."""
    if isinstance(level, int):
        return level
    resolved = logging.getLevelName(str(level).strip().upper())
    return resolved if isinstance(resolved, int) else logging.INFO


def _build_console_handler(level: int) -> logging.Handler:
    """Консольный handler с принудительным UTF-8 (важно для Windows)."""
    stream = sys.stdout
    try:
        # Python 3.7+: TextIOWrapper.reconfigure
        stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError, OSError):
        # Поток не поддерживает reconfigure (перенаправлен/подменён) — не критично
        pass
    handler = logging.StreamHandler(stream)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    return handler


def _build_file_handler(log_path: Path, level: int, max_bytes: int,
                        backup_count: int) -> logging.Handler:
    """Файловый handler с ротацией."""
    handler = RotatingFileHandler(
        filename=str(log_path),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
        delay=True,  # файл открывается при первой записи
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    return handler


def setup_logging(
    logs_dir: Optional[Union[str, Path]] = None,
    level: LevelType = "INFO",
    console: bool = True,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    force: bool = False,
) -> Optional[Path]:
    """Настраивает логирование проекта. Идемпотентна.

    Args:
        logs_dir: каталог для файла лога. По умолчанию — ``data/logs``.
        level: уровень логирования ('DEBUG'/'INFO'/... или число).
        console: дублировать ли вывод в stdout.
        max_bytes: размер файла до ротации.
        backup_count: сколько архивных файлов хранить.
        force: пересоздать handlers, даже если логирование уже настроено.

    Returns:
        Путь к файлу лога либо ``None``, если файловый лог создать не удалось
        (тогда работает только консоль).
    """
    global _configured, _log_file

    if _configured and not force:
        return _log_file

    numeric_level = _coerce_level(level)
    root = logging.getLogger(ROOT_LOGGER_NAME)
    root.setLevel(numeric_level)
    # Keep the project logger visible to standard logging observers (pytest,
    # host applications, and structured log collectors).  The project
    # handlers remain authoritative; external handlers decide whether to
    # forward the record further.
    root.propagate = True

    for handler in list(root.handlers):
        root.removeHandler(handler)
        try:
            handler.close()
        except (OSError, ValueError):
            pass

    if console:
        root.addHandler(_build_console_handler(numeric_level))

    target_dir = resolve_path(logs_dir) if logs_dir else default_paths()["logs_dir"]
    log_path: Optional[Path] = None
    if target_dir is not None:
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            log_path = target_dir / LOG_FILENAME
            root.addHandler(_build_file_handler(log_path, numeric_level,
                                                max_bytes, backup_count))
        except OSError as exc:
            log_path = None
            root.warning("Не удалось создать файловый лог в %s: %s", target_dir, exc)

    _configured = True
    _log_file = log_path
    return log_path


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Возвращает логгер проекта.

    Имя модуля (``__name__``) автоматически подшивается под корень ``jarvis``:
    ``core.llm.remote_api`` -> ``jarvis.core.llm.remote_api``.

    Если ``setup_logging`` ещё не вызывали, логирование настраивается
    значениями по умолчанию, чтобы сообщения не терялись.
    """
    if not _configured:
        setup_logging()

    if not name or name == ROOT_LOGGER_NAME:
        return logging.getLogger(ROOT_LOGGER_NAME)
    if name.startswith(f"{ROOT_LOGGER_NAME}."):
        return logging.getLogger(name)
    return logging.getLogger(f"{ROOT_LOGGER_NAME}.{name}")


def set_level(level: LevelType) -> None:
    """Меняет уровень логирования на лету (например, из настроек GUI)."""
    numeric_level = _coerce_level(level)
    root = logging.getLogger(ROOT_LOGGER_NAME)
    root.setLevel(numeric_level)
    for handler in root.handlers:
        handler.setLevel(numeric_level)


def is_configured() -> bool:
    """Было ли логирование уже настроено."""
    return _configured
