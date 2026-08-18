"""Provider manifests and deterministic provider priority."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable


@dataclass
class SkillManifest:
    name: str
    description: str = ""
    inputs: list[str] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)
    providers: list[str] = field(default_factory=list)
    risk: str = "low"
    verification: list[str] = field(default_factory=list)
    rollback: str = "none"
    reliability: float = 0.0
    latency_class: str = "deliberate"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderChoice:
    provider: str
    reason: str
    rank: int


class SkillCatalog:
    """Small manifest catalog; execution still belongs to existing owners."""

    def __init__(self, manifests: Iterable[SkillManifest] | None = None) -> None:
        self._items = {item.name: item for item in (manifests or default_skill_manifests())}

    def get(self, name: str) -> SkillManifest | None:
        return self._items.get(str(name))

    def list(self) -> list[SkillManifest]:
        return list(self._items.values())

    def register(self, manifest: SkillManifest) -> None:
        self._items[manifest.name] = manifest


_ORDER = ("native_api", "com", "cli", "powershell", "config", "registry", "uia", "dom", "playwright", "vision", "coordinates")


def choose_provider(available: Iterable[str], *, allow_coordinates: bool = False) -> ProviderChoice | None:
    candidates = {str(item).casefold() for item in available}
    for rank, provider in enumerate(_ORDER):
        if provider == "coordinates" and not allow_coordinates:
            continue
        if provider in candidates:
            return ProviderChoice(provider, f"selected by deterministic priority rank {rank}", rank)
    return None


def default_skill_manifests() -> list[SkillManifest]:
    return [
        SkillManifest(
            name="explain_local_material",
            description="Explain a local document or screenshot with bounded evidence.",
            inputs=["path", "query"],
            providers=["config", "vision"],
            verification=["citation_present", "source_exists"],
            latency_class="deliberate",
        ),
        SkillManifest(
            name="install_and_configure_app",
            description="Install from a trusted source and reach a verified desired state.",
            inputs=["application", "reference"],
            providers=["native_api", "cli", "powershell", "uia", "dom", "vision"],
            risk="medium",
            verification=["publisher_verified", "launch_observed", "desired_state_verified"],
            rollback="checkpoint_required",
            latency_class="deliberate",
        ),
        SkillManifest(
            name="research_with_offline_resume",
            description="Research online when available and persist a resumable task when not.",
            inputs=["query"],
            providers=["cli", "dom"],
            verification=["source_citations", "resume_task_on_network_failure"],
            latency_class="background",
        ),
    ]
