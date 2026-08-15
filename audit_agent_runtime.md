# Agent-Runtime / Planning / Execution Donor Audit (E:\jarvis-donors)

Read-only static analysis. Protected dirs EVA/jarvis/jarvis-py NOT touched.
camel uses README.ja.md (valid). MIT/Apache-2.0 everywhere → all GREEN.

## Per-Donor Mechanism Findings

### agent-zero — LICENSE: MIT (GREEN)
- Mechanism: main agent loop — `agent-zero/agent.py` `run_task()` with `while True` (L388) + nested per-turn loop (L400) and `self.loop_data.iteration` counter; `handle_intervention`, `handle_reasoning_stream`, `handle_response_stream` hooks.
- Mechanism: tool system — `agent-zero/helpers/tool.py` `class Tool` with `execute()` / `before_execution()` / `after_execution()` lifecycle; `tools/` dir with `parallel.py`, `scheduler.py`, `skills_tool.py`, `call_subordinate.py`, `notify_user.py`, `document_query.py`, `vision_load.py`.
- Mechanism: multi-agent — `tools/call_subordinate.py` (delegates to a named sub-agent) + `tools/parallel.py` (run several agents in parallel); `a2a_chat.py` (agent-to-agent).
- Mechanism: background/long tasks — `tools/scheduler.py` (delayed/scheduled tool execution).
- Mechanism: prompts-as-files — `agents/<profile>/prompts/*.md` (system role, solving, tool-response) + `prompts/agent.system.main.solving.md` (in-prompt planning).
- Problem solved: generalist autonomous loop with subagent delegation + scheduling + file-driven prompt profiles; scheduler enables background execution.
- Recommendation: **ADAPT** the `Tool` lifecycle + subagent/scheduler tools + file-based prompt profile system. MIT, clean, self-contained.

### openhands — LICENSE: MIT (GREEN)
- NOTE: snapshot is the TypeScript/Electron FRONTEND only. Core Python runtime (`opend`: AgentController → CodeActAgent, `planner.py`, memory condensing) is NOT present in this checkout (only `.github/scripts/*.py` CI + `tools/canvas_ui_tool.py`).
- Mechanism (present): observability/UI — `src/components/features/chat/tool-visualizers/*` (bash/file-editor/search/task), `src/api/agent-canvas-updates.ts`, `runtime-service/agent-server-runtime-service.ts`, agent-profile management.
- Mechanism (architectural, backend not in snapshot): agent loop = Controller drives Agent; planner builds a plan then CodeActExecutor runs shell; memory condensation.
- Problem solved (for JARVIS): reference-grade agent UI + human-verifiable tool event stream + canvas versioning.
- Recommendation: **ADAPT** the UI/observability/tool-visualizer layer only. Runtime/planner/executor must be sourced elsewhere (not in this snapshot). Value here is UI, not core loop.

### autogpt — LICENSE: MIT (classic); Polyform Shield (autogpt_platform, EXCLUDED) (GREEN for classic)
- Mechanism: planning strategies — `autogpt/classic/original_autogpt/autogpt/agents/prompt_strategies/`: `plan_execute.py` (`PlanExecutePromptStrategy`, `ExecutionPlan`, `PlanExecuteActionProposal`), `reflexion.py`, `rewoo.py`, `tree_of_thoughts.py`, `lats.py`, `multi_agent_debate.py`, `one_shot.py` — composable `BaseMultiStepPromptStrategy`.
- Mechanism: agent loop — `autogpt/classic/original_autogpt/autogpt/agents/agent.py` `execute()` (L373) / `execute_single()` (L511) dispatch of `AssistantFunctionCall`.
- Mechanism: tool registration — `autogpt/classic/forge/forge/command/command.py` `class Command` + `decorator.py` `@command` decorator (typed args → schema); `forge/agent/forge_agent.py` `execute_step()` / `execute()`.
- Problem solved: pluggable planning algorithms (plan-execute, reflexion, ReWOO, ToT, LATS, debate) as swap-in strategies; clean `@command` tool decorator.
- Recommendation: **ADAPT** the prompt-strategy planner hierarchy + forge `@command` decorator. MIT classic.

