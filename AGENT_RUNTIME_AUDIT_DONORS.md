# Архитектурный аудит donor-проектов: AGENT RUNTIME / PLANNING / EXECUTION / MULTI-AGENT

> Read-only аудит 9 проектов (E:\jarvis-donors). Цель — извлечь **REIMPLEMENT-паттерны** для JARVIS (desktop general-purpose agent). Ничего не устанавливалось, не запускалось, не менялось.

---

# DONOR: openhands

## Идея / лицензия / entrypoint / структура
- **Идея**: «Agent Canvas» — self-hosted developer control center. Запускает coding-агентов (OpenHands/Claude Code/Codex/Gemini) через **ACP (Agent-Client Protocol)** поверх local/docker/VM/cloud backends. Это **UI/оркестратор бэкендов**, а не runtime агента.
- **Лицензия**: `MIT License` (Copyright © 2025 OpenHands contributors) — `openhands/LICENSE`.
- **Стек**: TypeScript/React + Electron (`electron/`, `src/`), `package.json` (`@openhands/agent-canvas`), `agent-canvas` CLI.
- **Entrypoint**: `agent-canvas` (frontend + ingress + agent-server). Реальный agent-runtime — в отдельном репозитории OpenHands (здесь только canvas).
- **Структура**: `src/` (React routes, components, stores, services, lib), `electron/` (main.mjs, preload), `docs/` (SELF_HOSTING, automations/ACP).

## Agent loop
- Сам не реализует loop — делегирует бэкенду через **ACP**. См. `src/services/` и `docs/usage/agent-canvas/acp-agents`. Loop живёт в агент-сервере (вне этого чекаута).

## Tool system
- Расширение не здесь; инструменты определяются бэкендом-агентом. Canvas лишь визуализирует automations (Slack/GitHub/Linear webhooks).

## Planning / Execution
- Нет планировщика в этом слое. «Automations» = scheduled/webhook-триггеры на запуск агента.

## Model abstraction
- «Bring your own model» через LLM profiles бэкенда.

## Multi-agent / Orchestration
- Orchestration = переключение backend-агентов из одного фронтенда. Не внутренняя оркестрация.

## Error recovery / Observability
- Фронтенд-логи; реальный error-recovery в бэкенде.

## Оценки (0-5)
| AGENT LOOP | TOOLS | COMPUTER USE | BROWSER | MEMORY | RESEARCH | MULTI-AGENT | VOICE | UI | LONG TASKS | MCP | LICENSE | VALUE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 5 | 1 | 1 | 5(MIT) | 2 |

## Ключевые механизмы для JARVIS
- **ACP-протокол (Agent-Client Protocol)** → `docs/usage/agent-canvas/acp-agents` + `src/services`. REIMPLEMENT: единый UI/control-plane поверх разных agent-backends (local/remote/cloud) без привязки к конкретному runtime. Хорошо для desktop: JARVIS может иметь UI-слой, который говорит с любым backend-агентом по ACP. Сложность ADAPT: средняя (нужен свой ACP-сервер).
- **Electron + React control center** → `electron/`, `src/`. ADAPT: паттерн desktop-оболочки поверх headless agent-runtime.

## Риски/ограничения
- Это НЕ runtime-донор; планирование/loop/tool-system нужно брать из других (agno/swarms/swe-agent).
- Заточен под coding-задачи, не general-purpose desktop.

---

# DONOR: openclaw

## Идея / лицензия / entrypoint / структура
- **Идея**: Production-grade **TypeScript agent runtime + Gateway** (плагинная архитектура). Плагин-агностичное core, всё через plugin-SDK/manifest/registry. Поддержка провайдеров LLM, каналов (Slack/Telegram/Discord), tool-plugins, approvals, net-policy.
- **Лицензия**: `MIT License` (Copyright (c) 2026 OpenClaw Foundation) — `openclaw/LICENSE`.
- **Entrypoint**: `openclaw.mjs` (24KB CLI, 532KB `package.json`), `pnpm openclaw` / `pnpm dev` (Node 22+).
- **Структура**: `packages/` (agent-core, llm-core, gateway-protocol, gateway-client, tool-call-repair, retry, net-policy, memory-host-sdk, plugin-sdk, sdk, acp-core…), `extensions/` (≈100+ плагинов: anthropic, browser, codex, aws, brave…), `apps/`, `config/`.

## Agent loop
- **`packages/agent-core/src/agent-loop.ts`** (1927 строк) — центральный event-driven loop. Поток событий: `text_start/delta/end`, `thinking_*`, `toolcall_start/delta/end`. Обрабатывает `AssistantMessage` → tool calls → `ToolResultMessage`. Есть **tool-loop recovery** (`TOOL_LOOP_RECOVERY_TERMINATED_MESSAGE`), steering (пользователь может вмешаться между turns — `STEERING_TOOL_SKIP_MESSAGE`), turn-interruption (`turn-interruption.ts`), `getSteeringMessages`.
- Режимы: `reasoning.ts` (`resolveAgentReasoningOption`), compaction replay.

## Tool system
- **Tool-плагины** в `extensions/*/src`. Core потребляет их через `plugin-sdk` (barrels `api.ts`, `runtime-api.ts`), manifest-контракты. Типы: `AgentTool`, `AgentToolCall`, `AgentToolResult` (`agent-core/src/types.ts`).
- **`packages/tool-call-repair/`** — уникальный механизм: парсит/восстанавливает plain-text tool calls, которые модель выдала не в JSON-формате (`parseStandalonePlainTextToolCallBlocks`, `stream-normalizer.ts`, `promote.ts`). Это **error-recovery для неструктурированных tool-call'ов**.

## Planning / Execution
- Планирование не выделено в отдельный модуль (general-purpose conversation-agent, не planner-ориентированный). Execution — последовательный loop с опциональным параллелизмом tool batch (`takeInternalToolBatchLifecycle`).

## Model abstraction
- **`packages/llm-core/`** (`model-contracts/`, `types.ts`, `validation.ts`) + **`packages/model-catalog-core`** + `extensions/<provider>` (anthropic, openai, bedrock…). Роутинг провайдеров через плагины; `memory-host-sdk` для embeddings/sessions.

## Multi-agent / Orchestration
- Нет встроенного multi-agent в core; orchestration идёт через Gateway (routing сообщений по каналам/agents), `gateway-protocol`. Subagent flows упоминаются в доктрине (`AGENTS.md`).

