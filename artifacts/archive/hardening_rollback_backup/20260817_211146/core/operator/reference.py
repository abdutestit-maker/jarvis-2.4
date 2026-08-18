"""Reference → desired state, including adaptive local video analysis."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class InterpretedReference:
    application: str
    desired_state: dict[str, Any]
    source_type: str
    steps: list[str] = field(default_factory=list)
    observed_settings: dict[str, Any] = field(default_factory=dict)
    uncertain_items: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VideoReferenceResult:
    source: str
    metadata: dict[str, Any]
    keyframes: list[Path]
    transcript: str
    steps: list[str]
    observed_settings: dict[str, Any]
    uncertain_items: list[str]
    desired_state: dict[str, Any]


class VideoReferenceProvider:
    """Extracts scene keyframes/transcript and delegates bounded frame analysis."""

    def __init__(self, *, frame_analyzer: Callable[[list[Path], str], dict[str, Any]] | None = None,
                 transcriber: Callable[[Path], str] | None = None, max_keyframes: int = 12) -> None:
        self.frame_analyzer = frame_analyzer
        self.transcriber = transcriber
        self.max_keyframes = max(1, int(max_keyframes))

    def analyze(self, source: Path | str, *, output_dir: Path | str | None = None) -> VideoReferenceResult:
        video, source_label = self._materialize(source)
        target = Path(output_dir or Path(tempfile.mkdtemp(prefix="jarvis-video-reference-")))
        target.mkdir(parents=True, exist_ok=True)
        metadata, streams = self._metadata(video)
        keyframes = self._keyframes(video, target, float(metadata.get("duration_seconds", 0)))
        transcript = self._transcript(video, target, streams)
        analysis: dict[str, Any] = {}
        if self.frame_analyzer is not None:
            analysis = dict(self.frame_analyzer(keyframes, transcript) or {})
        uncertain = list(analysis.get("uncertain_items") or [])
        if self.frame_analyzer is None:
            uncertain.append("frame_analysis_unavailable")
        return VideoReferenceResult(
            source=source_label,
            metadata=metadata,
            keyframes=keyframes,
            transcript=transcript,
            steps=list(analysis.get("steps") or []),
            observed_settings=dict(analysis.get("observed_settings") or {}),
            uncertain_items=uncertain,
            desired_state=dict(analysis.get("desired_state") or {}),
        )

    @staticmethod
    def _materialize(source: Path | str) -> tuple[Path, str]:
        text = str(source)
        parsed = urllib.parse.urlparse(text)
        if parsed.scheme in {"http", "https"}:
            if parsed.scheme != "https":
                raise ValueError("reference URL must use HTTPS")
            from core.network_guard import assert_safe_url
            assert_safe_url(text)
            suffix = Path(parsed.path).suffix or ".mp4"
            target = Path(tempfile.mkdtemp(prefix="jarvis-reference-download-")) / f"reference{suffix}"
            request = urllib.request.Request(text, headers={"User-Agent": "JARVIS/0.1"})
            with urllib.request.urlopen(request, timeout=120) as response, target.open("wb") as stream:
                remaining = 5 * 1024 * 1024
                while remaining > 0:
                    chunk = response.read(min(64 * 1024, remaining + 1))
                    if not chunk:
                        break
                    if len(chunk) > remaining:
                        raise ValueError("reference exceeds 5 MB limit")
                    stream.write(chunk)
                    remaining -= len(chunk)
            return target, text
        path = Path(text).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        return path, str(path)

    @staticmethod
    def _metadata(video: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        done = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration:stream=index,codec_type,codec_name,width,height,avg_frame_rate",
            "-of", "json", str(video),
        ], capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60, check=False, shell=False)
        if done.returncode != 0:
            raise RuntimeError(done.stderr.strip() or "ffprobe failed")
        data = json.loads(done.stdout)
        streams = list(data.get("streams") or [])
        video_stream = next((item for item in streams if item.get("codec_type") == "video"), {})
        rate = str(video_stream.get("avg_frame_rate", "0/1"))
        numerator, _, denominator = rate.partition("/")
        fps = float(numerator or 0) / max(1.0, float(denominator or 1))
        return {
            "duration_seconds": float(data.get("format", {}).get("duration", 0) or 0),
            "width": int(video_stream.get("width", 0) or 0),
            "height": int(video_stream.get("height", 0) or 0),
            "fps": round(fps, 3),
            "codec": str(video_stream.get("codec_name", "")),
        }, streams

    def _keyframes(self, video: Path, target: Path, duration: float) -> list[Path]:
        pattern = target / "scene_%03d.jpg"
        done = subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-i", str(video),
            "-vf", "select='eq(n,0)+gt(scene,0.25)'", "-vsync", "vfr",
            "-frames:v", str(self.max_keyframes), str(pattern),
        ], capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120, check=False, shell=False)
        frames = sorted(target.glob("scene_*.jpg"))
        if done.returncode == 0 and frames:
            return frames[:self.max_keyframes]
        interval = max(0.25, duration / max(1, min(self.max_keyframes, 6)))
        fallback = target / "sample_%03d.jpg"
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-i", str(video),
            "-vf", f"fps=1/{interval}", "-frames:v", str(self.max_keyframes), str(fallback),
        ], capture_output=True, timeout=120, check=False, shell=False)
        return sorted(target.glob("sample_*.jpg"))[:self.max_keyframes]

    def _transcript(self, video: Path, target: Path, streams: list[dict[str, Any]]) -> str:
        if any(item.get("codec_type") == "subtitle" for item in streams):
            subtitle = target / "subtitle.srt"
            done = subprocess.run([
                "ffmpeg", "-y", "-v", "error", "-i", str(video), "-map", "0:s:0", str(subtitle),
            ], capture_output=True, timeout=60, check=False, shell=False)
            if done.returncode == 0 and subtitle.is_file():
                return subtitle.read_text(encoding="utf-8", errors="replace").strip()
        if self.transcriber is not None:
            return str(self.transcriber(video) or "").strip()
        return ""


class ReferenceInterpreter:
    """Converts video/image/web/text/structured evidence into state, never clicks."""

    _video_suffixes = {".mp4", ".mkv", ".mov", ".webm", ".avi"}
    _image_suffixes = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}

    def __init__(self, video: VideoReferenceProvider | None = None, *,
                 image_analyzer: Callable[[Path], dict[str, Any]] | None = None,
                 web_loader: Callable[[str], str] | None = None) -> None:
        self.video = video or VideoReferenceProvider()
        self.image_analyzer = image_analyzer
        self.web_loader = web_loader or self._load_web

    def interpret(self, reference: Any) -> InterpretedReference:
        if isinstance(reference, dict):
            source_type = str(reference.get("type", "structured"))
            if source_type == "video" and reference.get("source"):
                return self._from_video(reference["source"], application=str(reference.get("application", "")))
            desired = dict(reference.get("desired_state") or reference.get("settings") or {})
            desired.pop("clicks", None)
            return InterpretedReference(
                application=str(reference.get("application", "")),
                desired_state=desired,
                source_type=source_type,
                steps=list(reference.get("steps") or []),
                observed_settings=dict(reference.get("observed_settings") or desired),
                uncertain_items=list(reference.get("uncertain_items") or []),
            )
        path = Path(str(reference)).expanduser()
        if path.is_file():
            if path.suffix.casefold() in self._video_suffixes:
                return self._from_video(path)
            if path.suffix.casefold() in self._image_suffixes:
                return self._from_image(path.resolve())
            text = path.read_text(encoding="utf-8", errors="replace")
            return self._from_text(text, source_type=path.suffix.casefold().lstrip(".") or "text")
        text = str(reference)
        parsed = urllib.parse.urlparse(text)
        if parsed.scheme == "https":
            suffix = Path(parsed.path).suffix.casefold()
            if suffix in self._video_suffixes:
                return self._from_video(text)
            if suffix in self._image_suffixes:
                return self._from_image(self._download_image(text), source=text)
            interpreted = self._from_text(self.web_loader(text), source_type="web")
            return InterpretedReference(
                interpreted.application, interpreted.desired_state, "web",
                interpreted.steps, interpreted.observed_settings,
                interpreted.uncertain_items, {"source": text},
            )
        return self._from_text(text, source_type="text")

    def _from_video(self, source: Path | str, *, application: str = "") -> InterpretedReference:
        result = self.video.analyze(source)
        return InterpretedReference(
            application=application,
            desired_state=result.desired_state,
            source_type="video",
            steps=result.steps,
            observed_settings=result.observed_settings,
            uncertain_items=result.uncertain_items,
            evidence={"metadata": result.metadata, "keyframes": [str(path) for path in result.keyframes],
                      "transcript": result.transcript},
        )

    def _from_image(self, path: Path, *, source: str = "") -> InterpretedReference:
        analysis = dict(self.image_analyzer(path) or {}) if self.image_analyzer is not None else {}
        uncertain = list(analysis.get("uncertain_items") or [])
        if self.image_analyzer is None:
            uncertain.append("image_analysis_unavailable")
        return InterpretedReference(
            application=str(analysis.get("application", "")),
            desired_state=dict(analysis.get("desired_state") or {}),
            source_type="image",
            steps=list(analysis.get("steps") or []),
            observed_settings=dict(analysis.get("observed_settings") or {}),
            uncertain_items=uncertain,
            evidence={"source": source or str(path)},
        )

    @staticmethod
    def _load_web(url: str) -> str:
        from core.network_guard import assert_safe_url
        assert_safe_url(url)
        request = urllib.request.Request(url, headers={"User-Agent": "JARVIS/0.1"})
        with urllib.request.urlopen(request, timeout=60) as response:
            content_type = str(response.headers.get("Content-Type", "")).casefold()
            if content_type and not any(kind in content_type for kind in ("text/", "json", "xml")):
                raise ValueError(f"web reference is not text: {content_type}")
            payload = response.read(2_000_001)
            if len(payload) > 2_000_000:
                raise ValueError("web reference exceeds 2 MB")
            charset = response.headers.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")

    @staticmethod
    def _download_image(url: str) -> Path:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https":
            raise ValueError("image reference URL must use HTTPS")
        from core.network_guard import assert_safe_url
        assert_safe_url(url)
        suffix = Path(parsed.path).suffix.casefold()
        target = Path(tempfile.mkdtemp(prefix="jarvis-image-reference-")) / f"reference{suffix}"
        request = urllib.request.Request(url, headers={"User-Agent": "JARVIS/0.1"})
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read(10_000_001)
            if len(payload) > 10_000_000:
                raise ValueError("image reference exceeds 10 MB")
            target.write_bytes(payload)
        return target

    @classmethod
    def _from_text(cls, text: str, *, source_type: str) -> InterpretedReference:
        application = ""
        desired: dict[str, Any] = {}
        steps: list[str] = []
        for raw in text.splitlines():
            line = raw.strip().lstrip("-* ")
            if not line:
                continue
            steps.append(line)
            match = re.match(r"^([\w .-]+)\s*[:=]\s*(.+)$", line, re.UNICODE)
            if not match:
                continue
            key = re.sub(r"\s+", "_", match.group(1).strip().casefold())
            value = cls._coerce(match.group(2).strip())
            if key in {"application", "app", "приложение"}:
                application = str(value)
            elif key not in {"click", "clicks", "coordinates", "координаты"}:
                desired[key] = value
        if not desired and text.strip():
            return InterpretedReference(application, {}, source_type, steps,
                                        uncertain_items=["desired_state_not_explicit"])
        return InterpretedReference(application, desired, source_type, steps,
                                    observed_settings=dict(desired))

    @staticmethod
    def _coerce(value: str) -> Any:
        low = value.casefold()
        if low in {"true", "yes", "on", "enabled", "да", "вкл", "включено"}:
            return True
        if low in {"false", "no", "off", "disabled", "нет", "выкл", "отключено"}:
            return False
        if re.fullmatch(r"[-+]?\d+", value):
            return int(value)
        if re.fullmatch(r"[-+]?\d+\.\d+", value):
            return float(value)
        return value


@dataclass(frozen=True)
class DesiredStateDiff:
    changes: dict[str, dict[str, Any]]
    matches: list[str]

    @classmethod
    def between(cls, current: dict[str, Any], desired: dict[str, Any]) -> "DesiredStateDiff":
        changes: dict[str, dict[str, Any]] = {}
        matches: list[str] = []

        def compare(actual: dict[str, Any], expected: dict[str, Any], prefix: str = "") -> None:
            for key, wanted in expected.items():
                path = f"{prefix}.{key}" if prefix else key
                observed = actual.get(key)
                if isinstance(wanted, dict) and isinstance(observed, dict):
                    compare(observed, wanted, path)
                elif observed == wanted:
                    matches.append(path)
                else:
                    changes[path] = {"current": observed, "desired": wanted}

        compare(current, desired)
        return cls(changes=changes, matches=sorted(matches))
