# ATLAS Sprint 15 — Brain Fabric

Implementation scope accepted from the Sprint 15 request on 2026-08-17.

## Invariant

ATLAS owns identity, memory, capabilities, risk decisions and verification. Models are replaceable cognitive engines selected by semantic role and policy. No provider may bypass the Capability Engine, Risk Gate or verification boundary.

## Required surface

- `BrainFabric` is the single model-orchestration facade.
- Semantic roles: CHAT, FAST, REASONING, CODER, PLANNER, RESEARCH, VISION, CRITIC, SUMMARIZER and FALLBACK.
- Providers: local GGUF, OpenAI-compatible/custom, OpenAI, Anthropic and OpenRouter.
- Provider contract: health, models, generate, stream, cancel and capabilities.
- Routing inputs: task, complexity, required capabilities, privacy, latency, cost, availability and context size.
- Default policy is local-first with cloud disabled.
- Fallback is bounded and circuit-breaker aware.
- Context composition is relevance- and role-budgeted.
- Provider keys are referenced through the secure store and never persisted in provider configuration, memory or audit output.
- Local GGUF discovery reads file and header metadata without copying model files.
- Hot reload changes only future selections; a bound mission keeps its route unless fallback is required.
- Shadow background work uses cheap/local models unless explicitly permitted.

## Acceptance

Automated tests cover every Sprint 15 test category. A local OpenAI-compatible live endpoint demonstrates role routing, provider failure and bounded fallback, identity consistency, LOCAL_ONLY isolation, provider add/remove hot reload, and measured latency. Full Sprint 8–14 and voice regressions remain green.

