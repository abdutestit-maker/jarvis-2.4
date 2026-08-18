"""Reference interpretation, video foundation, state diff and foreground tests."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

from core.operator.reference import DesiredStateDiff, ReferenceInterpreter, VideoReferenceProvider
from core.operator.session import ForegroundClass, ForegroundSession


def test_reference_interpreter_extracts_state_and_never_replays_clicks() -> None:
    result = ReferenceInterpreter().interpret({
        "type": "text",
        "application": "Fixture App",
        "settings": {"theme": "Dark", "auto_update": False},
        "clicks": [{"x": 10, "y": 20}],
    })

    assert result.application == "Fixture App"
    assert result.desired_state == {"theme": "Dark", "auto_update": False}
    assert "clicks" not in result.desired_state


def test_text_reference_extracts_typed_key_value_desired_state() -> None:
    result = ReferenceInterpreter().interpret(
        "application: Fixture App\n"
        "theme: Dark\n"
        "autosave: true\n"
        "tab_size: 4\n"
    )

    assert result.application == "Fixture App"
    assert result.desired_state == {"theme": "Dark", "autosave": True, "tab_size": 4}


def test_image_reference_uses_bounded_analyzer_and_returns_desired_state(tmp_path: Path) -> None:
    image = tmp_path / "settings.png"
    image.write_bytes(b"fixture-image")

    def analyze(path: Path):
        assert path == image.resolve()
        return {
            "steps": ["Open editor preferences"],
            "observed_settings": {"theme": "Dark"},
            "desired_state": {"theme": "Dark"},
            "uncertain_items": [],
        }

    result = ReferenceInterpreter(image_analyzer=analyze).interpret(image)

    assert result.source_type == "image"
    assert result.desired_state == {"theme": "Dark"}
    assert result.evidence["source"] == str(image.resolve())


def test_https_reference_uses_web_loader_as_data() -> None:
    result = ReferenceInterpreter(
        web_loader=lambda url: "application: Fixture App\nword_wrap: true\n",
    ).interpret("https://docs.example/reference")

    assert result.source_type == "web"
    assert result.application == "Fixture App"
    assert result.desired_state == {"word_wrap": True}
    assert result.evidence["source"] == "https://docs.example/reference"


def test_current_to_desired_diff_contains_only_changed_nested_values() -> None:
    diff = DesiredStateDiff.between(
        {"theme": "Light", "editor": {"tab_size": 4, "wrap": False}, "locale": "ru"},
        {"theme": "Dark", "editor": {"tab_size": 4, "wrap": True}, "locale": "ru"},
    )

    assert diff.changes == {
        "theme": {"current": "Light", "desired": "Dark"},
        "editor.wrap": {"current": False, "desired": True},
    }
    assert diff.matches == ["editor.tab_size", "locale"]


def test_video_provider_extracts_real_metadata_keyframes_and_analyzed_state(tmp_path: Path) -> None:
    video = tmp_path / "reference.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", "color=c=red:s=320x240:d=1:r=10",
        "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=1:r=10",
        "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0",
        "-c:v", "mpeg4", str(video),
    ], check=True, timeout=30)

    def analyzer(frames: list[Path], transcript: str):
        assert frames
        assert transcript == ""
        return {
            "steps": ["Open settings", "Select dark theme"],
            "observed_settings": {"theme": "Dark"},
            "desired_state": {"theme": "Dark"},
            "uncertain_items": [],
        }

    result = VideoReferenceProvider(frame_analyzer=analyzer).analyze(video, output_dir=tmp_path / "out")

    assert 1.9 <= result.metadata["duration_seconds"] <= 2.1
    assert result.metadata["width"] == 320
    assert result.keyframes
    assert all(path.is_file() for path in result.keyframes)
    assert result.desired_state == {"theme": "Dark"}
    assert result.steps[-1] == "Select dark theme"


class _ForegroundLayer:
    def __init__(self) -> None:
        self.focused = []

    def window_active(self):
        return SimpleNamespace(ok=True, value={"handle": 10, "title": "User App"})

    def window_focus(self, **kwargs):
        self.focused.append(kwargs)
        return SimpleNamespace(ok=True, value={"focused": True})


def test_foreground_session_restores_previous_user_window() -> None:
    layer = _ForegroundLayer()

    with ForegroundSession(layer, classification=ForegroundClass.FOREGROUND_REQUIRED,
                           target_title="Fixture App") as session:
        assert session.acquired is True

    assert layer.focused == [{"title": "Fixture App"}, {"handle": 10}]
    assert session.restored is True
