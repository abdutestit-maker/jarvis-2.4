from __future__ import annotations

import json

import pytest

from core.brain import (
    BrainProviderConfigurator,
    BrainConfigStore,
    BrainRole,
    MemorySecretStore,
    ModelCapabilityProfile,
    ProviderConfig,
    DPAPISecretStore,
)


def _provider(base_url: str = "http://127.0.0.1:1234/v1") -> ProviderConfig:
    return ProviderConfig(
        name="custom", protocol="openai_compatible", base_url=base_url,
        api_key_ref="custom-secret", external=False,
        models=(ModelCapabilityProfile(
            model="local-gateway", roles=frozenset({BrainRole.CHAT}), local=True,
        ),),
    )


def test_provider_config_persists_reference_never_secret(tmp_path):
    path = tmp_path / "providers.json"
    secret = "sk-test-do-not-persist"
    store = BrainConfigStore(path)
    store.save((_provider(),))
    MemorySecretStore({"custom-secret": secret})

    raw = path.read_text(encoding="utf-8")
    assert secret not in raw
    assert "custom-secret" in raw
    assert "api_key\"" not in raw
    assert json.loads(raw)["providers"][0]["api_key_ref"] == "custom-secret"


def test_plaintext_api_key_in_provider_json_is_rejected(tmp_path):
    path = tmp_path / "providers.json"
    path.write_text(json.dumps({
        "providers": [{
            "name": "bad", "protocol": "openai_compatible",
            "base_url": "http://127.0.0.1:1/v1", "api_key": "plaintext",
            "models": [],
        }],
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="api_key_ref"):
        BrainConfigStore(path).load()


def test_hot_reload_changes_generation_only_and_redacts_snapshot(tmp_path):
    path = tmp_path / "providers.json"
    store = BrainConfigStore(path)
    store.save((_provider("http://127.0.0.1:1111/v1"),))
    first = store.load()
    generation = store.generation

    store.save((_provider("http://127.0.0.1:2222/v1"),))
    second = store.reload_if_changed()

    assert first[0].base_url.endswith("1111/v1")
    assert second[0].base_url.endswith("2222/v1")
    assert store.generation == generation + 1
    assert '"api_key":' not in json.dumps(second[0].public_dict())


def test_dpapi_secret_store_encrypts_at_rest_and_reopens(tmp_path):
    path = tmp_path / "provider-secrets.dpapi"
    secret = "sk-sensitive-test-value"
    store = DPAPISecretStore(path)
    store.set("custom-key", secret)

    assert secret.encode() not in path.read_bytes()
    assert DPAPISecretStore(path).get("custom-key") == secret


def test_custom_provider_configurator_persists_model_but_not_key(tmp_path):
    config_path = tmp_path / "providers.json"
    secret_path = tmp_path / "secrets.dpapi"
    configurator = BrainProviderConfigurator(
        BrainConfigStore(config_path), DPAPISecretStore(secret_path),
    )
    configurator.upsert_openai_compatible(
        name="studio", base_url="http://127.0.0.1:1234/v1",
        api_key="local-key", model="qwen-local", roles=(BrainRole.CHAT,),
    )

    text = config_path.read_text(encoding="utf-8")
    assert "qwen-local" in text
    assert "local-key" not in text
    assert DPAPISecretStore(secret_path).get("provider:studio") == "local-key"
