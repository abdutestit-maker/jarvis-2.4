"""Atomic provider metadata storage with deterministic hot reload."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from core.security.atomic import atomic_json_write

from .models import BrainRole, ModelCapabilityProfile, ProviderConfig
from .secrets import SecretStore


class BrainConfigStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.generation = 0
        self._digest = ""
        self._current: tuple[ProviderConfig, ...] = ()

    def save(self, providers: tuple[ProviderConfig, ...] | list[ProviderConfig]) -> Path:
        return atomic_json_write(self.path, {
            "version": 1,
            "providers": [provider.public_dict() for provider in providers],
        })

    def _bytes(self) -> bytes:
        try:
            return self.path.read_bytes()
        except FileNotFoundError:
            return b'{"version":1,"providers":[]}'

    def load(self) -> tuple[ProviderConfig, ...]:
        raw = self._bytes()
        payload = json.loads(raw.decode("utf-8-sig"))
        providers_raw = payload.get("providers", []) if isinstance(payload, dict) else []
        if not isinstance(providers_raw, list):
            raise ValueError("providers must be a list")
        providers = tuple(self._parse_provider(item) for item in providers_raw)
        self._current = providers
        self._digest = hashlib.sha256(raw).hexdigest()
        self.generation += 1
        return providers

    def reload_if_changed(self) -> tuple[ProviderConfig, ...]:
        raw = self._bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest == self._digest:
            return self._current
        return self.load()

    @staticmethod
    def _parse_provider(value: Any) -> ProviderConfig:
        if not isinstance(value, dict):
            raise ValueError("provider must be an object")
        if value.get("api_key") not in (None, ""):
            raise ValueError("plaintext api_key is forbidden; use api_key_ref")
        models = []
        for raw in value.get("models", []):
            if not isinstance(raw, dict):
                raise ValueError("model must be an object")
            try:
                roles = frozenset(BrainRole(str(item).upper()) for item in raw.get("roles", []))
            except ValueError as exc:
                raise ValueError(f"unknown brain role: {exc}") from exc
            models.append(ModelCapabilityProfile(
                model=str(raw.get("model", "")).strip(), roles=roles,
                streaming=bool(raw.get("streaming", False)),
                structured_output=bool(raw.get("structured_output", False)),
                tool_calling=bool(raw.get("tool_calling", False)),
                vision=bool(raw.get("vision", False)),
                context_window=max(1, int(raw.get("context_window", 4096))),
                local=bool(raw.get("local", not bool(value.get("external", True)))),
                cost_tier=max(0, int(raw.get("cost_tier", 0))),
                tested=frozenset(str(item) for item in raw.get("tested", [])),
                metadata=dict(raw.get("metadata", {})),
            ))
        return ProviderConfig(
            name=str(value.get("name", "")).strip(),
            protocol=str(value.get("protocol", "openai_compatible")).strip().lower(),
            base_url=str(value.get("base_url", "")).strip().rstrip("/"),
            api_key_ref=str(value.get("api_key_ref", "")).strip(),
            models=tuple(models), external=bool(value.get("external", True)),
            enabled=bool(value.get("enabled", True)),
            timeout_seconds=max(0.1, float(value.get("timeout_seconds", 7.0))),
            headers={str(k): str(v) for k, v in dict(value.get("headers", {})).items()},
        )


def _is_loopback_url(value: str) -> bool:
    from urllib.parse import urlparse
    host = (urlparse(value).hostname or "").casefold()
    return host in {"127.0.0.1", "localhost", "::1"}


class BrainProviderConfigurator:
    """User-facing add/remove operations that separate metadata from credentials."""

    def __init__(self, config_store: BrainConfigStore, secret_store: SecretStore) -> None:
        self.config_store = config_store
        self.secret_store = secret_store

    def upsert_openai_compatible(self, *, name: str, base_url: str, api_key: str,
                                 model: str, roles: tuple[BrainRole, ...],
                                 external: bool | None = None,
                                 streaming: bool = True,
                                 structured_output: bool = False,
                                 tool_calling: bool = False,
                                 vision: bool = False,
                                 context_window: int = 4096) -> ProviderConfig:
        provider_name = name.strip()
        if not provider_name or not model.strip() or not base_url.strip():
            raise ValueError("provider name, base URL and model are required")
        reference = f"provider:{provider_name}"
        setter = getattr(self.secret_store, "set", None)
        if api_key:
            if not callable(setter):
                raise ValueError("configured secret store is read-only")
            setter(reference, api_key)
        local_endpoint = _is_loopback_url(base_url)
        config = ProviderConfig(
            name=provider_name, protocol="openai_compatible",
            base_url=base_url.strip().rstrip("/"), api_key_ref=reference if api_key else "",
            models=(ModelCapabilityProfile(
                model=model.strip(), roles=frozenset(roles), streaming=streaming,
                structured_output=structured_output, tool_calling=tool_calling,
                vision=vision, context_window=max(1, int(context_window)),
                local=local_endpoint, tested=frozenset(),
            ),),
            external=(not local_endpoint if external is None else bool(external or not local_endpoint)),
        )
        current = {item.name: item for item in self.config_store.load()}
        current[provider_name] = config
        self.config_store.save(tuple(current.values()))
        return config

    def remove(self, name: str, *, remove_secret: bool = True) -> bool:
        current = {item.name: item for item in self.config_store.load()}
        removed = current.pop(name, None)
        if removed is None:
            return False
        self.config_store.save(tuple(current.values()))
        if remove_secret:
            deleter = getattr(self.secret_store, "delete", None)
            if callable(deleter):
                deleter(removed.api_key_ref or f"provider:{name}")
        return True


__all__ = ["BrainConfigStore", "BrainProviderConfigurator"]
