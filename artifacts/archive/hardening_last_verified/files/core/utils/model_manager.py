"""Управление моделями (ModelManager) — консольный слой + задел под GUI.

Позволяет регистрировать локальные модели и голоса без ручного редактирования
settings.json. Используется и консольными командами в main.py, и будущим GUI.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import Settings, load_config
from core.utils.logger import get_logger
from core.utils.paths import PROJECT_ROOT, ensure_parent
from core.security.atomic import atomic_json_write, load_json

__all__ = ["ModelManager"]

log = get_logger(__name__)


class ModelManager:
    """Менеджер регистрации моделей и голосов."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """
        Args:
            settings: объект Settings. Если не передан, загружается из файла.
        """
        self._settings = settings or load_config()
        self._config_path = self._settings.source_path or (PROJECT_ROOT / "config" / "settings.json")

    # --------------------------------------------------------------------- #
    #  Локальные модели (GGUF)
    # --------------------------------------------------------------------- #

    def register_local_model(
        self,
        name: str,
        path: str,
        role: str = "coder",
    ) -> None:
        """
        Регистрирует локальную GGUF-модель для указанного тира.

        Args:
            name: логическое имя модели (например, "qwen-coder-local").
            path: путь к файлу *.gguf (исходник копируется в data/models/).
            role: тир — "fast" | "analyst" | "coder" | "architect" | "embedding".

        Raises:
            ValueError: если роль неизвестна или файл не найден.
        """
        src = Path(path).expanduser().resolve()
        if not src.is_file():
            raise ValueError(f"Файл модели не найден: {src}")

        # Копируем в data/models/ если нужно
        models_dir = self._settings.models_dir
        models_dir.mkdir(parents=True, exist_ok=True)
        dst = models_dir / src.name

        if src != dst:
            log.info("Копирую модель %s -> %s", src, dst)
            shutil.copy2(src, dst)
        else:
            log.info("Модель уже в data/models/: %s", dst)

        # Обновляем конфиг в зависимости от роли
        config = self._load_config_dict()

        if role == "fast":
            config.setdefault("local_model", {})["gguf_path"] = f"data/models/{src.name}"
            config.setdefault("model_tiers", {})["fast"] = name
            config.setdefault("tier_providers", {})["fast"] = "local"
        elif role == "coder":
            # П1 §1.1: локальный 7B-coder удалён из эскалации. Регистрация
            # coder-модели ТЕПЕРЬ означает удалённого провайдера (Kimi/DeepSeek) —
            # поле local_coder_model больше не используется для спавна бэкенда.
            config.setdefault("model_tiers", {})["coder"] = name
            config.setdefault("tier_providers", {})["coder"] = "remote"
        elif role == "analyst":
            # Для analyst обычно используются удалённые модели, но можно добавить локальную
            config.setdefault("local_analyst_model", {})["gguf_path"] = f"data/models/{src.name}"
            config.setdefault("model_tiers", {})["analyst"] = name
            config.setdefault("tier_providers", {})["analyst"] = "local"
        elif role == "architect":
            config.setdefault("local_architect_model", {})["gguf_path"] = f"data/models/{src.name}"
            config.setdefault("model_tiers", {})["architect"] = name
            config.setdefault("tier_providers", {})["architect"] = "local"
        elif role == "embedding":
            config.setdefault("local_model", {})["embedding_gguf_path"] = f"data/models/{src.name}"
        else:
            raise ValueError(f"Неизвестная роль: {role}. Допустимо: fast, analyst, coder, architect, embedding")

        self._save_config_dict(config)
        log.info("Модель '%s' зарегистрирована для роли '%s'", name, role)

    def unregister_local_model(self, role: str) -> None:
        """
        Снимает регистрацию локальной модели для роли (не удаляет файл).

        Args:
            role: тир — "fast" | "analyst" | "coder" | "architect" | "embedding".
        """
        config = self._load_config_dict()

        if role == "fast":
            config.setdefault("local_model", {}).pop("gguf_path", None)
            config.setdefault("model_tiers", {}).pop("fast", None)
            config.setdefault("tier_providers", {}).pop("fast", None)
        elif role == "coder":
            # П1 §1.1: локальный coder удалён. Снимаем только удалённую
            # регистрацию (model_tiers/tier_providers). Поле local_coder_model
            # оставлено для обратной совместимости загрузки старых settings.json.
            config.setdefault("model_tiers", {}).pop("coder", None)
            config.setdefault("tier_providers", {}).pop("coder", None)
        elif role == "analyst":
            config.setdefault("local_analyst_model", {}).pop("gguf_path", None)
            config.setdefault("model_tiers", {}).pop("analyst", None)
            config.setdefault("tier_providers", {}).pop("analyst", None)
        elif role == "architect":
            config.setdefault("local_architect_model", {}).pop("gguf_path", None)
            config.setdefault("model_tiers", {}).pop("architect", None)
            config.setdefault("tier_providers", {}).pop("architect", None)
        elif role == "embedding":
            config.setdefault("local_model", {}).pop("embedding_gguf_path", None)
        else:
            raise ValueError(f"Неизвестная роль: {role}")

        self._save_config_dict(config)
        log.info("Регистрация модели для роли '%s' снята", role)

    # --------------------------------------------------------------------- #
    #  Голоса Piper TTS
    # --------------------------------------------------------------------- #

    def register_voice(
        self,
        name: str,
        onnx_path: str,
        json_path: Optional[str] = None,
        language: str = "ru",
    ) -> None:
        """
        Регистрирует голос Piper TTS.

        Args:
            name: имя голоса (используется как ключ, например "jarvis-medium").
            onnx_path: путь к *.onnx файлу модели голоса.
            json_path: путь к *.onnx.json конфигу (если None — ищется рядом с onnx).
            language: язык голоса ("en" | "ru" | ...).
        """
        src_onnx = Path(onnx_path).expanduser().resolve()
        if not src_onnx.is_file():
            raise ValueError(f"Файл голоса не найден: {src_onnx}")

        if json_path:
            src_json = Path(json_path).expanduser().resolve()
        else:
            src_json = src_onnx.with_suffix(".json")
            if not src_json.exists():
                src_json = src_onnx.with_name(src_onnx.name + ".json")

        if not src_json.is_file():
            raise ValueError(f"Конфиг голоса не найден: {src_json} (ожидался рядом с .onnx)")

        # Копируем в data/models/piper/
        piper_dir = self._settings.models_dir / "piper"
        piper_dir.mkdir(parents=True, exist_ok=True)

        dst_onnx = piper_dir / src_onnx.name
        dst_json = piper_dir / src_json.name

        if src_onnx != dst_onnx:
            log.info("Копирую голос %s -> %s", src_onnx, dst_onnx)
            shutil.copy2(src_onnx, dst_onnx)
        if src_json != dst_json:
            log.info("Копирую конфиг голоса %s -> %s", src_json, dst_json)
            shutil.copy2(src_json, dst_json)

        # Обновляем piper_voices в конфиге
        config = self._load_config_dict()
        voice_cfg = config.setdefault("voice", {})

        # Удаляем старый голос с тем же именем если есть
        voices = voice_cfg.get("piper_voices", [])
        voices = [v for v in voices if v.get("model_path", "").endswith(src_onnx.name) is False]

        voices.append({
            "model_path": f"data/models/piper/{src_onnx.name}",
            "language": language,
            "speaker_id": 0,
            "length_scale": 1.0,
            "noise_scale": 0.667,
            "noise_w": 0.8,
        })
        voice_cfg["piper_voices"] = voices

        # Если это первый голос или язык en — делаем его основным
        if not voice_cfg.get("piper_model_path") or language == "en":
            voice_cfg["piper_model_path"] = f"data/models/piper/{src_onnx.name}"

        self._save_config_dict(config)
        log.info("Голос '%s' (%s) зарегистрирован", name, language)

    def unregister_voice(self, name: str) -> None:
        """
        Снимает регистрацию голоса (не удаляет файлы).

        Args:
            name: имя голоса (stem onnx файла, например "jarvis-medium").
        """
        config = self._load_config_dict()
        voice_cfg = config.get("voice", {})
        voices = voice_cfg.get("piper_voices", [])

        voices = [v for v in voices if not v.get("model_path", "").endswith(f"{name}.onnx")]
        voice_cfg["piper_voices"] = voices

        # Если удалили основной голос, обнуляем piper_model_path
        if voice_cfg.get("piper_model_path", "").endswith(f"{name}.onnx"):
            voice_cfg["piper_model_path"] = ""
            if voices:
                voice_cfg["piper_model_path"] = voices[0]["model_path"]

        self._save_config_dict(config)
        log.info("Голос '%s' снят с регистрации", name)

    # --------------------------------------------------------------------- #
    #  Список зарегистрированных
    # --------------------------------------------------------------------- #

    def list_models(self) -> Dict[str, Any]:
        """Возвращает словарь с текущими регистрациями по всем тирам."""
        config = self._load_config_dict()

        result = {}
        # Локальные модели
        local_model = config.get("local_model", {})
        if local_model.get("gguf_path"):
            result["fast"] = {
                "path": local_model["gguf_path"],
                "model_id": config.get("model_tiers", {}).get("fast"),
                "provider": config.get("tier_providers", {}).get("fast"),
            }
        if local_model.get("embedding_gguf_path"):
            result.setdefault("fast", {})["embedding_path"] = local_model["embedding_gguf_path"]

        local_coder = config.get("local_coder_model", {})
        if local_coder.get("gguf_path"):
            result["coder"] = {
                "path": local_coder["gguf_path"],
                "model_id": config.get("model_tiers", {}).get("coder"),
                "provider": config.get("tier_providers", {}).get("coder"),
            }

        local_analyst = config.get("local_analyst_model", {})
        if local_analyst.get("gguf_path"):
            result["analyst"] = {
                "path": local_analyst["gguf_path"],
                "model_id": config.get("model_tiers", {}).get("analyst"),
                "provider": config.get("tier_providers", {}).get("analyst"),
            }

        local_architect = config.get("local_architect_model", {})
        if local_architect.get("gguf_path"):
            result["architect"] = {
                "path": local_architect["gguf_path"],
                "model_id": config.get("model_tiers", {}).get("architect"),
                "provider": config.get("tier_providers", {}).get("architect"),
            }

        # Голоса
        voice_cfg = config.get("voice", {})
        voices = voice_cfg.get("piper_voices", [])
        if voices:
            result["voices"] = [
                {
                    "model_path": v.get("model_path"),
                    "language": v.get("language"),
                    "speaker_id": v.get("speaker_id", 0),
                }
                for v in voices
            ]

        return result

    # --------------------------------------------------------------------- #
    #  Внутренние методы
    # --------------------------------------------------------------------- #

    def _load_config_dict(self) -> Dict[str, Any]:
        """Загружает конфиг как словарь."""
        if self._config_path.exists():
            return load_json(self._config_path, default={})
        return {}

    def _save_config_dict(self, config: Dict[str, Any]) -> None:
        """Атомарно сохраняет конфиг."""
        ensure_parent(self._config_path)
        try:
            atomic_json_write(self._config_path, config)
            log.info("Конфигурация обновлена: %s", self._config_path)
        except (OSError, json.JSONDecodeError) as exc:
            log.error("Не удалось сохранить конфиг: %s", exc)
            raise RuntimeError(f"Ошибка сохранения конфигурации: {exc}") from exc