## Error recovery / Observability
- `packages/retry/` (Result-тип из `normalization-core/result`), `tool-call-repair`, `turn-interruption`, `net-policy` (redact-sensitive-url, ip-фильтры SSRF), audit (`audit.run.inspect`). Очень строгая доктрина (`AGENTS.md` 422 строки): fail-closed, delegated run authority closure-bound, execution identity audit.

## Оценки (0-5)
| AGENT LOOP | TOOLS | COMPUTER USE | BROWSER | MEMORY | RESEARCH | MULTI-AGENT | VOICE | UI | LONG TASKS | MCP | LICENSE | VALUE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 4 | 2(comp-ext) | 3(browser ext) | 3(mem-sdk) | 1 | 2 | 2(azure-speech ext) | 3(gateway) | 3(pause/steering) | 2(acp-core) | 5(MIT) | 4 |

## Ключевые механизмы для JARVIS
- **`agent-loop.ts` event-stream loop** → REIMPLEMENT: единый turn-loop с streaming-событиями, steering (вмешательство юзера mid-run), turn-interruption. Отлично для desktop agent с GUI-кнопкой «Stop/Edit». Сложность REIMPLEMENT: высокая (TS), но паттерн переносим на Python.
- **`tool-call-repair`** → REIMPLEMENT: восстановление некорректных/plain-text tool calls модели. Критично для desktop, где модель иногда «забывает» JSON. Сложность ADAPT: низкая-средняя (чистая логика парсинга).
- **Plugin-SDK / manifest contract** → ADAPT: расширяемость tool/provider без правки core. Сложность: средняя.
- **`net-policy` (SSRF/redact)** → REIMPLEMENT для desktop security (блок локальных IP при web-тулах).

## Риски/ограничения
- TypeScript (JARVIS может быть Python/TS — нужна адаптация).
- Огромная доктрина/legacy-миграции делают fork тяжёлым; брать паттерны точечно, а не код.

---

# DONOR: autogpt

## Идея / лицензия / entrypoint / структура
- **Идея**: Два продукта в одном репо: **`autogpt_platform/`** (Low-code agent builder, Polyform Shield License — НЕ для JARVIS) и **`classic/original_autogpt/`** (классический autonomous agent, ReAct-подобный loop). Нас интересует classic.
- **Лицензия**: `LICENSE` — гибридная: `autogpt_platform/` под **Polyform Shield License** (commercial-restrictive!), всё остальное (включая classic) — **Apache-2.0** + MIT-фрагменты. Для JARVIS коммерческого закрытого — **classic (Apache-2.0) безопасен**, platform — НЕТ.
- **Entrypoint**: `autogpt/classic/original_autogpt/autogpt/app/main.py`, `cli.py`, `agent_protocol_server.py`.
- **Структура classic**: `agents/` (`agent.py`, `agent_manager.py`, `prompt_strategies/`: `plan_execute.py`, `reflexion.py`, `rewoo.py`, `lats.py`, `tree_of_thoughts.py`, `multi_agent_debate.py`, `one_shot.py`), `agent_factory/`, `app/`.

## Agent loop
- **`agents/agent.py`**: `class Agent(BaseAgent[AnyActionProposal])`. Цикл: `propose_action()` (LLM возвращает `AnyActionProposal` — ReAct-стиль действие) → `execute()` → observation обратно в контекст.
- **`execute()`** (line 373): **параллельное исполнение tool'ов** — `len(tools)==1` → `_execute_tool`, иначе `_execute_tools_parallel` (asyncio.gather, `execute_single` возвращает `(name, result, error)`). Перед exec — **permission check для каждого tool** (line 385-397: «Permission denied for command…»).

## Tool system
- Action-based: `propose_action` возвращает список `AssistantFunctionCall` (name + arguments). Command registry в `app/`. Расширяемость через `agent_factory` (генерация профиля агента).

## Planning / Execution
- **`prompt_strategies/`** — богатый набор стратегий планирования: `plan_execute` (plan→execute), `reflexion` (self-reflection), `rewoo` (reason-without-observation), `lats` (tree search), `tree_of_thoughts`, `multi_agent_debate`. Это **готовые planning-паттерны** как отдельные стратегии.

## Model abstraction
- `app/config.py`, provider-абстракция в `app/`. (В repo урезано; classic — более старая версия.)

## Multi-agent / Orchestration
- `prompt_strategies/multi_agent_debate.py` + `agent_manager.py`. Ограниченно.

## Error recovery / Observability
- try/except вокруг `_execute_tool`, сбор ошибок в параллельном режиме; Reflexion-стратегия = self-critique/retry.

## Оценки (0-5)
| AGENT LOOP | TOOLS | COMPUTER USE | BROWSER | MEMORY | RESEARCH | MULTI-AGENT | VOICE | UI | LONG TASKS | MCP | LICENSE | VALUE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 2 | 1 | 2 | 2 | 2 | 0 | 2 | 2 | 0 | 3(Apache-2.0, но гибрид!) | 3 |

## Ключевые механизмы для JARVIS
- **`prompt_strategies/` (plan_execute, reflexion, rewoo, lats)** → REIMPLEMENT: planning как **strategy-pattern** модуль. Хорошо для desktop: можно переключать стратегию под задачу. Сложность ADAPT: низкая (чистая логика промптов).
- **Параллельный execute** (`_execute_tools_parallel`, line 499) → REIMPLEMENT: одновременный запуск tool-вызовов с агрегацией ошибок. Сложность: низкая.
- **Permission check перед execute** (line 385) → REIMPLEMENT для desktop security (подтверждение опасных команд).

## Риски/ограничения
- Гибридная лицензия: платформа — Polyform Shield (коммерчески closed-source-враждебна). Брать ТОЛЬКО classic (Apache-2.0) и только паттерны, не код platform.
- classic устарел относительно современных runtime.

---

# DONOR: agno

## Идея / лицензия / entrypoint / структура
- **Идея**: Production agent **framework + runtime (AgentOS)** + UI. «Build, run, manage agent platforms». 50+ API endpoints (SSE/websockets), storage (sessions/memory/knowledge/traces в БД), 100+ integrations (toolkits), context providers (Slack/Drive/MCP), human approval, observability (OTel), JWT RBAC, scheduling.
- **Лицензия**: `Apache-2.0` (`agno/LICENSE`) — коммерчески friendly.
- **Entrypoint**: `libs/agno/agno/` (Python package). `Agent`, `Team`, `Workflow`, `Registry`.
- **Структура**: `agno/` с подмодулями: `agent/` (`_run.py`, `_run_options.py`, `_tools.py`, `_init.py`, `_storage.py`, `_messages.py`, `_hooks.py`, `_session.py`), `models/` (40+ провайдеров + `fallback.py`, `litellm.py`, `base.py`), `tools/` (`decorator.py`, `function.py`, `toolkit.py`, `mcp/`, ~200 toolkit-файлов), `team/`, `workflow/`, `registry/`, `memory/`, `session/`, `run/` (RunStatus, approval, cancel), `reasoning/`, `knowledge/`, `guardrails/`, `tracing/`, `scheduler/`, `learn/`, `skills/`, `vectordb/`.