### agno — LICENSE: Apache-2.0 (GREEN)
- Mechanism: agent loop — `agno/libs/agno/agno/agent/agent.py` `run()` / `arun()` (L1345–1506), `_managers.py`, `_run.py`, `_response.py`, `_session.py`.
- Mechanism: model abstraction — `agno/libs/agno/agno/models/` ~50 providers (openai, anthropic, google, ollama, litellm, bedrock, groq, mistral, together, huggingface, vllm, …) + `base.py`, `fallback.py`, `message.py`, `response.py`.
- Mechanism: multi-agent — `agno/libs/agno/agno/team/team.py` `class Team` (members, `delegate_to_all_members`, `determine_input_for_members`, router leader, `add_team_history_to_members`) + `run/team.py`.
- Mechanism: workflow orchestration — `agno/libs/agno/agno/workflow/` `workflow.py`, `steps.py`, `step.py`, `loop.py`, `parallel.py`, `router.py`, `remote.py`, `factory.py`, `decorators.py`.
- Mechanism: memory + learning — `agno/libs/agno/agno/memory/` (`manager.py`, `strategies`) + `agno/libs/agno/agno/learn/` (machine, stores, schemas, curate).
- Mechanism: tools — `agno/libs/agno/agno/tools/`; tracing/telemetry in `agno/libs/agno/agno/tracing`, `metrics.py`.
- Problem solved: broadest model-provider abstraction + first-class multi-agent Team + graph-style Workflow + memory/learn + tracing.
- Recommendation: **ADAPT** Team/workflow orchestration + model provider layer + memory/learn. Apache-2.0, clean, highest multi-agent value.

### swarms — LICENSE: Apache-2.0 (GREEN)
- Mechanism: multi-agent topologies — `swarms/swarms/structs/`: `graph_workflow.py` (`GraphWorkflow`, `GraphBackend`), `agent_rearrange.py` (`AgentRearrange`), `groupchat.py` (`GroupChat`), `hiearchical_swarm.py` (`SwarmSpec`), `concurrent_workflow.py` (`ConcurrentWorkflow`), `agent_router.py` (`AgentRouter`), `auto_swarm_builder.py`.
- Mechanism: agent loop — `swarms/swarms/agents/autonomous_loop.py`, `auto_chat_agent.py`; variants `ape_agent.py`, `consistency_agent.py`, `flexion_agent.py`, `reasoning_duo.py`, `reasoning_agent_router.py`.
- Mechanism: LLM manager — `swarms/swarms/agents/llm_manager.py` (provider/concurrency abstraction); `context_compressor.py`.
- Problem solved: widest variety of multi-agent topologies (graph/rearrange/groupchat/hierarchical/concurrent) + auto-swarm builder from YAML.
- Recommendation: **ADAPT** the orchestration topology primitives (GraphWorkflow, AgentRearrange, GroupChat). Apache-2.0. Thinner memory/tool/UI than agno.

### camel — LICENSE: Apache-2.0 (GREEN; README.ja.md valid)
- Mechanism: agent loop — `camel/camel/agents/chat_agent.py` `class ChatAgent` with `step()` (L2896), `_step_impl()` (L2949), `_step_get_info()`, `_step_terminate()` (L4049); tool-calling variants.
- Mechanism: memory — `camel/camel/memories/` `agent_memories.py`, `base.py`, `blocks/`, `context_creators/` (modular memory blocks + context assembly).
- Mechanism: multi-agent — `camel/camel/societies/role_playing.py` `class RolePlaying`; `camel/camel/societies/workforce/` (role-based workforce orchestration); `mcp_agent.py`.
- Mechanism: research tooling — `camel/camel/benchmarks/`, `data_collectors/`, RAG/data-gen modules.
- Problem solved: clean ChatAgent.step loop + composable memory blocks + RolePlaying/workforce societies + strong research/data tooling.
- Recommendation: **ADAPT** ChatAgent.step + memory-blocks design + RolePlaying/workforce. Apache-2.0.

