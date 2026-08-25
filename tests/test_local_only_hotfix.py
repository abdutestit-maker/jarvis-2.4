from config import load_config
from core.llm.factory import clear_backend_cache, get_llm_backend
from core.llm.local_qwen import LocalQwenBackend
from core.model_router import ModelRouter


def test_production_config_is_deepseek_only():
    settings = load_config()
    assert settings.offline_mode is False
    assert settings.deepseek_brain_mode is True
    assert settings.get_provider("analyst") == "deepinfra"
    assert all(not value for value in settings.api_keys.model_dump().values())


def test_deepseek_router_preserves_single_remote_brain():
    settings = load_config()
    from core.brain.bootstrap import build_brain_fabric
    decision = ModelRouter(settings, brain_fabric=build_brain_fabric(settings)).route("проанализируй проект")
    assert decision.forced_local is False
    assert decision.provider == "deepinfra" or decision.brain_route.primary.provider == "deepinfra"
    assert decision.model == "deepseek-ai/DeepSeek-V4-Flash-0731" or decision.brain_route.primary.model == "deepseek-ai/DeepSeek-V4-Flash-0731"
    assert decision.fallback_chain == []
