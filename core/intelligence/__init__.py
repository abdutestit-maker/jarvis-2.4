"""Universal intelligence contracts for JARVIS.

The package is deliberately lightweight on the active path: task intake is
deterministic and local, while heavier teaching/research work is opt-in or
scheduled on the deliberate/background path.
"""

from .contracts import (
    EvidenceRecord,
    LatencyBudget,
    LatencyObservation,
    ResearchPending,
    TaskContract,
    latency_summary,
)
from .intake import IntentFamily, UniversalIntake
from .skills import SkillCatalog, SkillManifest, ProviderChoice, choose_provider, default_skill_manifests
from .tutor import TeachingSession, TutorEngine, TutorResult, TutorMode

__all__ = [
    "EvidenceRecord", "LatencyBudget", "LatencyObservation", "ResearchPending",
    "TaskContract", "latency_summary", "IntentFamily", "UniversalIntake",
    "SkillCatalog", "SkillManifest", "ProviderChoice", "choose_provider", "default_skill_manifests", "TeachingSession",
    "TutorEngine", "TutorResult", "TutorMode",
]