## Agent loop
- **`agent/agent.py`** (`@dataclass Agent`) — модульный. Главный loop в **`agent/_run.py`** (`_arun_stream`, line 2151): 13 шагов (session → deps → pre-hooks → determine tools → run messages → memory bg → reasoning → model response incl. function calls → parser → followups → summary → cleanup/store). Loop — `while True` (line 4471 для sync-варианта) с `num_attempts` retry на каждом шаге (line 401, 813, 1537, 2210 — `for attempt in range(num_attempts)`). Обработка tool-ответов через `ahandle_tool_call_updates` (line 4733) + `determine_tools_for_model` + `tool_call_limit`. **Pause**: `if any(tool_call.is_paused …)` (line 4784) → RunStatus.PAUSED для approval.

## Tool system
- **`tools/decorator.py`** — `@tool` decorator (line 61/88): превращает функцию в `Function`. **`tools/function.py`** — `Function` (runtime entrypoint, caching, injected media params). **`tools/toolkit.py`** — `Toolkit` (группа tools).
- **Registry паттерн** → **`registry/registry.py`** (`class Registry`): flat/qualified `_entrypoint_lookup` (tool name ↔ Function/Callable, toolkit-qualified tuple keys). Центральный каталог tools/models/dbs/agents/teams. Это **ключевой extensibility-механизм**: добавить tool = зарегистрировать Function в Registry, без правки core.
- ~200 готовых toolkits: `browserbase.py`, `shell.py`, `webbrowser.py`, `duckduckgo.py`, `file.py`, `local_file_system.py`, `computer`-подобные.

## Planning / Execution
- `workflow/` (Workflow = много-step DAG-исполнение), `reasoning/` (chain-of-thought/reasoning-режимы), `planner` через Workflow. Team реализует hierarchical planner-исполнение.

## Model abstraction
- **`models/`**: `base.py` (Model ABC), 40+ провайдеров (openai, anthropic, google, ollama, groq, azure, bedrock, litellm…). **`models/fallback.py`** — `FallbackConfig` (line 21): error-specific routing — `on_rate_limit`, `on_context_window_exceeded`, general `on_error`; `get_fallback_models()` (line 76) не маскирует non-retryable 401/403. Это **production-grade fallback**.

## Multi-agent / Orchestration
- **`team/team.py`** (`class Team`, line 73): `members: List[Agent|Team]`, `delegate_to_all_members`, `determine_input_for_members`, `add_team_history_to_members`. Leader-агент делегирует подзадачи членам. Поддержка вложенных teams (recursive).

## Error recovery / Observability
- retry на каждом шаге (`num_attempts`), model fallback (выше), **approval/cancel** (`run/approval.py`, `run/cancel.py` — `acancel_run`, `aregister_run`, `raise_if_cancelled`), `RunStatus` enum (`run/base.py` line 327: created/running/completed/**paused**/**cancelled**/failed), **OTel tracing** (`tracing/`), guardrails (`guardrails/`), learning machine (`learn/`).

