# Brain Fabric Design

## Architecture

`core.brain` is an additive orchestration boundary. Existing `LLMBackend` implementations remain intact and are wrapped by provider adapters. `BrainFabric` owns the provider registry, semantic router, health/circuit state, context composition, bounded fallback and mission route binding. The legacy tier router receives a compatibility bridge so existing Council and Agent paths can use the fabric without changing the frontend or action pipeline.

## Components

1. **Typed contracts** — enums and immutable request/route/result/capability records contain no hidden reasoning.
2. **Provider adapters** — one OpenAI-compatible HTTP adapter is reused by OpenAI, OpenRouter and custom endpoints; Anthropic and local GGUF adapt their existing backends.
3. **Secure configuration** — ordinary JSON stores provider metadata and `api_key_ref` only. Secret resolution uses environment variables or a local protected store; logs and exported config are recursively redacted.
4. **Semantic router** — filters by privacy, required capabilities, context size, health and user policy, then ranks by role, locality, latency and cost. It returns structured reason codes and a bounded fallback chain.
5. **Execution fabric** — binds one route per mission stage, invokes a provider, records health, and advances through the bounded chain on a quick failure. Tool calls remain data and never execute at this layer.
6. **Context and output** — `ContextComposer` applies role budgets and preserves identity, request and mission before optional memory. `StructuredOutputValidator` performs typed validation and bounded repair.
7. **Local lifecycle** — discovers configured GGUF files, inspects safe header metadata, estimates RAM, and loads only the selected model. Idle unload is explicit.
8. **Integration** — Cognitive Core owns `BrainFabric`; Council and Agent receive its backend bridge; CapabilitySelfModel reports factual active provider/model details; Shadow asks the policy for a local background route.

## Data flow

`user/mission → Cognitive Core → BrainRequest → semantic route → policy/privacy filter → healthy provider/model → composed context + identity contract → generate/stream → schema validation → Cognitive Core → Risk Gate/Capability Engine/verification`.

Provider failures update health and open a bounded circuit. The route advances without rebinding the mission to an unrelated provider mid-step. A new mission or stage may select a different semantic role.

## Safety and failure handling

- LOCAL_ONLY filters every external provider before scoring.
- SENSITIVE cloud use requires explicit policy permission.
- API keys are never present in provider snapshots, routing reasons, benchmark records or exception messages.
- Malformed structured output is inert data and receives at most two repair attempts.
- Cancellation is provider-scoped and thread-safe.
- All-provider failure returns a user-safe status while debug data stays redacted.

## Testing

Tests use real local Python objects and a loopback HTTP server rather than cloud services. They cover provider contracts, custom endpoints, health, circuit breaking, routing, privacy, context budgets, structured validation, capability probes, GGUF discovery, identity consistency, hot reload, critic decisions, Shadow policy, secret leakage, malformed responses and mid-mission failure. The final gate runs the entire repository suite plus a loopback live demo and performance probe.

## Self-review

The design contains no placeholders, keeps the frontend unchanged, preserves the existing local default, separates model confidence from evidence confidence, and does not replace existing capability, risk or verification owners.

