from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.llm import hardware_profile


def test_recommend_profile_uses_strongest_safe_gpu_tier(tmp_path: Path):
    hw = hardware_profile.HardwareInfo(
        total_ram_gb=32,
        has_cuda_gpu=True,
        gpu_name="fixture-gpu",
        vram_total_gb=10,
    )
    profile = hardware_profile.recommend_profile(hw, models_dir=tmp_path)

    assert profile.core_model == "Qwen3-8B-Q5_K_M.gguf"
    assert profile.n_gpu_layers == -1
    assert profile.n_ctx == 8192
    assert profile.download_required is True


def test_apply_profile_only_switches_to_a_present_model(tmp_path: Path, monkeypatch):
    model = tmp_path / "qwen3-4b-instruct-q5_k_m.gguf"
    model.write_bytes(b"fixture")
    monkeypatch.setattr(
        hardware_profile,
        "detect_hardware",
        lambda: hardware_profile.HardwareInfo(total_ram_gb=16, vram_total_gb=8),
    )

    class Local:
        gguf_path = "data/models/Qwen3-1.7B-Q6_K.gguf"
        auto_profile = True
        n_gpu_layers = 0
        n_ctx = 4096
        n_batch = 512

        @property
        def resolved_gguf_path(self):
            return Path(self.gguf_path)

    settings = SimpleNamespace(models_dir=tmp_path, local_model=Local())
    profile = hardware_profile.apply_profile(settings)

    assert profile.core_model == "qwen3-4b-instruct-q5_k_m.gguf"
    assert settings.local_model.gguf_path == "data/models/qwen3-4b-instruct-q5_k_m.gguf"
    assert settings.local_model.n_ctx == 8192


def test_apply_profile_keeps_existing_path_when_target_is_missing(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        hardware_profile,
        "detect_hardware",
        lambda: hardware_profile.HardwareInfo(total_ram_gb=32, vram_total_gb=24),
    )

    class Local:
        gguf_path = "data/models/existing.gguf"
        auto_profile = True

        @property
        def resolved_gguf_path(self):
            return Path(self.gguf_path)

    settings = SimpleNamespace(models_dir=tmp_path, local_model=Local())
    profile = hardware_profile.apply_profile(settings)

    assert profile.core_model == "Qwen3-14B-Q4_K_M.gguf"
    assert settings.local_model.gguf_path == "data/models/existing.gguf"
    assert any("текущий GGUF сохранён" in reason for reason in profile.reasons)
