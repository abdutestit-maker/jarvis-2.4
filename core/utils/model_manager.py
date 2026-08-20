"""Управление моделями (ModelManager) — консольный слой + задел под GUI.

Позволяет регистрировать локальные модели и голоса без ручного редактирования
settings.json. Используется и консольными командами в main.py, и будущим GUI.
"""

from __future__ import annotations

import json
import hashlib
import shutil
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from config.settings import Settings, load_config
from core.utils.logger import get_logger
from core.utils.paths import PROJECT_ROOT, ensure_parent
from core.security.atomic import atomic_json_write, load_json

__all__ = ["ModelArtifact", "ModelDownloadError", "ModelManager"]

log = get_logger(__name__)


@dataclass(frozen=True)
class ModelArtifact:
    """Pinned, locally verifiable model download description."""

    key: str
    filename: str
    url: str
    size_bytes: int
    sha256: str
    source_filename: str = ""

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ModelArtifact":
        filename = str(payload.get("filename") or "").strip()
        url = str(payload.get("url") or "").strip()
        digest = str(payload.get("sha256") or "").strip().casefold()
        if not filename or Path(filename).name != filename:
            raise ValueError("manifest filename must be a plain file name")
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in {
            "huggingface.co", "www.huggingface.co", "hf.co",
        }:
            raise ValueError("model source must be an HTTPS Hugging Face URL")
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError(f"invalid SHA-256 for {filename}")
        size = int(payload.get("size_bytes") or 0)
        if size <= 0:
            raise ValueError(f"invalid size for {filename}")
        return cls(
            key=str(payload.get("key") or Path(filename).stem),
            filename=filename,
            url=url,
            size_bytes=size,
            sha256=digest,
            source_filename=str(payload.get("source_filename") or ""),
        )


class ModelDownloadError(RuntimeError):
    """A model could not be downloaded or failed local verification."""


