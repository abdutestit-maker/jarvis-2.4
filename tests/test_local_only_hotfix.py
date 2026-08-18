from config import load_config
from core.llm.factory import clear_backend_cache, get_llm_backend
from core.llm.local_qwen import LocalQwenBackend
from core.model_router import ModelRouter


def test_production_config_is_local_only():
    settings = load_config()
    assert settings.offline_mode is True
    assert settings.get_provider("analyst") == "local"
    assert all(not value for value in settings.api_keys.model_dump().values())


def test_offline_router_preserves_role_without_remote_escalation():
    settings = load_config()
    decision = ModelRouter(settings).route("проанализируй проект")
    assert decision.forced_local is True
    assert decision.tier.value == "analyst"
    assert decision.fallback_chain == []
    clear_backend_cache()
    backend = get_llm_backend(settings, "analyst")
    assert isinstance(backend, LocalQwenBackend)
    assert backend.task_role == "analyst"
    clear_backend_cache()
