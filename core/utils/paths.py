"""Пути проекта и создание рабочих каталогов.

Модуль сознательно не зависит ни от чего внутри проекта (кроме stdlib):
его импортируют и logger, и settings, поэтому любая обратная зависимость
привела бы к циклу импортов.

Единственный источник истины о расположении проекта — константа
``PROJECT_ROOT``: она вычисляется от файла модуля, поэтому работает
одинаково при запуске из любой рабочей директории.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional, Union

__all__ = [
    "PROJECT_ROOT",
    "DEFAULT_DATA_DIR",
    "DATA_SUBDIR_KEYS",
    "project_root",
    "default_paths",
    "resolve_path",
    "ensure_dirs",
    "ensure_parent",
]

PathLike = Union[str, os.PathLike[str], Path]

def _runtime_project_root() -> Path:
    """Resolve the install root for source and frozen runtimes.

    The desktop bundle launches the backend from a Tauri resource directory,
    while PyInstaller extracts Python modules into a temporary folder.  A
    process-owned ``JARVIS_HOME`` is therefore the only stable anchor in the
    packaged path; source runs keep the historical module-relative fallback.
    """
    configured = os.environ.get("JARVIS_HOME", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_dir():
            return candidate.resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


#: Корень проекта: env anchor for packaged runtime, module path in source.
PROJECT_ROOT: Path = _runtime_project_root()

#: Каталог данных по умолчанию (может быть переопределён в settings.paths)
DEFAULT_DATA_DIR: Path = PROJECT_ROOT / "data"

#: Ключи каталогов, которые обязаны существовать до старта ассистента.
#: Порядок важен только для читаемости логов.
DATA_SUBDIR_KEYS: tuple[str, ...] = (
    "data_dir",
    "documents_dir",
    "profile_dir",
    "memory_dir",
    "graph_dir",
    "models_dir",
    "logs_dir",
)


def project_root() -> Path:
    """Возвращает абсолютный путь к корню проекта."""
    return PROJECT_ROOT


def default_paths() -> Dict[str, Path]:
    """Пути каталогов данных по умолчанию (абсолютные).

    Используется, когда конфигурация ещё не загружена (например, чтобы
    настроить логирование до чтения settings.json).
    """
    data = DEFAULT_DATA_DIR
    return {
        "data_dir": data,
        "documents_dir": data / "documents",
        "profile_dir": data / "profile",
        "memory_dir": data / "memory",
        "graph_dir": data / "graph",
        "models_dir": data / "models",
        "logs_dir": data / "logs",
    }


def resolve_path(value: Optional[PathLike], base: Optional[PathLike] = None) -> Optional[Path]:
    """Приводит путь к абсолютному виду.

    * раскрывает ``~`` и переменные окружения (``%APPDATA%``, ``$HOME``);
    * относительные пути считает относительно ``base`` (по умолчанию — корень проекта);
    * пустая строка / ``None`` -> ``None`` (значит «не задано»).
    """
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None

    expanded = Path(os.path.expandvars(raw)).expanduser()
    if expanded.is_absolute():
        return expanded
    root = Path(base).expanduser().resolve() if base is not None else PROJECT_ROOT
    return (root / expanded).resolve()


def ensure_dirs(paths: Optional[Mapping[str, PathLike]] = None,
                keys: Optional[Iterable[str]] = None) -> Dict[str, Path]:
    """Создаёт рабочие каталоги, если их нет, и возвращает абсолютные пути.

    Args:
        paths: отображение «ключ -> путь» (обычно ``settings.paths.as_dict()``).
            Если не передано — используются пути по умолчанию.
        keys: подмножество ключей, которые нужно создать. По умолчанию —
            все ключи из ``DATA_SUBDIR_KEYS``, присутствующие в ``paths``.

    Returns:
        Словарь «ключ -> абсолютный Path» только по фактически созданным/
        проверенным каталогам.

    Raises:
        OSError: если каталог невозможно создать (нет прав, занято имя файла).
    """
    source: Mapping[str, PathLike] = paths if paths is not None else default_paths()
    wanted = tuple(keys) if keys is not None else DATA_SUBDIR_KEYS

    created: Dict[str, Path] = {}
    for key in wanted:
        raw = source.get(key)
        if raw is None:
            continue
        target = resolve_path(raw)
        if target is None:
            continue
        # exist_ok=True — повторный запуск не должен падать
        target.mkdir(parents=True, exist_ok=True)
        created[key] = target
    return created


def ensure_parent(file_path: PathLike) -> Path:
    """Гарантирует существование родительского каталога для файла.

    Возвращает абсолютный путь к самому файлу (файл не создаётся).
    """
    resolved = resolve_path(file_path)
    if resolved is None:
        raise ValueError("ensure_parent: пустой путь к файлу")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved
