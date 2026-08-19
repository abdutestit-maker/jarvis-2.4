"""Regression coverage for the portable runtime and first-request readiness."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from types import SimpleNamespace

from core.orchestrator import Orchestrator


def _orchestrator_stub(*, ready: bool, state: str) -> Orchestrator:
    orchestrator = Orchestrator.__new__(Orchestrator)
    orchestrator._settings = SimpleNamespace(
        warmup_local_on_start=True,
        server_start_timeout_sec=0.2,
    )
    orchestrator._warmup_ready = threading.Event()
    orchestrator._warmup_diagnostics = {"state": state}
    if ready:
        orchestrator._warmup_ready.set()
    return orchestrator


def test_runtime_readiness_returns_ready_without_sleeping() -> None:
    orchestrator = _orchestrator_stub(ready=True, state="ready")

    assert orchestrator.wait_for_runtime_ready(timeout=0.01) == "ready"


def test_runtime_readiness_reports_unavailable_after_timeout() -> None:
    orchestrator = _orchestrator_stub(ready=False, state="unavailable")

    assert orchestrator.wait_for_runtime_ready(timeout=0.01) == "unavailable"


def test_packaged_config_is_local_voice_and_silent_on_start() -> None:
    config_path = Path("jarvis/src-tauri/resources/jarvis-runtime/config/settings.json")
    data = json.loads(config_path.read_text(encoding="utf-8"))

    assert data["launcher"]["backend_command"] == ["runtime/jarvis-backend.exe"]
    assert data["launcher"]["greeting_enabled"] is False
    assert data["voice"]["tts_enabled"] is True
    assert data["voice"]["provider"] == "piper"
    assert data["voice"]["language"] == "ru"
    assert data["voice"]["piper_binary_path"] == "runtime/piper/piper.exe"
    assert data["voice"]["piper_model_path"].endswith("ru_RU-dmitri-medium.onnx")


def test_portable_installer_builder_declares_bundled_model_and_voice() -> None:
    builder = Path("scripts/build_portable_installer.py").read_text(encoding="utf-8")

    assert "jarvis-backend.exe" in builder
    assert "runtime/piper/piper.exe" in builder
    assert "qwen3-4b-instruct-q5_k_m.gguf" in builder
    assert "7z.sfx" in builder