### swe-agent — LICENSE: MIT (GREEN)
- Mechanism: agent loop — `swe-agent/sweagent/agent/agents.py` `step()` (L328/L1235) + `run()` (L390/L1265); `SWEAgent` holds `_trajectory`, `_attempt_data`, `replay_config`.
- Mechanism: observability / replay — `save_trajectory()`, `get_trajectory_data()`, `_chook.on_run_done(trajectory=...)`; drivers `run/single.py`, `run_replay.py`, `run_batch.py`; `run/run_replay.py` re-executes saved trajectories.
- Mechanism: error recovery / context — `swe-agent/sweagent/agent/history_processors.py` composable `HistoryProcessor.__call__(history)->history` (windowing, summary, trait-stripping) e.g. `DefaultHistoryProcessor` (L15).
- Mechanism: execution env — `swe-agent/sweagent/environment/swe_env.py` `execute_command()` (containerized shell); command tools.
- Problem solved: best-in-class trajectory logging + replay + composable history processors for context-window management and error recovery/observability.
- Recommendation: **COPY/ADAPT** the trajectory + history-processor pattern (MIT, small, self-contained). Narrow (SWE) scope but the observability design is reusable.

### pydantic-ai — LICENSE: MIT (GREEN)
- Mechanism: agent loop + retry — `pydantic-ai/pydantic_ai_slim/pydantic_ai/agent/abstract.py` `run()` / `run_sync()` / `run_stream()` / `run_stream_events()`; `AgentRetries` (typed retry config) + per-tool `ToolOutput(max_retries=...)` (L109–125).
- Mechanism: model abstraction — `pydantic_ai_slim/pydantic_ai/models/`: openai, anthropic, google, groq, ollama, mistral, bedrock, huggingface, together, cerebras, cohere, etc. + `fallback.py` (`FallbackModel`), `function.py`, `instrumented.py`, `concurrency.py`.
- Mechanism: tool system — `pydantic_ai_slim/pydantic_ai/toolsets/`: `Toolset`, `WrapperToolset`, `ToolSearchToolset` (semantic tool search, `max_retries` cascade), `deferred_loading`, `approval_required`, `prefixed`, `prepared`, `renamed`, `filtered`, `combined`, `external`.
- Mechanism: durable/background execution — `pydantic_ai_slim/pydantic_ai/durable_exec/` backends: `dbos/`, `prefect/`, `temporal/` (+ `_base.py`, `_runtime_toolsets.py`) → long-running/resumable tasks.
- Mechanism: graphs — `pydantic_graph` (separate pkg) for state-machine agentic flows; `mcp.py` + `capabilities/mcp.py` (MCP); `ui/ag_ui`, `ui/vercel_ai`.
- Problem solved: strongest model-abstraction + richest typed toolset system with per-tool retries + durable background execution (DBOS/Prefect/Temporal) + graph flows + MCP.
- Recommendation: **ADAPT** core (model layer + FallbackModel, toolsets, retry, durable_exec, pydantic_graph). MIT — highest overall value for JARVIS.

## Comparative Matrix (0–5 scale)

