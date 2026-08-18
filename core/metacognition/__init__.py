"""ATLAS metacognition public contracts."""

from core.metacognition.calibration import ConfidenceCalibrator
from core.metacognition.audit import AuditTrail
from core.metacognition.correction import (
    CorrectionAttempt,
    CorrectionReport,
    SelfCorrectionEngine,
    Strategy,
)
from core.metacognition.engine import KnowledgeDecision, MetacognitionEngine
from core.metacognition.freshness import FreshnessPolicy
from core.metacognition.expectation import (
    ComparisonResult,
    Expectation,
    ExpectationComparator,
    Surprise,
)
from core.metacognition.failures import (
    FailureEpisode,
    FailureEpisodeStore,
    fingerprint_environment,
)
from core.metacognition.models import (
    Belief,
    CalibrationResult,
    EpistemicState,
    EpistemicStatus,
    EvidenceRef,
    Freshness,
    FreshnessState,
    SourceType,
    VerificationStatus,
)
from core.metacognition.store import BeliefStore

__all__ = [
    "AuditTrail", "Belief", "BeliefStore", "CalibrationResult", "ComparisonResult",
    "ConfidenceCalibrator", "CorrectionAttempt", "CorrectionReport", "EpistemicState", "EpistemicStatus",
    "EvidenceRef", "Expectation", "ExpectationComparator", "FailureEpisode",
    "FailureEpisodeStore", "Freshness", "FreshnessPolicy", "FreshnessState",
    "KnowledgeDecision", "MetacognitionEngine", "SelfCorrectionEngine", "SourceType",
    "Strategy", "Surprise", "VerificationStatus", "fingerprint_environment",
]
