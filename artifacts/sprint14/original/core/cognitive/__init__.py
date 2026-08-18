"""ATLAS Cognitive Core public contract."""

from core.cognitive.addressing import AddressFormStore, AddressMatch, AddressRecognizer
from core.cognitive.continuity import ContinuityResolver, GoalStack
from core.cognitive.identity import AtlasIdentityCore
from core.cognitive.models import (
    CognitiveEpisode,
    ContinuationResolution,
    CurrentMindState,
    GoalFrame,
)
from core.cognitive.orchestrator import CognitiveOrchestrator, CognitiveTurn
from core.cognitive.self_model import (
    CapabilitySelfModel,
    SelfKnowledgeAnswer,
    SelfModelSnapshot,
)
from core.cognitive.state import MindStateStore

__all__ = [
    "AddressFormStore", "AddressMatch", "AddressRecognizer", "AtlasIdentityCore",
    "CognitiveEpisode", "ContinuationResolution", "ContinuityResolver",
    "CognitiveOrchestrator", "CognitiveTurn", "CurrentMindState", "GoalFrame",
    "GoalStack", "MindStateStore", "CapabilitySelfModel", "SelfKnowledgeAnswer",
    "SelfModelSnapshot",
]
