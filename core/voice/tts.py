"""Локальный Russian-only Text-to-Speech через Piper.

Voice выбирается конфигурацией, а не эвристикой языка входной строки. Это
исключает старый путь ``Error 455 -> English jarvis-medium``.

Если piper_binary_path / piper_model_path не найдены — ``is_available()`` = False,
``speak()`` логирует warning и не падает (текстовый режим остаётся рабочим).
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import threading
import time
import wave
from array import array
from pathlib import Path
from typing import Optional

from config.settings import Settings
from core.utils.logger import get_logger

__all__ = ["PiperTTS"]

log = get_logger(__name__)

# Регулярка для определения кириллицы
class VoiceConfig:
    """Конфигурация одного голоса Piper."""

    def __init__(
        self,
        name: str,
        model_path: Path,
        config_path: Path,
        language: str = "ru",
        speaker_id: int = 0,
        length_scale: float = 1.0,
        noise_scale: float = 0.667,
        noise_w: float = 0.8,
    ) -> None:
        self.name = name
        self.model_path = model_path
        self.config_path = config_path
        self.language = language
        self.speaker_id = speaker_id
        self.length_scale = length_scale
        self.noise_scale = noise_scale
        self.noise_w = noise_w


class PiperTTS:
    """Обёртка над Piper TTS с поддержкой нескольких голосов."""

    def __init__(self, settings: Settings) -> None:
        """
        Args:
            settings: конфигурация (voice.piper_binary_path, voice.piper_model_path,
                      voice.piper_voices - список дополнительных голосов).
        """
        self._settings = settings
        self._voice_settings = getattr(settings, "voice", None)
        language = str(getattr(self._voice_settings, "language", "ru")).lower()
        self._target_language = language.split("_")[0].split("-")[0]
        self._provider = str(getattr(self._voice_settings, "provider", "piper")).lower()
        self._binary = self._resolve_binary()

        # Загружаем конфигурацию голосов
        self._voices: dict[str, VoiceConfig] = {}
        self._default_voice: Optional[str] = None
        self._load_voices()

        self._available = (
            self._provider == "piper" and self._binary is not None
            and any(voice.model_path.is_file() for voice in self._voices.values())
        )

        if self._available:
            voice_names = ", ".join(self._voices.keys())
            log.info("PiperTTS инициализирован: binary=%s, voices=[%s]", self._binary, voice_names)
        else:
            log.warning(
                "PiperTTS недоступен: binary=%s, voices=%d. TTS отключён (текстовый режим).",
                self._binary,
                len(self._voices),
            )

    def _resolve_binary(self) -> Optional[Path]:
        """Находит Piper, предпочитая проверенный runtime внутри проекта.

        ``piper`` из PATH не является стабильной зависимостью: пакет Piper
        1.3.0 может находиться там вместо совместимого с текущими ONNX-голосами
        runtime. Явный существующий путь из конфигурации всё ещё имеет высший
        приоритет, затем используется локальная проверенная сборка.
        """
        voice = getattr(self._settings, "voice", None)
        if voice and getattr(voice, "piper_binary_path", None):
            p = Path(voice.piper_binary_path).expanduser()
            if not p.is_absolute():
                home = os.environ.get("JARVIS_HOME", "").strip()
                p = (Path(home) if home else Path.cwd()) / p
            if p.exists():
                return p.resolve()

        models_dir = Path(getattr(self._settings, "models_dir", Path("data/models")))
        # Source layout keeps Piper under data/runtime.  The portable
        # installer places it beside llama-server under runtime/piper, so the
        # backend still resolves the exact validated binary after Tauri moves
        # the resource tree to another machine.
        bundled_candidates = [
            models_dir.parent / "runtime" / "piper" / "piper.exe",
            models_dir.parent.parent / "runtime" / "piper" / "piper.exe",
        ]
        home = os.environ.get("JARVIS_HOME", "").strip()
        if home:
            bundled_candidates.append(Path(home) / "runtime" / "piper" / "piper.exe")
        for bundled in bundled_candidates:
            if bundled.exists():
                return bundled.resolve()

        # Стандартные места установки
        candidates = [
            Path.home() / ".local" / "bin" / "piper.exe",
            Path("C:/Program Files/piper/piper.exe"),
            Path("C:/Program Files (x86)/piper/piper.exe"),
        ]
        for c in candidates:
            try:
                if c.exists():
                    return c.resolve()
            except Exception:
                pass
        import shutil
        discovered = shutil.which("piper")
        if discovered:
            return Path(discovered).resolve()
        return None

    def _load_voices(self) -> None:
        """Загружает конфигурацию голосов из settings."""
        voice_cfg = getattr(self._settings, "voice", None)
        if not voice_cfg or self._provider != "piper":
            return

        # Основной голос (для обратной совместимости)
        main_model = getattr(voice_cfg, "resolved_primary_piper_model", None)
        if main_model is None:
            main_model = getattr(voice_cfg, "resolved_piper_model", None)
        if main_model and main_model.exists():
            config_path = main_model.with_suffix(main_model.suffix + ".json")
            if not config_path.exists():
                # Попробуем найти .onnx.json
                config_path = main_model.with_name(main_model.name + ".json")

            lang = self._model_language(config_path, main_model.stem)
            if lang != self._target_language:
                log.warning("Piper model %s skipped: language=%s, required=%s",
                            main_model.name, lang, self._target_language)
                main_model = None

        if main_model and main_model.exists():
            config_path = main_model.with_suffix(main_model.suffix + ".json")
            if not config_path.exists():
                config_path = main_model.with_name(main_model.name + ".json")
            lang = self._model_language(config_path, main_model.stem)
            # ВАЖНО: не переопределяем noise/length параметры модели своими
            # громкими значениями, если сама модель в своём .onnx.json не
            # задаёт их. Иначе голос искажается («robot/garbled» звук,
            # похожий на "err... node"). Piper сам возьмёт родные значения
            # из конфигурации модели.
            use_model_tuning = config_path.exists() and self._config_has_tuning(config_path)
            self._voices[main_model.stem] = VoiceConfig(
                name=main_model.stem,
                model_path=main_model,
                config_path=config_path if config_path.exists() else main_model,
                language=lang,
                speaker_id=getattr(voice_cfg, "piper_speaker_id", 0),
                length_scale=getattr(voice_cfg, "piper_length_scale", 1.0) if use_model_tuning else 1.0,
                noise_scale=getattr(voice_cfg, "piper_noise_scale", 0.667) if use_model_tuning else 0.0,
                noise_w=getattr(voice_cfg, "piper_noise_w", 0.8) if use_model_tuning else 0.0,
            )
            self._default_voice = main_model.stem

        # Keep the configured Russian voice selectable even before its model
        # is downloaded.  Availability still requires a real model file above.
        if main_model and not main_model.exists():
            config_path = main_model.with_suffix(main_model.suffix + ".json")
            if not config_path.exists():
                config_path = main_model.with_name(main_model.name + ".json")
            lang = self._model_language(config_path, main_model.stem)
            if lang == self._target_language:
                self._voices[main_model.stem] = VoiceConfig(
                    name=main_model.stem,
                    model_path=main_model,
                    config_path=config_path,
                    language=lang,
                    speaker_id=getattr(voice_cfg, "piper_speaker_id", 0),
                )
                self._default_voice = self._default_voice or main_model.stem

        # Дополнительные голоса из piper_voices (если заданы)
        extra_voices = getattr(voice_cfg, "piper_voices", None)
        if extra_voices and isinstance(extra_voices, list):
            for v in extra_voices:
                if not isinstance(v, dict):
                    continue
                model_path = v.get("model_path")
                if not model_path:
                    continue
                p = Path(model_path).expanduser()
                if not p.exists():
                    continue

                lang = str(v.get("language", "ru")).lower()
                if lang != self._target_language:
                    continue
                config_path = p.with_suffix(p.suffix + ".json")
                if not config_path.exists():
                    config_path = p.with_name(p.name + ".json")

                self._voices[p.stem] = VoiceConfig(
                    name=p.stem,
                    model_path=p,
                    config_path=config_path if config_path.exists() else p,
                    language=lang,
                    speaker_id=v.get("speaker_id", 0),
                    length_scale=v.get("length_scale", 1.0),
                    noise_scale=v.get("noise_scale", 0.667),
                    noise_w=v.get("noise_w", 0.8),
                )
                if not self._default_voice:
                    self._default_voice = p.stem

        # Авто-добавление известных голосов из data/models/piper/
        piper_dir = self._settings.models_dir / "piper"
        if piper_dir.exists():
            for onnx_file in piper_dir.glob("*.onnx"):
                if onnx_file.stem in self._voices:
                    continue
                config_path = onnx_file.with_suffix(".json")
                if not config_path.exists():
                    config_path = onnx_file.with_name(onnx_file.name + ".json")
                lang = self._model_language(config_path, onnx_file.stem)
                if lang != self._target_language:
                    continue

                self._voices[onnx_file.stem] = VoiceConfig(
                    name=onnx_file.stem,
                    model_path=onnx_file,
                    config_path=config_path if config_path.exists() else onnx_file,
                    language=lang,
                )
                if not self._default_voice:
                    self._default_voice = onnx_file.stem

    @staticmethod
    def _which(cmd: str) -> bool:
        """Проверяет наличие команды в PATH."""
        import shutil
        return shutil.which(cmd) is not None

    @staticmethod
    def _model_language(config_path: Path, stem: str = "") -> str:
        try:
            import json
            data = json.loads(config_path.read_text(encoding="utf-8"))
            language = data.get("language", {})
            code = language.get("family") or language.get("code")
            if code:
                return str(code).split("_")[0].split("-")[0].lower()
        except Exception:
            pass
        low = stem.lower()
        if low.startswith("ru_") or "dmitri" in low or "irina" in low:
            return "ru"
        if low.startswith("en_") or "jarvis" in low:
            return "en"
        return "unknown"

    @staticmethod
    def _config_has_tuning(config_path: Path) -> bool:
        """True, если .onnx.json модели сам задаёт noise/length-параметры.

        Если задаёт — уважаем их (пользователь явно настроил). Если нет —
        НЕ подставляем наши громкие дефолты (0.667/0.8), иначе голос
        искажается. Piper тогда возьмёт собственные родные значения модели.
        """
        try:
            import json
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            return False
        audio = data.get("audio") if isinstance(data, dict) else None
        if not isinstance(audio, dict):
            return False
        return any(k in audio for k in ("noise_scale", "length_scale", "noise_w"))

    def is_available(self) -> bool:
        """True, если piper бинарник и хотя бы одна модель найдены."""
        return self._available

    def _select_voice(self, text: str) -> Optional[VoiceConfig]:
        """Выбирает только configured Russian voice; input language irrelevant."""
        if not self._voices:
            return None
        selected_name = str(getattr(self._voice_settings, "voice", ""))
        if (selected_name in self._voices
                and self._voices[selected_name].language == self._target_language):
            return self._voices[selected_name]
        if self._default_voice and self._default_voice in self._voices:
            default = self._voices[self._default_voice]
            if default.language == self._target_language:
                return default
        if str(getattr(self._voice_settings, "fallback", "none")).lower() == "none":
            return None
        return next((v for v in self._voices.values()
                     if v.language == self._target_language), None)

    def synthesize_to_file(self, text: str, output_path: Path | str,
                           *, rate: float = 1.0, volume: float = 1.0) -> bool:
        """Генерирует WAV локальным Russian Piper без воспроизведения."""
        if not text or not text.strip() or not self._available:
            return False
        voice = self._select_voice(text)
        if voice is None or voice.language != self._target_language:
            log.warning("Piper synthesis skipped: compatible %s voice not found",
                        self._target_language)
            return False
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        adjusted_length = voice.length_scale / max(0.5, min(2.0, float(rate)))
        has_tuning = (
            voice.noise_scale > 0 or voice.noise_w > 0
            or abs(adjusted_length - 1.0) > 0.001
        )
        cmd = [
            str(self._binary), "--model", str(voice.model_path),
            "--speaker", str(voice.speaker_id), "--output_file", str(target),
        ]
        if has_tuning:
            cmd += ["--length_scale", str(adjusted_length)]
            if voice.noise_scale > 0:
                cmd += ["--noise_scale", str(voice.noise_scale)]
            if voice.noise_w > 0:
                cmd += ["--noise_w", str(voice.noise_w)]
        child_env = os.environ.copy()
        # Python Piper 1.3 reads redirected stdin using the active Windows code
        # page unless these flags are explicit. Sending UTF-8 bytes without the
        # matching decoder turns Russian text into mojibake ("РЎСЌ...").
        child_env["PYTHONIOENCODING"] = "utf-8"
        child_env["PYTHONUTF8"] = "1"
        try:
            proc = subprocess.run(
                cmd, input=(text.strip() + "\n").encode("utf-8"),
                capture_output=True, timeout=30, env=child_env, shell=False,
            )
        except subprocess.TimeoutExpired:
            log.error("Piper таймаут (>30s)")
            target.unlink(missing_ok=True)
            return False
        except Exception as exc:
            log.error("Piper synthesis ошибка: %s", exc)
            target.unlink(missing_ok=True)
            return False
        if proc.returncode != 0 or not target.exists() or target.stat().st_size == 0:
            log.error("Piper ошибка (code=%d): %s", proc.returncode,
                      proc.stderr.decode(errors="ignore"))
            target.unlink(missing_ok=True)
            return False
        self._apply_volume(target, volume)
        log.info("Piper WAV generated: provider=piper voice=%s language=%s rate=%s",
                 voice.name, voice.language, rate)
        return True

    @staticmethod
    def _apply_volume(path: Path, volume: float) -> None:
        """Scales Piper's 16-bit PCM WAV using only the standard library."""
        factor = max(0.0, min(1.0, float(volume)))
        if abs(factor - 1.0) < 0.001:
            return
        try:
            with wave.open(str(path), "rb") as source:
                params = source.getparams()
                frames = source.readframes(source.getnframes())
            if params.sampwidth != 2:
                log.warning("Piper volume control skipped: sample_width=%s", params.sampwidth)
                return
            samples = array("h")
            samples.frombytes(frames)
            for index, sample in enumerate(samples):
                samples[index] = max(-32768, min(32767, int(sample * factor)))
            temp_path = path.with_suffix(path.suffix + ".volume.tmp")
            with wave.open(str(temp_path), "wb") as target:
                target.setparams(params)
                target.writeframes(samples.tobytes())
            temp_path.replace(path)
        except Exception as exc:
            log.warning("Piper volume control skipped: %s", exc)

    def speak(self, text: str, blocking: bool = True, *, rate: float = 1.0,
              volume: float = 1.0) -> None:
        """Озвучивает уже отрендеренный текст локальным русским voice.

        Args:
            text: текст для озвучки.
            blocking: ждать окончания воспроизведения (True) или вернуть управление сразу.
        """
        if not text or not text.strip():
            log.debug("speak: пустой текст, пропуск")
            return

        if not self._available:
            log.warning("speak: Piper недоступен, текст не озвучен: %s", text[:60])
            return

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        tmp_path.unlink(missing_ok=True)
        if not self.synthesize_to_file(text, tmp_path, rate=rate, volume=volume):
            return
        if blocking:
            self._play_wav(tmp_path)
        else:
            threading.Thread(target=self._play_wav, args=(tmp_path,), daemon=True).start()

    def speak_rendered(self, rendered) -> None:
        """Typed queue-provider boundary used by :class:`TTSQueue`."""
        self.speak(rendered.text, blocking=True,
                   rate=rendered.rate, volume=rendered.volume)

    def _play_wav(self, path: Path) -> None:
        """Воспроизводит WAV через winsound (Windows) или удаляет файл после."""
        try:
            import winsound
            winsound.PlaySound(str(path), winsound.SND_FILENAME)
        except Exception:
            # Фоллбэк: просто ждём длительности (грубая оценка)
            try:
                with wave.open(str(path), "rb") as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    duration = frames / float(rate)
                time.sleep(duration + 0.2)
            except Exception:
                time.sleep(1)
        finally:
            # Удаляем временный файл
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass

    def stop_speaking(self) -> None:
        """Останавливает текущее воспроизведение (best effort).

        winsound не поддерживает остановку, поэтому просто логируем.
        Для полноценной остановки нужна отдельная очередь (см. tts_queue.py).
        """
        try:
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass
        log.debug("stop_speaking: playback purge requested")

    @property
    def available_voices(self) -> list[str]:
        """Список доступных голосов."""
        return list(self._voices.keys())

    @property
    def provider_info(self) -> dict[str, object]:
        selected = self._select_voice("")
        return {
            "provider": "piper",
            "local": True,
            "language": selected.language if selected else self._target_language,
            "voice": selected.name if selected else None,
            "fallback": str(getattr(self._voice_settings, "fallback", "none")),
            "available": self._available,
        }