## Оценки (0-5)
| AGENT LOOP | TOOLS | COMPUTER USE | BROWSER | MEMORY | RESEARCH | MULTI-AGENT | VOICE | UI | LONG TASKS | MCP | LICENSE | VALUE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | 5 | 3 | 4(browserbase) | 4 | 3 | 4(Team) | 2(cartesia/eleven) | 3(AgentOS) | 4(pause/cancel/sched) | 4(mcp/*) | 5(Apache-2.0) | 5 |

## Ключевые механизмы для JARVIS
- **`@tool` decorator + `Function`/`Toolkit` + `Registry`** (`tools/decorator.py`, `tools/function.py`, `registry/registry.py`) → **REIMPLEMENT/ADAPT**: чистый, типобезопасный tool-registry паттерн. JARVIS берёт: decorator → Function-объект → Registry lookup по имени. Без переписывания core. Сложность ADAPT: низкая.
- **`RunStatus` (PAUSED/CANCELLED) + cancel/approval** (`run/base.py`, `run/cancel.py`) → REIMPLEMENT: pause/resume/cancel для long-running desktop tasks. Сложность: средняя.
- **`FallbackConfig` error-specific** (`models/fallback.py`) → REIMPLEMENT: переключение моделей по типу ошибки (429 → одна, context-exceeded → другая). Идеально для desktop, где модель может быть локальной+облачной. Сложность: низкая.
- **`Team` (leader-delegation)** (`team/team.py`) → ADAPT для multi-agent desktop оркестрации. Сложность: средняя.
- **OTel tracing + guardrails + learning** → ADAPT для observability/безопасности.

## Риски/ограничения
- Тяжёлый (AgentOS, 40+ провайдеров) — брать точечные модули, не весь framework.
- Много зависимостей; для desktop нужна выборочная сборка.

---

# DONOR: swarms

## Идея / лицензия / entrypoint / структура
- **Идея**: «Enterprise-Grade Production-Ready Multi-Agent Orchestration Framework». 60+ готовых multi-agent архитектур (sequential, concurrent, hierarchical, graph, Mixture-of-Agents, GroupChat, ForestSwarm, HeavySwarm, SwarmRouter и т.д.).
- **Лицензия**: `pyproject.toml` → **Apache-2.0** (`license = "Apache-2.0"`). Коммерчески friendly.
- **Entrypoint**: `swarms/cli/main.py` (`swarms = "swarms.cli.main:main"`). Python package `swarms/`.
- **Структура**: `swarms/agents/` (спец-агенты: ReflexionAgent, GKPAgent, ReasoningDuo, AgentJudge, SkillsManager…), `swarms/structs/` (**60+ swarm-архитектур** + `agent.py` — базовый Agent 164KB!), `swarms/tools/` (`base_tool.py` 111KB!, `mcp_manager.py`, `computer_use.py`, `handoffs_tool.py`), `swarms/prompts/`, `swarms/telemetry/`, `swarms/schemas/`.

## Agent loop
- **`structs/agent.py`** (`class Agent`, line 136): `_run()` (line 1235) — **ReAct loop** с `max_loops` (число или `"auto"` — агент сам решает когда остановиться, line 531/1378). Ядро: `while (max_loops=="auto" or loop_count < max_loops):` (line 1377) → `call_llm` → `parse_llm_output` → `short_memory.add` → обработка `handoff_task` tool calls → `execute_tools`. **Retry**: `while attempt < self.retry_attempts and not success` (line 1435) вокруг LLM-call. Встроенный **reasoning prompt** (REACT_SYS_PROMPT) при `max_loops>=2` или auto (line 625).

## Tool system
- **`tools/base_tool.py`** (`BaseTool` + кастомные exceptions: BaseToolError, ToolValidationError, ToolExecutionError, ToolNotFoundError). Схемы из pydantic/функций → OpenAI-function schema (`pydantic_to_json`, `get_openai_function_schema_from_func`). **Параллельное исполнение**: `_execute_function_calls_parallel` (line 2694) + `execute_tool_by_name`, `max_workers` (default 4, line 2198). Computer use: `tools/computer_use.py`. Handoffs: `handoffs_tool.py` (делегирование другому агенту).

## Planning / Execution
- Planning через спец-агентов (`agent_judge`, `reasoning_agent_router`, `planner_generator_evaluator.py` — `class PlannerGeneratorEvaluator`, line 143, `.run()` line 785). Execution-структуры: `SequentialWorkflow`, `ConcurrentWorkflow`, `GraphWorkflow` (DAG), `AgentRearrange`, `MixtureOfAgents`, `GroupChat`, `HierarchicalSwarm`, `HeavySwarm` (5-phase: Research/Analysis/Alternatives/Verification), `SwarmRouter`.

## Model abstraction
- **litellm** (pyproject: `litellm = "1.76.1"`) — единая абстракция 100+ провайдеров. `LLMManager` (`agents/llm_manager.py`). `model_name` строкой.

## Multi-agent / Orchestration
- **Главная сила**. `structs/` содержит 60+ swarm-паттернов. Примеры: `sequential_workflow.py`, `concurrent_workflow.py`, `graph_workflow.py`, `groupchat.py`, `hierarchical_swarm.py`, `heavy_swarm.py`, `mixture_of_agents.py`, `swarm_router.py`, `forest_swarm.py`, `tree_swarm.py`, `agent_rearrange.py`. Это **каталог готовых оркестраций**.

## Error recovery / Observability
- `retry_attempts` (per-loop), `ToolExecutionError` handling, `autosave` trajectory (`to_dict`, `save`), `telemetry/` (OpenTelemetry: `opentelemetry-sdk`), context compression (`context_compressor.py` в agents).

## Оценки (0-5)
| AGENT LOOP | TOOLS | COMPUTER USE | BROWSER | MEMORY | RESEARCH | MULTI-AGENT | VOICE | UI | LONG TASKS | MCP | LICENSE | VALUE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 4 | 3(computer_use) | 2 | 3(short/long mem) | 3 | 5(60+ structs) | 0 | 0 | 3(autosave/max_loops=auto) | 3(mcp_manager) | 5(Apache-2.0) | 4 |

## Ключевые механизмы для JARVIS
- **`max_loops="auto"` + ReAct + reasoning prompt** (`structs/agent.py`) → REIMPLEMENT: агент сам завершает итерации по stopping-condition. Хорошо для open-ended desktop-задач. Сложность: низкая.
- **`handoffs_tool.py`** → REIMPLEMENT: делегирование задачи другому агенту как tool-call. База для multi-agent в desktop. Сложность: средняя.
- **Каталог swarm-структур** (`structs/*.py`) → **ADAPT как reference**: выбрать 3-4 паттерна (Sequential, Concurrent, Hierarchical, Graph) для JARVIS orchestration. Сложность: средняя (это готовые blueprint'ы).
- **Параллельный tool-exec** (`_execute_function_calls_parallel`) → REIMPLEMENT. Сложность: низкая.

## Риски/ограничения
- `structs/agent.py` (164KB) и `base_tool.py` (111KB) — монолитные, тяжело читать/адаптировать напрямую; брать паттерны, не копипастить.
- Качество кода неравномерное (huge files).

---

# DONOR: pydantic-ai

## Идея / лицензия / entrypoint / структура
- **Идея**: Type-safe agent framework на базе **pydantic-graph** (state machine из узлов). Строгая типизация, structured output, instrumented (OTel), durable execution, MCP.
- **Лицензия**: `LICENSE` — MIT (короткий файл, проверено). Коммерчески friendly.
- **Entrypoint**: `pydantic_ai_slim/pydantic_ai/` (package). `Agent`, `ToolManager`, `Toolset`.
- **Структура**: `_agent_graph.py` (graph-based loop), `agent/` (subpackage), `tool_manager.py`, `tools.py`, `toolsets/`, `_tool_execution.py`, `_mcp.py`, `durable_exec/`, `capabilities/`, `concurrency.py`, `run.py`.

## Agent loop
- **Graph-based, не while-loop!** `pydantic_graph` (`BaseNode`, `End`, `Graph`). Узлы: **`UserPromptNode`** (line 501), **`ModelRequestNode`** (line 1106), **`CallToolsNode`** (line 1816), `EndNode` (line 2297, `return End(final_result)`). `UserPromptNode.run` возвращает `ModelRequestNode` или `CallToolsNode` (line 598/614/656/700) — **это transition между узлами = agent loop как state machine**. `GraphAgentState` (line 299: `run_step`, `check_incomplete_tool_call`), `GraphAgentDeps`. `EndStrategy` (line 99: early/graceful/exhaustive).
- Main entry: `run.py` (`AgentRun`, граф-раннер), `run_sync`/`arun`.

## Tool system
- **`tool_manager.py`** (`class ToolManager`, line 143): `toolset: AbstractToolset` (line 146). **Динамические toolsets**: `async def for_run_step(ctx)` (line 187) — инструменты пересчитываются **per step** (dynamic tool discovery, `discovered_tool_names`). `toolsets/abstract.py` (`AbstractToolset`, `ToolsetTool`), `OutputToolset`, `WrapperToolset` (напр. CodeModeToolset диспатчит). `tools.py` — `FunctionTool`/`ToolProvider`.

## Planning / Execution
- Не planner-ориентирован (general agent). Execution = узлы графа; параллелизм через `concurrency.py`. **Durable execution** (`durable_exec/`) — возобновляемые runs (state сохраняется между шагами).

## Model abstraction
- `models/` (в `pydantic_ai_slim/pydantic_ai/models` через зависимости), provider-плагины. `durable_exec` для long-running.

## Multi-agent / Orchestration
- Через граф + tool-delegation; явного Team-примитива меньше, чем у agno/swarms. `capabilities/` для расширения.

## Error recovery / Observability
- **Graph-based cancellable runs** (`_cancel.py`), `GraphTaskRequest`/`JoinItem` (параллельные ветви), `incomplete_tool_call` detection (token-limit exceeded при генерации tool-call аргументов, line 345), **OTel instrumentation** (`_instrumentation.py`, `_otel_messages.py`), `_history_processor.py`, retries (`retries.py`).

## Оценки (0-5)
| AGENT LOOP | TOOLS | COMPUTER USE | BROWSER | MEMORY | RESEARCH | MULTI-AGENT | VOICE | UI | LONG TASKS | MCP | LICENSE | VALUE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5(graph) | 4(dynamic) | 1 | 1 | 2 | 2 | 2 | 0 | 0 | 4(durable) | 4(_mcp) | 5(MIT) | 4 |

## Ключевые механизмы для JARVIS
- **Graph-based agent loop** (`_agent_graph.py`: `ModelRequestNode`→`CallToolsNode`→`End`) → **REIMPLEMENT**: agent loop как явная state machine. Преимущество для desktop: легко вставлять узлы (approval, human-in-loop, pause), детерминированный control-flow, resume после crash. Сложность REIMPLEMENT: средняя-высокая, но архитектурно чище чем while-loop.
- **Dynamic toolsets `for_run_step`** (`tool_manager.py` line 187) → REIMPLEMENT: инструменты, доступные агенту, могут меняться каждый шаг (context-aware tool visibility). Идеально для desktop (показывать file-тулы только когда агент в файловой задаче). Сложность: средняя.
- **Durable execution** (`durable_exec/`) → REIMPLEMENT для long tasks (pause/resume при перезапуске desktop). Сложность: высокая.
- **Incomplete tool-call detection** (line 345) → ADAPT (как у openclaw tool-call-repair, но на уровне schema-validation).

## Риски/ограничения
- Тяжёлая зависимость от `pydantic_graph` (отдельный пакет) — для JARVIS возможен свой упрощённый граф.
- Меньше готовых browser/computer-use тулов (не его фокус).

---

# DONOR: swe-agent

## Идея / лицензия / entrypoint / структура
- **Идея**: Agent для **SWE-bench** (решение GitHub-issue → патч). Action/observation loop в изолированном окружении (docker).
- **Лицензия**: `LICENSE` — MIT (короткий, проверено). Коммерчески friendly.
- **Entrypoint**: `sweagent/__main__.py`, `sweagent/run/`.
- **Структура**: `sweagent/agent/` (`agents.py` — `DefaultAgent`/`AbstractAgent`, `models.py`, `action_sampler.py`, `history_processors.py`, `reviewer.py`, `hooks/`), `sweagent/environment/` (bash/docker), `sweagent/tools/` (`ToolHandler`), `sweagent/run/`, `sweagent/inspector`.

## Agent loop
- **`agent/agents.py`** (`AbstractAgent.run`, line 390): **action/observation loop** — `while not step_output.done:` (line 413) → `self.step()` → `save_trajectory` → `on_submit` (review) → `retry()` (если ScoreRetryLoop/ChooserRetryLoop). History processors модифицируют контекст (`history_processors.py`: `tag_tool_call_observations`).
- `DefaultAgent.step` (line 328): вызывает `_agent.step()` (в `agents.py` line 1235 — `def step`), обрабатывает tool_calls, `max_requeries` (line 1107) при ошибке формата.

## Tool system
- **`sweagent/tools/`** (`ToolHandler`) — команды bash, поиск, редактирование файлов. `ToolHandler` парсит/валидирует вызовы. Инструменты привязаны к `environment` (bash/docker).

## Planning / Execution
- Планирование через промпт-стратегию (system prompt с инструкциями). `Reviewer` (`reviewer.py`) верифицирует патч (score/chooser retry-loops).

## Model abstraction
- **`agent/models.py`** (`AbstractModel`): унифицированный интерфейс к LLM, `tool_calls` из response (line 769-773, 859-862). Retry-лупы на уровне модели (`while True` line 398/407/451).

## Multi-agent / Orchestration
- Нет (single-agent, заточенный под SWE).

## Error recovery / Observability
- **Retry loops**: `RetryLoop` (ScoreRetryLoop, ChooserRetryLoop), `max_requeries` при плохом формате tool-call, **cost-limit** guard (`TotalCostLimitExceededError`, line 336/369), trajectory save (`.traj` JSON), `Reviewer` verification, `_catch_errors`.

## Оценки (0-5)
| AGENT LOOP | TOOLS | COMPUTER USE | BROWSER | MEMORY | RESEARCH | MULTI-AGENT | VOICE | UI | LONG TASKS | MCP | LICENSE | VALUE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4(action/obs) | 3 | 4(bash/docker) | 0 | 2(traj) | 1 | 0 | 0 | 1(inspector) | 3(cost-limit/retry) | 0 | 5(MIT) | 3 |

## Ключевые механизмы для JARVIS
- **Action/observation loop + trajectory (.traj)** (`agent/agents.py`) → REIMPLEMENT: чистый separation «agent предлагает action → env исполняет → observation возвращается». Хорошо для desktop (env = filesystem/shell). Trajectory = audit log. Сложность: низкая.
- **RetryLoop (Score/Chooser) + cost-limit guard** → REIMPLEMENT: автоматический повтор при неудаче + жёсткий бюджет (критично для desktop, где LLM-вызовы = деньги). Сложность: низкая-средняя.
- **`history_processors`** (`tag_tool_call_observations`) → ADAPT: пост-обработка истории перед следующим шагом (компрессия/тегирование observation). Сложность: низкая.

## Риски/ограничения
- Узко заточен под SWE (bash/docker env). Для general-purpose desktop нужен свой `environment` (OS-level).
- Нет planning/multi-agent из коробки.

---

# DONOR: camel

## Идея / лицензия / entrypoint / структура
- **Идея**: Multi-agent framework для «society of agents» (role-playing, исследования, задачи). Огромный каталог agents/toolkits/environments.
- **Лицензия**: `LICENSE` — Apache-2.0 (проверено, 11KB). Коммерчески friendly.
- **Entrypoint**: `camel/` (Python package). `ChatAgent`, `Society`, `RoleAssignmentAgent`.
- **Структура**: `camel/agents/` (chat_agent, critic_agent, role_assignment_agent, search_agent, task_agent, repo_agent, mcp_agent, multi_hop_generator_agent…), `camel/societies/` (`role_playing.py` → `Society`, `workforce/`), `camel/toolkits/` (~80 toolkits: browser, code_execution, excel, arxiv…), `camel/models/`, `camel/memories/`, `camel/messages/`, `camel/environments/`, `camel/tasks/`, `camel/runtimes/`, `camel/verifiers/`, `camel/prompts/`.

## Agent loop
- **`agents/chat_agent.py`** (`class ChatAgent`, line 366): `step()` (line 2896) — single turn: `_step_impl` → model → tool-calling loop (`while True` line 3005/3311/4457/5468 — **inner tool-call loop**: «if tool calls → `_record_tool_calling` → execute → append result → repeat»). **Pause/resume**: `pause_event` (line 3012/3102 — `while not self.pause_event.is_set()`). Timeout: `step_timeout` через ThreadPoolExecutor (line 2908).

## Tool system
- **`toolkits/base.py`** (`Toolkit`) + множество специализированных (browser_toolkit, code_execution, excel, arxiv, async_browser_toolkit, hybrid_browser_toolkit). Декоратор-based регистрация (`@tool`/register). Расширяемость: subclass `Toolkit` + добавить методы.

## Planning / Execution
- **`societies/role_playing.py`** (`Society`): `with_task_planner` (line 100/281) → `TaskPlannerAgent.run` генерирует `planned_task_prompt` (line 291). **Role assignment**: `RoleAssignmentAgent` (`agents/role_assignment_agent.py`) автоматически распределяет роли агентам. Это **planning через task-planner + role-play**.

## Model abstraction
- **`camel/models/`** — `ModelFactory`, множество backend (openai, anthropic, ollama, gemini, mistral…). `model_config_dict`.

## Multi-agent / Orchestration
- **Сильная сторона**. `Society` (role_playing) = несколько `ChatAgent` с ролями, общаются в цикле (`step` line 631). `workforce/` (laboratory/workforce) — иерархическая оркестрация (manager + worker agents). `RoleAssignmentAgent` для динамического распределения.

## Error recovery / Observability
- `step_timeout`, `pause_event`, `verifiers/` (верификация ответов), `critic_agent.py` (self-critique), `memories/` (долгосрочная память).

## Оценки (0-5)
| AGENT LOOP | TOOLS | COMPUTER USE | BROWSER | MEMORY | RESEARCH | MULTI-AGENT | VOICE | UI | LONG TASKS | MCP | LICENSE | VALUE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 4(80 toolkits) | 2(code_exec) | 4(browser) | 4(memories) | 4 | 5(Society/workforce) | 1 | 2(apps) | 3(pause/timeout) | 3(mcp_agent) | 5(Apache-2.0) | 4 |

## Ключевые механизмы для JARVIS
- **Inner tool-call loop в `ChatAgent.step`** (`chat_agent.py` line 3005) → REIMPLEMENT: вложенный цикл «пока есть tool_calls → execute → repeat», пока модель не даст финальный ответ. Чистый паттерн. Сложность: низкая.
- **`pause_event` (threading.Event)** (`chat_agent.py` line 3012) → REIMPLEMENT: pause/resume агента из GUI. Сложность: низкая.
- **`RoleAssignmentAgent` + `TaskPlannerAgent` + `Society`** (`societies/role_playing.py`, `agents/role_assignment_agent.py`) → ADAPT: автоматическое планирование задачи и распределение ролей между агентами. Отлично для desktop multi-agent. Сложность: средняя.
- **`workforce/` иерархия** → ADAPT как blueprint hierarchical orchestration.

## Риски/ограничения
- Огромный (много устаревшего/экспериментального кода в `toolkits/`). Брать паттерны, не зависимости целиком.
- Меньше focus на single-agent runtime качестве (чем agno/pydantic-ai).

---

# DONOR: mirothinker

## Идея / лицензия / entrypoint / структура
- **Идея**: **Deep research agent** (BrowseComp 88.2). Оптимизирован под research/prediction, «interactive scaling». Open-source веса (MiroThinker-1.7 и т.д.).
- **Лицензия**: `LICENSE` — Apache-2.0 (10KB, проверено; copyright MiroMind). Коммерчески friendly (но веса моделей могут иметь свои условия).
- **Entrypoint**: `apps/miroflow-agent/main.py` (hydra + asyncio), `apps/gradio-demo/`, `apps/collect-trace/`, `libs/miroflow-tools/`.
- **Структура**: `apps/miroflow-agent/src/` (`core/`: `orchestrator.py`, `pipeline.py`, `tool_executor.py`, `answer_generator.py`, `stream_handler.py`; `io/`; `llm/`; `logging/`; `config/`; `utils/`), `libs/miroflow-tools/src/miroflow_tools/` (MCP servers: browser, python, search, reasoning, vision, audio), `conf/` (yaml-конфиги агентов/llm, включая `multi_agent.yaml`, `single_agent.yaml`).

## Agent loop
- **`src/core/orchestrator.py`** (`class Orchestrator`, line 86): управляет execution loop для main и sub-agents. `run_sub_agent` (line 327) — `while turn_count < max_turns and total_attempts < max_attempts` (line 390) с **retry/rollback protection** (`consecutive_rollbacks`, line 398/224/250 — «Ending agent loop after N consecutive rollbacks»). Main loop координирует tool-calls + sub-agent delegation.
- **`pipeline.py`**: `create_pipeline_components` (ToolManager фабрика) + `execute_task_pipeline`.

## Tool system
- **MCP-first**: `libs/miroflow-tools/` — набор MCP-серверов (`browser_session.py`, `python_mcp_server.py`, `searching_google_mcp_server.py`, `reasoning_mcp_server.py`, `vision_mcp_server.py`, `audio_mcp_server.py`). Tool определяется как MCP-server. `ToolManager` управляет ими.
- Sub-agents экспонируются как tools (`_list_tools` line 56, `wrapped()` — sub-agent вызывается как tool из main-agent).

## Planning / Execution
- **Multi-agent configs**: `conf/agent/multi_agent.yaml`, `multi_agent_os.yaml`, `single_agent.yaml`. Planning через конфигурацию (hydra). Tool-call-driven execution с rollback при format-errors.

## Model abstraction
- **`src/llm/`**: `base_client.py`, `factory.py`, `providers/` (anthropic_client, openai_client). Абстракция провайдера через factory.

## Multi-agent / Orchestration
- **Сильная/интересная**: main-agent оркестрирует sub-agents, которые сами — отдельные агенты с лимитами (`max_turns`, `max_attempts`). Sub-agent = tool для main-agent. Это **delegation-as-tool паттерн** в чистом виде.

## Error recovery / Observability
- **Consecutive rollback protection** (format errors/refusals) — `orchestrator.py` line 224/250/397. `task_logger.py`, `summary_time_cost.py` (cost tracking). Duplicate query check (`_check_duplicate_query` line 257) — защита от циклов поиска.

## Оценки (0-5)
| AGENT LOOP | TOOLS | COMPUTER USE | BROWSER | MEMORY | RESEARCH | MULTI-AGENT | VOICE | UI | LONG TASKS | MCP | LICENSE | VALUE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 4(MCP) | 2(python) | 4(browser MCP) | 1 | 5(BrowseComp) | 4(sub-agent delegation) | 1(audio MCP) | 2(gradio) | 3(rollback protect) | 5(MCP-native) | 5(Apache-2.0) | 4 |

## Ключевые механизмы для JARVIS
- **Sub-agent-as-tool delegation** (`orchestrator.py` `_list_tools`/`run_sub_agent`) → REIMPLEMENT: main-agent делегирует подзадачи sub-агентам, вызывая их как инструменты. Чистый паттерн multi-agent для desktop (напр. «research-subagent», «file-subagent»). Сложность: средняя.
- **MCP-native tool servers** (`libs/miroflow-tools/`) → ADAPT: каждый tool = отдельный MCP-сервер (browser/python/search/reasoning). Изоляция, расширяемость без правки core. Сложность: средняя.
- **Rollback/duplicate-query protection** (`orchestrator.py`) → REIMPLEMENT: защита от бесконечных loop'ов поиска/формат-ошибок. Критично для long-running desktop. Сложность: низкая.

## Риски/ограничения
- Заточен под research (browser/search heavy). Для general-purpose desktop нужны OS-тулы (не только browser/python).
- Меньше готового single-agent runtime (это «agent config + orchestrator» поверх MCP).

---

# ЛУЧШИЕ МЕХАНИЗМЫ AGENT RUNTIME / PLANNING

Синтез: какой подход к **agent loop, tool registry, planning, multi-agent, error recovery** лучше всего подходит для **desktop general-purpose agent (JARVIS)**.

## 1. AGENT LOOP
**Победитель: граф-based (pydantic-ai) как архитектура + ReAct/auto-loops (swarms/agno) как практика.**

- **pydantic-ai `_agent_graph.py`** (`ModelRequestNode` → `CallToolsNode` → `End`): agent loop как **явная state machine**. Для desktop это лучше чем `while`-loop, потому что: (a) легко вставить узлы approval/human-in-loop/pause между model и tools; (б) детерминированный control-flow; (в) естественный resume после crash.
- **Дополнение от swarms** (`structs/agent.py` `_run`, `max_loops="auto"` + `REACT_SYS_PROMPT`): агент сам решает когда остановиться (stopping-condition) — идеально для open-ended desktop-задач без фиксированного числа шагов.
- **Дополнение от camel** (`chat_agent.py` inner tool-call loop line 3005): вложенный цикл «пока есть tool_calls → execute → repeat» внутри одного step — чистый паттерн обработки multi-tool-calls.
- **REIMPLEMENT для JARVIS**: гибрид — graph из 3 узлов (Think→Act→Observe), где Act-узел содержит inner tool-call loop, а переход Think→Act управляется `max_loops="auto"` + stopping-condition.

## 2. TOOL REGISTRY / EXTENSIBILITY
**Победитель: agno `Registry` + `@tool` decorator + pydantic-ai dynamic toolsets.**

- **agno `registry/registry.py`** (`Registry` class, `_entrypoint_lookup`): центральный каталог tools/models/agents с flat + qualified (toolkit,name) keys. Добавить tool = зарегистрировать `Function` (`tools/decorator.py` `@tool` → `tools/function.py` `Function`). **Без правки core.**
- **pydantic-ai `tool_manager.py`** `ToolManager.for_run_step(ctx)` (line 187): **dynamic toolsets** — инструменты пересчитываются каждый шаг → context-aware tool visibility (desktop: file-тулы только в файловых задачах).
- **REIMPLEMENT для JARVIS**: `@tool` decorator → `Function` объект (со schema, doc, injected-params) → регистрация в центральном `Registry` (dict name→Function). `ToolManager` возвращает актуальный список tool-схем **per step** (dynamic). Новый tool добавляется одним decorator-ом.

## 3. PLANNING
**Победитель: autogpt `prompt_strategies` (strategy-pattern) + agno `Workflow`/`Team` + camel `TaskPlanner`/`RoleAssignment`.**

- **autogpt `prompt_strategies/`** (`plan_execute.py`, `reflexion.py`, `rewoo.py`, `lats.py`, `tree_of_thoughts.py`, `multi_agent_debate.py`): planning как **сменяемая стратегия**. Для JARVIS: переключатель стратегии под тип задачи (план-исполнение для сложных, one-shot для простых).
- **agno `workflow/`** (DAG execution) + **camel `societies/role_playing.py` `TaskPlannerAgent`** (line 291 генерирует `planned_task_prompt`): planner отдельным агентом.
- **REIMPLEMENT для JARVIS**: Planner-агент (отдельный LLM-call) генерирует структурированный план (список шагов + назначение sub-agent'ам) → Executor исполняет. Стратегия выбирается по сложности задачи (default: plan-execute, fallback: one-shot ReAct).

## 4. MULTI-AGENT ORCHESTRATION
**Победитель: mirothinker (sub-agent-as-tool) + agno `Team` (leader-delegation) + swarms (каталог структур) + camel `workforce` (hierarchical).**

- **mirothinker `orchestrator.py`** (`_list_tools`/`run_sub_agent` line 56/327): sub-agent экспонируется как **tool** main-agent'а. Самый чистый паттерн delegation — не нужен отдельный orchestrator-протокол, sub-agent вызывается через tool-call.
- **agno `team/team.py`** (`Team`, `delegate_to_all_members`, `add_team_history_to_members`): leader-агент делегирует подзадачи members, поддержка вложенных teams.
- **swarms `structs/`** (60+ blueprint'ов: SequentialWorkflow, ConcurrentWorkflow, GraphWorkflow, HierarchicalSwarm, HeavySwarm) — **готовый каталог** для выбора топологии.
- **camel `workforce/`** — иерархия manager+workers.
- **REIMPLEMENT для JARVIS**:
  1. Базовый паттерн = **mirothinker sub-agent-as-tool** (desktop: «research-subagent», «filesystem-subagent», «browser-subagent» вызываются как tools из main-agent).
  2. Для сложных задач = **agno Team** (leader планирует, делегирует workers).
  3. Топологию брать из **swarms** (Sequential для pipeline, Concurrent для параллельного сбора, Hierarchical для менеджмента).

## 5. ERROR RECOVERY / OBSERVABILITY
**Победитель: agno (RunStatus + fallback + OTel) + openclaw (tool-call-repair + net-policy) + swe-agent (retry-loops + cost-limit) + mirothinker (rollback protection).**

- **agno `run/base.py` `RunStatus`** (CREATED/RUNNING/COMPLETED/**PAUSED**/**CANCELLED**/FAILED) + `run/cancel.py` (`raise_if_cancelled`) + `models/fallback.py` `FallbackConfig` (error-specific routing: 429→model A, context-exceeded→model B, non-retryable 401/403 не маскируются) + **OTel tracing** (`tracing/`). → **Эталон для desktop long-tasks + модельного fallback'а.**
- **openclaw `tool-call-repair/`** (`parseStandalonePlainTextToolCallBlocks`, `stream-normalizer.ts`): восстановление некорректных/plain-text tool-calls модели. + `net-policy` (SSRF/redact) для безопасности desktop.
- **swe-agent `RetryLoop` (Score/Chooser) + `TotalCostLimitExceededError`** (line 336): авто-retry + жёсткий бюджет (критично: LLM-вызовы = деньги).
- **mirothinker `orchestrator.py`** `consecutive_rollbacks` + `_check_duplicate_query`: защита от бесконечных loop'ов формат-ошибок/поиска.
- **REIMPLEMENT для JARVIS**:
  1. `RunStatus` (PAUSED/CANCELLED) + cancel-токен в каждом step → GUI-кнопки Stop/Pause.
  2. `FallbackConfig` error-specific → локальная модель (fast) + облачная (quality) с авто-switch.
  3. `tool-call-repair` → парсинг некорректных tool-calls (без падения агента).
  4. `RetryLoop` + cost-limit guard → авто-retry с бюджетом.
  5. `rollback`/`duplicate-query` protection → защита от loop'ов.
  6. OTel tracing → observability в desktop UI.

