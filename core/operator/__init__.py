"""Verified real-world computer operator components for Sprint 10."""

from .adapters import XmlConfigAdapter, XmlSetting
from .knowledge import AppKnowledge, AppKnowledgeStore
from .mission import MissionControl, OperatorMission, OperatorMissionReport
from .setup import SetupMission
from .reference import (
    DesiredStateDiff,
    ReferenceInterpreter,
    VideoReferenceProvider,
)
from .session import ForegroundClass, ForegroundSession
from .software import InstallerEngine, SoftwareCandidate, SoftwareResolver
from .windows import AppExplorer, SemanticControl, SemanticSelector

__all__ = [
    "AppExplorer",
    "AppKnowledge",
    "AppKnowledgeStore",
    "DesiredStateDiff",
    "ForegroundClass",
    "ForegroundSession",
    "InstallerEngine",
    "MissionControl",
    "OperatorMission",
    "OperatorMissionReport",
    "ReferenceInterpreter",
    "SemanticControl",
    "SemanticSelector",
    "SoftwareCandidate",
    "SoftwareResolver",
    "SetupMission",
    "VideoReferenceProvider",
    "XmlConfigAdapter",
    "XmlSetting",
]