DONOR | agent_loop | tools | computer_use | browser | memory | research | multi_agent | voice | ui | long_tasks | mcp | license | value(0-5) | justification
agent-zero | 4 | 4 | 3 | 3 | 3 | 3 | 4 | 1 | 4 | 4 | 3 | MIT | 4 | Well-rounded generalist loop; subagent+scheduler+skills tools; file-driven prompts; MIT.
openhands | 2 | 2 | 3 | 2 | 2 | 2 | 1 | 1 | 5 | 2 | 2 | MIT | 2 | Frontend-only snapshot; core runtime/planner absent here but UI/observability is reference-grade.
autogpt | 3 | 3 | 2 | 2 | 3 | 3 | 3 | 1 | 2 | 2 | 1 | MIT | 3 | Richest composable planning strategies (plan_execute/reflexion/rewoo/ToT/LATS) + clean @command decorator.
agno | 4 | 4 | 2 | 2 | 4 | 3 | 5 | 2 | 3 | 4 | 3 | Apache-2.0 | 5 | Best multi-agent orchestration (Team+Workflow) + broadest model providers + memory/learn + tracing.
swarms | 3 | 3 | 1 | 1 | 2 | 2 | 5 | 1 | 1 | 3 | 1 | Apache-2.0 | 3 | Widest multi-agent topologies (graph/rearrange/groupchat/hierarchical) but thin memory/tool/UI.
camel | 4 | 3 | 1 | 2 | 4 | 4 | 4 | 1 | 1 | 3 | 2 | Apache-2.0 | 4 | Clean ChatAgent.step + memory blocks + RolePlaying/workforce + strong research tooling.
swe-agent | 4 | 3 | 4 | 1 | 2 | 1 | 1 | 0 | 2 | 4 | 1 | MIT | 3 | Best trajectory logging + replay + composable history processors for recovery; narrow SWE scope.
pydantic-ai | 4 | 5 | 1 | 1 | 2 | 1 | 3 | 1 | 3 | 5 | 4 | MIT | 5 | Best model abstraction + richest toolset w/ per-tool retries + durable background exec (DBOS/Prefect/Temporal) + graph.

## Conclusions — Best Patterns for JARVIS

- **Agent loop:** Combine pydantic-ai's `run/run_stream` with typed `AgentRetries` + per-tool `max_retries` (robust retry) and swe-agent's `step()` + trajectory log (observability). The loop should emit a structured trajectory at every step for replay/debug.
- **Planner:** ADAPT autogpt's composable `BaseMultiStepPromptStrategy` hierarchy (plan_execute / reflexion / rewoo / ToT / LATS) as swappable planning modules; delegate sub-goals via agno `Team` router or agent-zero `call_subordinate`.
- **Executor:** ADAPT swe-agent's `history_processors` (windowing/summarization) for context management + trajectory `replay` for error recovery; wrap execution in agno `Workflow` steps for resumability.
- **Tool system:** ADAPT pydantic-ai `toolsets` (deferred loading, `ToolSearchToolset` semantic lookup, `approval_required`, `prefixed`, per-tool `max_retries`). Cleanest tool lifecycle; agent-zero `Tool.before/after_execution` hooks as secondary reference.
- **Model abstraction:** ADAPT pydantic-ai `models/` + `FallbackModel` (primary) or agno `models/` (~50 providers). Both MIT/Apache-2.0, 20+ providers, clean base class.
- **Multi-agent:** ADAPT agno `Team` (delegation/router) for runtime + swarms `GraphWorkflow`/`AgentRearrange`/`GroupChat` for explicit topologies; camel `RolePlaying`/`workforce` for role-based societies.
- **Memory:** ADAPT agno `memory` manager + `learn` (self-improving) and camel `memory` blocks + `context_creators` (modular assembly).
- **Background / long tasks:** ADAPT pydantic-ai `durable_exec` (DBOS / Prefect / Temporal) for resumable long-running agents — unique among donors.
- **Observability:** ADAPT swe-agent trajectory replay + agno `tracing`/`metrics`/`telemetry`.

**Net recommendation:** Build JARVIS core on pydantic-ai abstractions (model + toolset + retry + durable_exec + graph), layer agno Team/Workflow + swarms topologies for orchestration, borrow swe-agent trajectory/history-processor for observability/recovery, and agent-zero/autogpt planning strategies for the planner. All donors are MIT or Apache-2.0 (GREEN) → safe to ADAPT/COPY with attribution.
