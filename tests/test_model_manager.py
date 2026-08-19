from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

from core.utils.model_manager import ModelArtifact, ModelDownloadError, ModelManager


def _settings(tmp_path: Path):
    return SimpleNamespace(models_dir=tmp_path / "models", source_path=None)


def test_repository_manifest_is_pinned_and_valid():
    manager = ModelManager(_settings(Path(".")))
    manifest = manager.load_model_manifest()

    assert {"qwen3-0.6b", "qwen3-1.7b", "qwen3-4b", "qwen3-8b", "qwen3-14b"} <= set(manifest)
    assert all(item.url.startswith("https://huggingface.co/") for item in manifest.values())
    assert all(len(item.sha256) == 64 and item.size_bytes > 0 for item in manifest.values())


def test_existing_artifact_is_verified_without_network(tmp_path: Path):
    payload = b"fixture-gguf"
    digest = hashlib.sha256(payload).hexdigest()
    artifact = ModelArtifact("fixture", "fixture.gguf", "https://huggingface.co/fixture", len(payload), digest)
    target = tmp_path / "models" / artifact.filename
    target.parent.mkdir()
    target.write_bytes(payload)
    manager = ModelManager(_settings(tmp_path))
    manager._ensure_artifact(artifact, target, progress=None, cancel=None, timeout_sec=1)
    assert target.read_bytes() == payload


def test_invalid_download_is_removed_after_hash_mismatch(tmp_path: Path, monkeypatch):
    payload = b"fixture-gguf"
    artifact = ModelArtifact(
        "fixture", "fixture.gguf", "https://huggingface.co/fixture", len(payload), "0" * 64,
    )
    target = tmp_path / "models" / artifact.filename
    manager = ModelManager(_settings(tmp_path))

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, _size: int):
            nonlocal payload
            value, payload = payload, b""
            return value

    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: Response())
    try:
        manager._ensure_artifact(artifact, target, progress=None, cancel=None, timeout_sec=1)
    except ModelDownloadError:
        pass
    else:
        raise AssertionError("hash mismatch must fail the model install")
    assert not target.exists()
    assert not target.with_name(target.name + ".part").exists()
