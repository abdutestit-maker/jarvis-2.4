"""Sprint 11 local living-context and proactive-intelligence API."""

from .context import LivingContextEngine
from .inference import FrictionDetector, GoalTracker
from .models import (
    ActivityEpisode,
    AutonomyLevel,
    ComputerAssistanceLevel,
    ContextObservation,
    CurrentContext,
    FrictionSignal,
    GoalHypothesis,
    InterruptionLevel,
    ProactiveAction,
    ReturnContext,
)
from .monitor import LivingContextMonitor, WindowsContextSampler
from .workflow import (
    SemanticAction,
    WorkflowCandidate,
    WorkflowCapabilityBridge,
    WorkflowExecutor,
    WorkflowLearner,
    WorkflowRun,
)
from .proactive import (
    AssistancePolicy,
    AttentionManager,
    AttentionSnapshot,
    ProactiveCandidate,
    ProactiveDecisionEngine,
    ProactiveMemoryStore,
    UserProfile,
    UserProfileStore,
)
from .resources import (
    BackgroundBudgetManager,
    BackgroundMode,
    CapabilityQualityLoop,
    LocalResourceSampler,
    ResourceSnapshot,
    ShadowPriorityFactors,
)
from .service import LivingIntelligence

__all__ = [
    "ActivityEpisode", "AutonomyLevel", "ComputerAssistanceLevel",
    "ContextObservation", "CurrentContext", "FrictionDetector", "FrictionSignal",
    "GoalHypothesis", "GoalTracker", "InterruptionLevel", "LivingContextEngine",
    "LivingContextMonitor", "WindowsContextSampler",
    "ProactiveAction", "ReturnContext",
    "SemanticAction", "WorkflowCandidate", "WorkflowCapabilityBridge",
    "WorkflowExecutor", "WorkflowLearner", "WorkflowRun",
    "AssistancePolicy", "AttentionManager", "AttentionSnapshot",
    "ProactiveCandidate", "ProactiveDecisionEngine", "ProactiveMemoryStore",
    "UserProfile", "UserProfileStore",
    "BackgroundBudgetManager", "BackgroundMode", "CapabilityQualityLoop", "LocalResourceSampler",
    "ResourceSnapshot", "ShadowPriorityFactors",
    "LivingIntelligence",
]