class ModelManager:
    """Менеджер регистрации моделей и голосов."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """
        Args:
            settings: объект Settings. Если не передан, загружается из файла.
        """
        self._settings = settings or load_config()
        self._config_path = self._settings.source_path or (PROJECT_ROOT / "config" / "settings.json")

    # ------------------------------------------------------------------ #
    #  Пинованный GGUF-манифест и безопасная докачка
    # ------------------------------------------------------------------ #

    @property
    def manifest_path(self) -> Path:
        """Path to the repository-owned model manifest."""
        return PROJECT_ROOT / "config" / "models_manifest.json"

    def load_model_manifest(
        self,
        path: Optional[Path | str] = None,
        *,
        include_legacy: bool = True,
    ) -> Dict[str, ModelArtifact]:
        """Load the pinned production manifest and optional legacy entries.

        ``models`` is the production set.  ``legacy_models`` remains readable
        for rollback and compatibility callers, but packaging never consumes
        it unless explicitly requested.
        """
        manifest_path = Path(path) if path is not None else self.manifest_path
        try:
            payload = load_json(manifest_path, default={})
        except (OSError, ValueError, TypeError) as exc:
            raise ModelDownloadError(f"Не удалось прочитать манифест моделей: {exc}") from exc
        rows = payload.get("models") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise ModelDownloadError("Манифест моделей не содержит списка models")
        rows = list(rows)
        if include_legacy:
            legacy = payload.get("legacy_models", [])
            if not isinstance(legacy, list):
                raise ModelDownloadError("Манифест legacy_models имеет некорректный формат")
            rows.extend(legacy)
        artifacts: Dict[str, ModelArtifact] = {}
        for row in rows:
            if not isinstance(row, dict):
                raise ModelDownloadError("Манифест содержит некорректную запись")
            try:
                artifact = ModelArtifact.from_dict(row)
            except (TypeError, ValueError) as exc:
                raise ModelDownloadError(f"Некорректная запись манифеста: {exc}") from exc
            if artifact.key in artifacts:
                raise ModelDownloadError(f"Дубликат ключа модели: {artifact.key}")
            artifacts[artifact.key] = artifact
        return artifacts

    def ensure_model(
        self,
        profile: Any,
        *,
        progress: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel: Optional[threading.Event] = None,
        timeout_sec: float = 30.0,
    ) -> Dict[str, Path]:
        """Ensure the core (and optional draft) GGUF for a hardware profile.

        Downloads are resumable and always land in ``*.part`` first.  A file
        becomes visible as a model only after its exact byte count and
        SHA-256 match the pinned manifest.  The method is explicit so a
        startup policy can choose whether to download in the background; it
        never silently reaches outside the trusted manifest.
        """
        manifest = self.load_model_manifest()
        names = [str(getattr(profile, "core_model", "") or "")]
        draft = str(getattr(profile, "draft_model", "") or "")
        if draft and draft not in names:
            names.append(draft)
        if not names or not names[0]:
            raise ModelDownloadError("Профиль не содержит core_model")

        results: Dict[str, Path] = {}
        for filename in names:
            artifact = next((item for item in manifest.values() if item.filename == filename), None)
            if artifact is None:
                raise ModelDownloadError(f"Модель не закреплена в манифесте: {filename}")
            target = self._settings.models_dir / artifact.filename
            self._ensure_artifact(
                artifact, target, progress=progress, cancel=cancel,
                timeout_sec=timeout_sec,
            )
            results[artifact.key] = target
        return results

    def _ensure_artifact(
        self,
        artifact: ModelArtifact,
        target: Path,
        *,
        progress: Optional[Callable[[Dict[str, Any]], None]],
        cancel: Optional[threading.Event],
        timeout_sec: float,
    ) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        if self._verified_file(target, artifact):
            self._emit_progress(progress, artifact, target.stat().st_size, artifact.size_bytes, "ready")
            return

        part = target.with_name(target.name + ".part")
        self._download_artifact(
            artifact, part, progress=progress, cancel=cancel, timeout_sec=timeout_sec,
        )
        if not self._verified_file(part, artifact):
            try:
                part.unlink()
            except OSError:
                pass
            raise ModelDownloadError(f"Проверка модели не пройдена: {artifact.filename}")
        # os.replace is atomic on the same volume and leaves no half-written
        # GGUF for a concurrent backend to open.
        part.replace(target)
        self._emit_progress(progress, artifact, artifact.size_bytes, artifact.size_bytes, "verified")

    @staticmethod
    def _verified_file(path: Path, artifact: ModelArtifact) -> bool:
        try:
            if path.stat().st_size != artifact.size_bytes:
                return False
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            return digest.hexdigest().casefold() == artifact.sha256
        except (OSError, ValueError):
            return False

    def _download_artifact(
        self,
        artifact: ModelArtifact,
        part: Path,
        *,
        progress: Optional[Callable[[Dict[str, Any]], None]],
        cancel: Optional[threading.Event],
        timeout_sec: float,
    ) -> None:
        try:
            offset = part.stat().st_size if part.exists() else 0
        except OSError:
            offset = 0
        headers = {"User-Agent": "JARVIS-local-model-manager/1", "Accept-Encoding": "identity"}
        if 0 < offset < artifact.size_bytes:
            headers["Range"] = f"bytes={offset}-"
        request = urllib.request.Request(artifact.url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=float(timeout_sec)) as response:
                final_url = str(getattr(response, "geturl", lambda: artifact.url)() or artifact.url)
                if urllib.parse.urlparse(final_url).hostname not in {
                    "huggingface.co", "www.huggingface.co", "hf.co",
                    "cdn-lfs.huggingface.co", "cdn-lfs-us-1.hf.co",
                }:
                    raise ModelDownloadError("редирект модели ушёл за пределы Hugging Face")
                status = int(getattr(response, "status", 200) or 200)
                resumed = offset > 0 and status == 206
                if not resumed:
                    offset = 0
                mode = "ab" if resumed else "wb"
                downloaded = offset
                with part.open(mode) as handle:
                    while True:
                        if cancel is not None and cancel.is_set():
                            raise ModelDownloadError(f"Загрузка отменена: {artifact.filename}")
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)
                        downloaded += len(chunk)
                        self._emit_progress(
                            progress, artifact, downloaded, artifact.size_bytes, "downloading",
                        )
        except ModelDownloadError:
            raise
        except (OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
            raise ModelDownloadError(f"Не удалось скачать {artifact.filename}: {exc}") from exc

        try:
            actual = part.stat().st_size
        except OSError as exc:
            raise ModelDownloadError(f"Временный файл модели не создан: {part}") from exc
        if actual != artifact.size_bytes:
            raise ModelDownloadError(
                f"Неполная загрузка {artifact.filename}: {actual} из {artifact.size_bytes} байт"
            )

    @staticmethod
    def _emit_progress(
        callback: Optional[Callable[[Dict[str, Any]], None]],
        artifact: ModelArtifact,
        downloaded: int,
        total: int,
        state: str,
    ) -> None:
        if callback is None:
            return
        try:
            callback({
                "key": artifact.key,
                "filename": artifact.filename,
                "downloaded_bytes": int(downloaded),
                "total_bytes": int(total),
                "progress": round(min(1.0, downloaded / total) if total else 0.0, 4),
                "state": state,
            })
        except Exception:
            # Progress is presentation only; it must never break a verified
            # download or turn a closed UI callback into a failed model.
            log.debug("Прогресс загрузки модели недоступен", exc_info=True)

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
