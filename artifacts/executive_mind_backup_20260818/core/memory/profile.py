"""Профиль пользователя — простой JSON-файл (НЕ ChromaDB).

Профиль хранит факты о пользователе (СДВГ, хобби, предпочтения ответа и т.п.)
в человекочитаемом JSON. Используется для сборки системного промпта
(``get_profile_context``) и персонализации ответов.

Запись атомарная (tmp-файл + rename), как в ``config/settings.py``,
чтобы не оставить битый файл при сбое в середине записи.
"""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import Settings
from core.utils.logger import get_logger
from core.utils.paths import ensure_parent

__all__ = [
    "DEFAULT_PROFILE",
    "load_profile",
    "save_profile",
    "update_profile",
    "get_profile_context",
    "profile_path",
]

log = get_logger(__name__)

#: Базовые поля профиля (пустые — заполняются в ходе общения).
DEFAULT_PROFILE: Dict[str, Any] = {
    "name": "",
    "conditions": [],          # напр. ["СДВГ"]
    "interests": [],           # напр. ["GTA 5", "Менталист"]
    "dislikes": [],            # напр. ["ждать"]
    "preferences": {           # напр. {"response_length": "short"}
        "response_length": "default",
    },
    "notes": "",               # свободный текст
}


def profile_path(settings: Settings) -> Path:
    """Абсолютный путь к файлу профиля (``profile_dir/profile.json``)."""
    base = settings.paths.resolved("profile_dir")
    base.mkdir(parents=True, exist_ok=True)
    return base / "profile.json"


def load_profile(settings: Settings) -> Dict[str, Any]:
    """Загружает профиль или создаёт дефолтный, если файла нет/битый.

    При отсутствии файла профиль НЕ выдумывается — возвращается
    :data:`DEFAULT_PROFILE` (пустые поля). Файл при этом не перезаписывается
    (пользователь может создать его вручную). Чтобы материализовать файл,
    вызовите ``save_profile`` явно.

    Returns:
        Словарь профиля.
    """
    path = profile_path(settings)
    if not path.is_file():
        log.info("Файл профиля не найден (%s) — использую дефолтный пустой профиль", path)
        # Глубокая копия: DEFAULT_PROFILE содержит списки (interests/...),
        # поверхностная копия отдала бы их по ссылке — и первый же
        # learn_facts мутировал бы «дефолт» для всех будущих сессий.
        return copy.deepcopy(DEFAULT_PROFILE)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Профиль повреждён (%s), возвращаю дефолт: %s", path, exc)
        return copy.deepcopy(DEFAULT_PROFILE)

    if not isinstance(data, dict):
        log.warning("Профиль не является объектом JSON, возвращаю дефолт")
        return copy.deepcopy(DEFAULT_PROFILE)
    # Дополняем недостающие ключи дефолтами, чтобы не ловить KeyError
    # (вложенные списки тоже копируем — см. замечание выше).
    merged = copy.deepcopy(DEFAULT_PROFILE)
    merged.update(data)
    return merged


def save_profile(settings: Settings, profile: Dict[str, Any]) -> Path:
    """Атомарно сохраняет профиль в JSON (tmp + rename).

    Args:
        settings: конфигурация.
        profile: словарь профиля.

    Returns:
        Путь к сохранённому файлу.

    Raises:
        OSError: при ошибке записи.
    """
    target = profile_path(settings)
    ensure_parent(target)
    payload = json.dumps(profile, ensure_ascii=False, indent=2) + "\n"
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=str(target.parent),
            prefix=".profile.", suffix=".tmp", delete=False,
        ) as handle:
            tmp_name = handle.name
            handle.write(payload)
            handle.flush()
        import os
        os.replace(tmp_name, target)
    except OSError as exc:
        raise OSError(f"Не удалось сохранить профиль в {target}: {exc}") from exc
    log.info("Профиль сохранён: %s", target)
    return target


def update_profile(settings: Settings, key: str, value: Any) -> Dict[str, Any]:
    """Обновляет одно поле профиля и сохраняет файл.

    Args:
        settings: конфигурация.
        key: ключ верхнего уровня профиля (например, ``"interests"``).
        value: новое значение (любой JSON-совместимый тип).

    Returns:
        Обновлённый словарь профиля.
    """
    profile = load_profile(settings)
    profile[key] = value
    save_profile(settings, profile)
    log.info("Профиль обновлён: %s", key)
    return profile


def get_profile_context(settings: Settings) -> str:
    """Собирает человекочитаемую выжимку профиля для системного промпта.

    Формат примерно такой:
        «СДВГ. Любит GTA 5. Смотрит Менталиста. Не любит ждать.
        Предпочитает короткие ответы.»

    Пустой профиль -> пустая строка (без выдумок).
    """
    profile = load_profile(settings)
    parts: list[str] = []

    name = (profile.get("name") or "").strip()
    if name:
        parts.append(f"Пользователя зовут {name}.")

    conditions = profile.get("conditions") or []
    if conditions:
        parts.append(", ".join(conditions) + ".")

    interests = profile.get("interests") or []
    if interests:
        if len(interests) == 1:
            parts.append(f"Любит {interests[0]}.")
        else:
            parts.append("Любит " + ", ".join(interests) + ".")

    dislikes = profile.get("dislikes") or []
    if dislikes:
        if len(dislikes) == 1:
            parts.append(f"Не любит {dislikes[0]}.")
        else:
            parts.append("Не любит " + ", ".join(dislikes) + ".")

    preferences = profile.get("preferences") or {}
    if isinstance(preferences, dict):
        length = preferences.get("response_length")
        if length == "short":
            parts.append("Предпочитает короткие ответы.")
        elif length == "long":
            parts.append("Предпочитает подробные ответы.")

    notes = (profile.get("notes") or "").strip()
    if notes:
        parts.append(notes)

    return " ".join(parts).strip()