## 6. MODEL ABSTRACTION
- **agno `models/`** (40+ провайдеров + `litellm` + `fallback.py`) и **swarms `litellm`** — эталон. **pydantic-ai / camel / mirothinker** — factory-паттерн.
- **REIMPLEMENT**: `Model` ABC + provider-плагины (OpenAI/Anthropic/Ollama/local) + `FallbackConfig` из agno.

## 7. SECURITY / PERMISSIONS
- **autogpt** (`execute()` permission check line 385) + **openclaw `net-policy`** (SSRF/redact) + **agno `approval.py`** (human approval перед tool) + **agno `guardrails/`**.
- **REIMPLEMENT для desktop**: permission-prompt перед опасными операциями (rm, сеть, exec) + SSRF-фильтр локальных IP + approval-gate для admin-tools.

## ИТОГОВАЯ РЕКОМЕНДАЦИЯ ДЛЯ JARVIS (REIMPLEMENT-набор)

| Механизм | Donor-источник | Файл(ы) | Сложность |
|---|---|---|---|
| Agent loop (graph: Think→Act→Observe + inner tool-loop + auto-stop) | pydantic-ai + swarms + camel | `_agent_graph.py`, `structs/agent.py`, `chat_agent.py` | Средняя |
| Tool registry (`@tool`→`Function`→`Registry` + dynamic per-step) | agno + pydantic-ai | `registry/registry.py`, `tools/decorator.py`, `tool_manager.py` | Низкая |
| Planner (strategy-pattern + TaskPlanner agent) | autogpt + camel + agno | `prompt_strategies/`, `societies/role_playing.py`, `workflow/` | Низкая-Средняя |
| Multi-agent (sub-agent-as-tool + Team + топологии) | mirothinker + agno + swarms | `orchestrator.py`, `team/team.py`, `structs/*.py` | Средняя |
| Error recovery (RunStatus + fallback + tool-call-repair + retry + cost-limit + rollback) | agno + openclaw + swe-agent + mirothinker | `run/base.py`, `models/fallback.py`, `tool-call-repair/`, `RetryLoop`, `orchestrator.py` | Низкая-Средняя |
| Model abstraction (ABC + 40 провайдеров + FallbackConfig) | agno | `models/` | Низкая |
| Security (permission + SSRF + approval) | autogpt + openclaw + agno | `agent.py execute`, `net-policy/`, `approval.py` | Низкая |
| Observability (OTel tracing + trajectory) | agno + swe-agent | `tracing/`, `sweagent .traj` | Средняя |
| Pause/Resume (pause_event + durable exec) | camel + pydantic-ai | `chat_agent.py pause_event`, `durable_exec/` | Средняя |

**Лицензии (все safe для закрытого коммерческого JARVIS)**: agno(Apache-2.0), swarms(Apache-2.0), pydantic-ai(MIT), swe-agent(MIT), camel(Apache-2.0), mirothinker(Apache-2.0), openclaw(MIT), openhands(MIT). ⚠️ **autogpt — гибрид**: брать ТОЛЬКО `classic/` (Apache-2.0), НЕ `autogpt_platform/` (Polyform Shield License — коммерчески закрытый).

**Главный вывод**: ни один donor не идеален целиком, но **комбинация** даёт production-grade desktop runtime:
- **Loop/State**: pydantic-ai graph + swarms auto-loops.
- **Tools**: agno Registry + pydantic-ai dynamic toolsets.
- **Planning/Orchestration**: autogpt strategies + mirothinker sub-agent-as-tool + agno Team.
- **Resilience**: agno RunStatus/fallback + openclaw tool-call-repair + swe-agent retry/cost + mirothinker rollback.
- Все паттерны — **REIMPLEMENT** (не copy code), лицензии совместимы.
