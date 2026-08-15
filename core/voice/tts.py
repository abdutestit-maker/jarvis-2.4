"""Text-to-Speech через Piper (локальный, быстрый, качественный).

``PiperTTS`` поддерживает несколько голосов и выбирает их по языку текста:
- Английский (en) -> Jarvis voice (en_GB)
- Русский (ru) -> irina voice (ru_RU)
- Другие -> fallback на ru голос

Если piper_binary_path / piper_model_path не найдены — ``is_available()`` = False,
``speak()`` логирует warning и не падает (текстовый режим остаётся рабочим).
"""

from __future__ import annotations

import re
import subprocess
import tempfile
import threading
import time
import wave
from pathlib import Path
from typing import Optional

from config.settings import Settings
from core.utils.logger import get_logger

__all__ = ["PiperTTS"]

log = get_logger(__name__)

# Регулярка для определения кириллицы
_CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")


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
        self._binary = self._resolve_binary()

        # Загружаем конфигурацию голосов
        self._voices: dict[str, VoiceConfig] = {}
        self._default_voice: Optional[str] = None
        self._load_voices()

        self._available = self._binary is not None and len(self._voices) > 0

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
        """Находит piper исполняемый файл."""
        voice = getattr(self._settings, "voice", None)
        if voice and getattr(voice, "piper_binary_path", None):
            p = Path(voice.piper_binary_path).expanduser()
            if p.exists():
                return p

        # Стандартные места установки
        candidates = [
            Path("piper.exe"),  # в PATH
            Path.home() / ".local" / "bin" / "piper.exe",
            Path("C:/Program Files/piper/piper.exe"),
            Path("C:/Program Files (x86)/piper/piper.exe"),
        ]
        for c in candidates:
            try:
                if c.exists() or (c.name == "piper.exe" and self._which("piper")):
                    return c
            except Exception:
                pass
        return None

    def _load_voices(self) -> None:
        """Загружает конфигурацию голосов из settings."""
        voice_cfg = getattr(self._settings, "voice", None)
        if not voice_cfg:
            return

        # Основной голос (для обратной совместимости)
        main_model = getattr(voice_cfg, "resolved_piper_model", None)
        if main_model and main_model.exists():
            # Определяем язык по имени файла
            lang = "ru"  # дефолт
            if "jarvis" in main_model.stem.lower():
                lang = "en"
            elif "irina" in main_model.stem.lower():
                lang = "ru"

            config_path = main_model.with_suffix(main_model.suffix + ".json")
            if not config_path.exists():
                # Попробуем найти .onnx.json
                config_path = main_model.with_name(main_model.name + ".json")

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

                lang = v.get("language", "ru")
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
                # Определяем язык по имени
                lang = "ru"
                if "jarvis" in onnx_file.stem.lower():
                    lang = "en"
                elif "irina" in onnx_file.stem.lower():
                    lang = "ru"

                config_path = onnx_file.with_suffix(".json")
                if not config_path.exists():
                    config_path = onnx_file.with_name(onnx_file.name + ".json")

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
        """Выбирает голос по языку текста."""
        if not self._voices:
            return None

        # Определяем язык текста
        has_cyrillic = bool(_CYRILLIC_RE.search(text))
        lang = "ru" if has_cyrillic else "en"

        # Ищем голос для языка
        for voice in self._voices.values():
            if voice.language == lang:
                return voice

        # Fallback на дефолтный
        if self._default_voice and self._default_voice in self._voices:
            return self._voices[self._default_voice]

        # Любой доступный
        return next(iter(self._voices.values()))

    def speak(self, text: str, blocking: bool = True) -> None:
        """Озвучивает текст, выбирая голос по языку.

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

        voice = self._select_voice(text)
        if not voice:
            log.warning("speak: нет доступных голосов")
            return

        # Передаём Piper параметры тюнинга ТОЛЬКО если они заданы (>0).
        # Если noise_scale/length_scale == 0 — значит модель сама знает свои
        # родные значения из .onnx.json, и мы НЕ переопределяем их (это
        # предотвращает искажение/«garbled» звук).
        has_tuning = (voice.noise_scale > 0) or (voice.noise_w > 0) or (voice.length_scale != 1.0)

        log.debug("speak: voice=%s, lang=%s, text=%s", voice.name, voice.language, text[:50])

        # Генерируем WAV во временный файл
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = Path(tmp.name)

            cmd = [
                str(self._binary),
                "--model", str(voice.model_path),
                "--speaker", str(voice.speaker_id),
                "--output_file", str(tmp_path),
            ]
            if has_tuning:
                cmd += [
                    "--length_scale", str(voice.length_scale),
                    "--noise_scale", str(voice.noise_scale),
                    "--noise_w", str(voice.noise_w),
                ]

            # Piper читает текст из stdin
            proc = subprocess.run(
                cmd,
                input=text.strip().encode("utf-8"),
                capture_output=True,
                timeout=30,
            )

            if proc.returncode != 0:
                log.error("Piper ошибка (code=%d): %s", proc.returncode, proc.stderr.decode(errors="ignore"))
                tmp_path.unlink(missing_ok=True)
                return

            # Воспроизводим
            if blocking:
                self._play_wav(tmp_path)
            else:
                threading.Thread(target=self._play_wav, args=(tmp_path,), daemon=True).start()

        except subprocess.TimeoutExpired:
            log.error("Piper таймаут (>30s)")
        except Exception as exc:
            log.error("Piper speak ошибка: %s", exc)

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
        log.debug("stop_speaking: запрос остановки (winsound не поддерживает прерывание)")

    @property
    def available_voices(self) -> list[str]:
        """Список доступных голосов."""
        return list(self._voices.keys())