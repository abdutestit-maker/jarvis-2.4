"""Canonical mission authority for JARVIS 4.0.

The kernel is intentionally additive.  Existing orchestrators and agents can
keep their public contracts while every new mission gets an idempotent record,
typed evidence and a verified outcome in one local ledger.
"""

from .models import (
    CancellationResult,
    DecisionTrace,
    EvidenceRecordV2,
    MissionHandle,
    MissionRecord,
    RuntimeProfile,
    TaskContractV2,
    VerificationOutcome,
)
from .capabilities import CapabilityGraph, CapabilityManifest
from .ledger import MissionLedger
from .kernel import CognitiveKernel

__all__ = [
    "CancellationResult",
    "CapabilityGraph",
    "CapabilityManifest",
    "CognitiveKernel",
    "DecisionTrace",
    "EvidenceRecordV2",
    "MissionHandle",
    "MissionLedger",
    "MissionRecord",
    "RuntimeProfile",
    "TaskContractV2",
    "VerificationOutcome",
]
