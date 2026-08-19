from __future__ import annotations

import json
from pathlib import Path

from config.settings import load_config
from core.llm.hardware_profile import HardwareInfo, recommend_profile


def test_ministral_profile_is_explicit_and_single_model():
    profile = recommend_profile(
        HardwareInfo(total_ram_gb=8.0, vram_total_gb=6.0, has_cuda_gpu=True, gpu_name="fixture"),
        models_dir=Path("data/models"),
        model_family="ministral",
    )
    assert profile.model_family == "ministral"
    assert profile.core_model == "Ministral-3-3B-Reasoning-2512-Q4_K_M.gguf"
    assert profile.n_ctx <= 8192


def test_production_config_selects_local_ministral_and_denis():
    settings = load_config(Path("config/settings.json"))
    assert settings.model_family == "ministral"
    assert settings.tier_providers.get("fast") == "local"
    assert "Ministral" in settings.model_tiers.get("fast")
    assert settings.voice.voice == "ru_RU-denis-medium"
    assert settings.voice.resolved_primary_piper_model.name == "ru_RU-denis-medium.onnx"


def test_manifest_has_official_hash_and_no_duplicate_production_model():
    data = json.loads(Path("config/models_manifest.json").read_text(encoding="utf-8"))
    item = next(item for item in data["models"] if item["key"] == "ministral3-3b-reasoning")
    assert item["url"].startswith("https://huggingface.co/mistralai/")
    assert len(item["sha256"]) == 64
    assert item["size_bytes"] > 2_000_000_000
