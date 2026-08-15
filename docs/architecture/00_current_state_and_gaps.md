# 00 — Текущее состояние J.A.R.V.I.S. и архитектурные разрывы

> Источники: `AUDIT_CURRENT_JARVIS.md` (AGENT A) + прямое чтение `core/**`,
> `jarvis/**` + `audit_model_tool_ui_security.md` (AGENT F). Это НЕ доноры —
> это текущее ядро. Дата аудита: 2026-08-15.

## 1. Структура проекта (дерево)

```
E:\jarvis-project\
├── main.py                 # REPL entrypoint, signal handlers, интерактивные команды
├── pyproject.toml          # deps (границы), entry-point jarvis=main:main
├── config/
│   ├── settings.py         # Settings (pydantic): api_keys/endpoints/tiers/providers/voice/limits
│   └── settings.json       # рабочий конфиг
├── core/                   # ЯДРО (Python, без langchain/langgraph)
│   ├── agent.py            # Agent: контроллер миссии (intent→risk→mode→plan→exec→verify→repair)
│   ├── orchestrator.py     # Orchestrator: синхронный REPL + асинхронные submit_goal/миссии
│   ├── model_router.py     # ModelRouter: выбор тира по сложности (regex-оценка)
│   ├── state.py            # JarvisState, Message, ActionResult-контейнеры
│   ├── structured.py       # parse_structured / validate_tool_call (JSON-решение модели)
│   ├── capabilities.py     # CapabilityRegistry: паспорта инструментов + TOOL RETRIEVAL (§12)
│   ├── safety.py           # assess_risk: RISK-классификация (LOW/MEDIUM/HIGH) + prompt-injection
│   ├── verifier.py         # verify_action_result: ФАКТИЧЕСКАЯ проверка результата (core/verifier.py)
│   ├── repair.py           # RepairLoop: self-healing при ошибке (§8/§9)
│   ├── research.py         # ResearchEngine: отдельный research-конвейер (core/research.py)
│   ├── skill_forge.py      # SkillForge: черновики/навыки (§9, core/skill_forge.py)
│   ├── ingest.py           # chunking больших входов (§7)
│   ├── llm/                # LLM-абстракция
│   │   ├── backend.py      # LLMBackend (ABC) + исключения + нормализация
│   │   ├── factory.py      # get_llm_backend с кэшем инстансов
│   │   ├── local_qwen.py   # LocalQwenBackend: llama-cpp, Qwen3-4B (Tier.FAST)
│   │   ├── remote_api.py   # RemoteAPIBackend: OpenAI-compatible + Anthropic (ANALYST/CODER/ARCHITECT)
│   │   └── tiers.py        # Tier enum + ESCALATION_ORDER (FAST→ANALYST→CODER→ARCHITECT)
│   ├── actions/            # Движок инструментов
│   │   ├── base.py         # Tool (ABC), ToolContext, ActionResult
│   │   ├── registry.py     # ToolRegistry + DEFAULT_REGISTRY
│   │   ├── executor.py     # execute_tool: валидация JSON Schema + retry
│   │   ├── app_control.py  # open_app / close_app (Windows, psutil)
│   │   ├── system.py       # volume / system_status
│   │   ├── web_search.py   # DuckDuckGo
│   │   ├── web_fetch.py    # скачивание+чистка (bs4)
│   │   ├── filesystem.py   # list/read/write/search
│   │   ├── reminders.py    # add/list/cancel напоминаний
│   │   └── weather.py      # open-meteo
│   ├── memory/             # Слои памяти
│   │   ├── embedder.py     # Embedder (ChromaDB DefaultEmbeddingFunction, all-MiniLM-L6-v2)
│   │   ├── long_term.py    # ChromaDB long-term
│   │   ├── document_rag.py # RAG по документам
│   │   └── retrieval.py    # retrieval-слой
│   ├── voice/              # Голос
│   │   ├── tts.py          # PiperTTS (локальный)
│   │   ├── tts_queue.py    # TTSQueue (очередь, не блокирует)
│   │   └── stt.py          # ЗАГЛУШКА (NotImplementedError)
│   ├── proactive.py        # proactive/background поведение
│   └── task_runtime.py     # TaskRuntime: EventBus, Mission, MissionRunner, watchdog
├── persona/                # system prompts, persona
├── hud/                    # head-up display backend?
├── jarvis/                 # Tauri 2 + React + TS фронтенд
│   ├── src/                # App.tsx, components/ActivityStream, useBackendBridge, stores
│   └── src-tauri/          # Rust backend (main.rs — почти пустой)
├── jarvis-ui/              # старая версия UI (не используется)
├── docs/                   # документация (вкл. jarvis_core_architecture.md)
└── data/                   # documents, chroma, etc.
```

## 2. Карта компонентов (статус по коду)

| Компонент | Файл/модуль | Статус | Назначение |
|-----------|-------------|--------|-----------|
| Tool base + registry | `core/actions/registry.py` | ✅ works | `Tool`(ABC)+`ToolRegistry`+`ToolContext`+`ActionResult` |
| Capability registry | `core/capabilities.py` | ✅ works | паспорта + `retrieve(goal, top_k)` (keyword-скоринг) |
| Safety / risk gating | `core/safety.py` | ✅ works | `assess_risk`(LOW/MED/HIGH)+`wrap_untrusted` |
| Verifier | `core/verifier.py` | ✅ works | реестр фактических проверок (12 verifier-ов) |
| Repair loop | `core/repair.py` | ✅ works | diagnose→patch→LLM-reasoner→fallback→human |
| LLM backends | `core/llm/*` | ✅ works | `LocalQwenBackend`, `RemoteAPIBackend`, `factory`, `tiers` |
| Actions (14 tools) | `core/actions/*` | ✅ works | registry-базированные |
| Memory (RAG/vector) | `core/memory/*` | ✅ works | embedder, long_term, document_rag |
| Voice TTS | `core/voice/tts.py`+`tts_queue.py` | ✅ works | Piper, локально, очередь |
| Config | `config/settings.py` | ✅ works | зрелый pydantic |
| Frontend (event-timeline) | `jarvis/src/**` | ✅ works (UI) | но подключён к MOCK-бэкенду |
| ModelRouter | `core/model_router.py` | ⚠️ partial | считает тир, НО решение игнорируется в missions |
| Agent mission loop | `core/agent.py` | ⚠️ partial | переписан, НО routing сломан (см. §7.2) |
| Intent routing | `core/intent_router`/agent | ⚠️ partial | статический keyword, хрупкий |
| STT | `core/voice/stt.py` | 🔴 mock | `NotImplementedError` |
| Computer control | — | 🔴 absent | нет mouse/keyboard/screenshot |
| Browser automation | — | 🔴 absent | только web_fetch/web_search |
| Real backend bridge | `jarvis/src/integrations/backend.ts` | 🔴 mock | `createMockBackend()` жёстко |
| Artifact generation | — | 🔴 absent | нет презентаций/документов |
| `Agent.run_mission` async-путь | `core/agent.py` | 💀 dead | НЕ вызывается нигде (мёртвый код) |

## 3. Что реально РАБОТАЕТ (KEEP-ядро — сохранить при эволюции)

1. **Verifier** (`core/verifier.py`) — фактическая проверка: `write_file`→файл на
   диске, `open_app`→процесс жив, `web_fetch`→>50 символов, 12 специализированных
   verifier-ов + честный `strict=False` для trust_ok. Сильнее большинства доноров.
2. **RepairLoop** (`core/repair.py`) — self-healing: retry / LLM-патч аргументов /
   эвристика путей / fallback-tool / `permission_denied`→`needs_human`.
3. **Safety** (`core/safety.py`) — `assess_risk` двойной гейт (до планирования и
   перед выполнением), HIGH→подтверждение, EXE-паттерны. `auto_confirm_high_risk=False`.
4. **CapabilityRegistry** (`core/capabilities.py`) — опережающий многих доноров
   дизайн (risk/permissions/speed/fallbacks/success_check).
5. **ToolRegistry** (`core/actions/registry.py`) — расширяем без правки core.
6. **LLM abstraction** (`core/llm/*`) — чистый `LLMBackend`(ABC), `factory` с кэшем,
   `tiers.py` model-agnostic (model-id в settings, НЕ в коде).
7. **Memory** (`core/memory/*`) — RAG, ChromaDB, embedder (all-MiniLM-L6-v2).
8. **Fast-path / ACK** (`core/agent.py`) — `_try_fast_path` (open/close/volume/status)
   детерминированный, мгновенный; `pick_acknowledgement` без модели (§5).
9. **TaskRuntime / EventBus** (`core/task_runtime.py`) — миссии в daemon-потоке,
   `EventBus` публикует события, `watchdog` опционален (безлимит по умолчанию).

## 4. Что ЧАСТИЧНО

- `ModelRouter.route()` честно оценивает сложность и строит
  `RoutingDecision(tier, fallback_chain, forced_local)`, НО решение **не
  применяется** в `_decide_with_model` (см. §7.2).
- `Agent` переписан в mission loop, НО завязан на хардкод локальной модели.
- Tool retrieval — keyword-scoring (теги/имя/описание), без эмбеддингов →
  хромает на синонимах и длинных целях («поставь будильник» не найдёт
  `add_reminder`).
- Intent routing — статический keyword, нет семантики.

## 5. Mock / Stub

- `Agent.run_mission` async-путь — **заглушка-призрак**: нигде не вызывается.
- `core/voice/stt.py` — `NotImplementedError` (STT отключён).
- `jarvis/src/integrations/backend.ts` — `createMockBackend()` (скриптованный
  таймлайн); `createRealBackend()` возвращает мок. `useBackendBridge.ts:21`
  жёстко `const backend = createMockBackend()`. `src-tauri/main.rs` почти пустой.
  → UI полностью оторван от backend.
- `TaskRuntime.resume()` — только `PAUSED→EXECUTING`, НЕ несёт решение
  пользователя (HIGH-risk подтверждение НЕ замыкается, §7.3).

## 6. Dead code / неиспользуемое

- **Две конфликтующие архитектуры** (§7.1): живой REPL-путь
  (`Orchestrator.handle_input`→`CouncilRouter`) и мёртвый async-путь
  (`submit_goal`→`Agent.run_mission`). Весь богатый Agent (planning/repair/
  skill_forge/research) мёртв во втором пути. Две копии intent- и model-роутинга.
- `ModelRouter`/`tiers.py`/`remote_api.py`/`_is_available` — **мёртвы в основном
  цикле** (живут только в `CouncilRouter` для синхронного `handle_input`).

## 7. КРИТИЧЕСКИЕ блокирующие факторы

### 7.1 Две конфликтующие архитектуры в одном репозитории
- ЖИВОЙ: `Orchestrator.handle_input` → `CouncilRouter`.
- МЁРТВЫЙ: `submit_goal` → `Agent.run_mission` — **нигде не вызывается**.
- Две копии intent- и model-роутинга расходятся.
- **Решение:** убрать мёртвый путь, маршрутизировать `submit_goal` через единый
  mission loop (эволюция, не reset — KEEP-ядро сохраняется).

### 7.2 Routing не работает в миссиях (подтверждён по коду)
В `Agent.execute` (agent.py:249) `routing = self._model_router.route(goal)` —
решение ПРИНИМАЕТСЯ и пишется в `mission.model_used`. Но внутри
`_decide_with_model` (agent.py:468) `backend = self._get_local_backend()` →
`get_llm_backend(self._settings, Tier.FAST)` — **жёстко Tier.FAST**.
- **Итог:** планирование всегда на локальной Qwen3-4B. Тиры ANALYST/CODER/ARCHITECT
  никогда не используются. `ModelRouter` мёртв в основном цикле.
- **План фикса** (детально в `02_target_architecture.md` §1 + `audit_model_tool_ui_security.md` §1.3):
  заменить `_get_local_backend` на `_get_backend_for_tier`, пробегать
  `routing.fallback_chain` при `BackendUnavailable`, честно фиксировать
  `mission.model_used`, передать `routing` в `_handle_research`.

### 7.3 Подтверждение HIGH-risk НЕ замыкается (подтверждение HIGH-risk не замыкается)
`TaskRuntime.resume()` — заглушка. При `exec_risk.needs_confirmation` миссия
останавливается, НО никто не сохраняет `(tool, arguments)` и нет
`confirm_mission(task_id, approved)`. Фронтенд не обрабатывает
`confirmation_required`.
- **Решение:** `Orchestrator.confirm_mission` + хранение `pending_confirmation` в
  `mission.metadata`.

### 7.4 Дублирование метаданных tool-системы
`capabilities.py` вручную дублирует схемы `actions/*` → рассинхрон.
- **Решение:** единый источник truth — регистрация tool автоматически порождает
  capability-паспорт (см. `02` §2).

## 8. Latency bottlenecks

- Пользователь ждёт 10+ сек молча на простой вопрос: нет **instant
  acknowledgement** до тяжёлого планирования в основном пути.
- **Решение:** `ACKNOWLEDGING` мгновенно (без LLM) в `Orchestrator`, тяжёлая
  работа — в фоновый `MissionRunner` (уже есть `task_runtime.EventBus`).
- Нет backpressure: `TaskRuntime._missions` растёт без лимита. Добавить
  `max_concurrent` (≈3) + `QUEUED` статус.

## 9. Tight coupling

- `Agent._decide_*` жёстко завязан на локальную модель (§7.2).
- Tool retrieval привязан к keyword-скорингу (нет embedding-слоя).
- Intent routing дублируется в двух местах (§7.1).
- `verifier`/`repair`/`agent` логируют `args` без `redact_secrets()` → пароли/пути
  могут попасть в лог (добавить redact).

## 10. Расширяемость Tool-системы

- **Сейчас:** добавить tool можно через `ToolRegistry` (новый модуль в
  `core/actions/`, импорт в `__init__`), НО нужно вручную продублировать
  метаданные в `capabilities.py` (risk/speed/fallbacks). Точка трения.
- **Цель:** регистрация tool автоматически порождает capability-паспорт (single
  source of truth) + semantic retrieval (embedding поверх ChromaDB-эмбеддера).

## 11. Конкретные пути (важно знать)

```
core/actions/registry.py        — Tool, ToolRegistry, ToolContext, ActionResult
core/capabilities.py            — CapabilityRegistry, retrieve() (keyword)
core/safety.py                  — assess_risk, wrap_untrusted
core/verifier.py                — register_verifier, verify_action_result
core/repair.py                  — RepairLoop
core/llm/tiers.py               — model-agnostic tiers
core/llm/factory.py             — get_llm_backend (кэш)
core/model_router.py            — ModelRouter (не применяется в missions)
core/agent.py                   — mission loop + СЛОМАННЫЙ _decide_with_model (:468)
core/orchestrator.py            — Orchestrator.handle_input (живой REPL-путь)
core/task_runtime.py            — TaskRuntime, EventBus, Mission, resume() (заглушка)
core/voice/stt.py               — ЗАГЛУШКА
jarvis/src/integrations/backend.ts — createMockBackend (жёстко)
jarvis/src/hooks/useBackendBridge.ts — подписка на события (мок)
jarvis/src-tauri/main.rs       — почти пустой
```

## 12. Ключевые выводы

1. **Ядро зрелое** — `verifier`/`repair`/`safety`/`capabilities`/`registry`/`llm`/
   `memory` опережают большинство доноров. Это KEEP-ядро.
2. **Главный блокер** — две конфликтующие архитектуры + мёртвый routing. Богатый
   Agent (planning/repair/research) НЕ работает в миссиях.
3. **Rerouting сломан** — `ModelRouter` игнорируется, всегда локальная Qwen3-4B.
4. **Frontend оторван** — зрелый event-timeline UI, но на MOCK-бэкенде.
5. **Security почти не применяется** — `wrap_untrusted` только в `research.py`;
   веб/док/файл-контент идёт в модель без конверта (prompt-injection уязвимость).
6. **Computer-use / browser / STT / artifacts — отсутствуют** (целевые фазы).
7. **Лицензия** — 19 доноров reimplement-safe, 3 БЛОКЕРА (everywhere BSL 1.1,
   isair-jarvis non-commercial, khoj AGPL-3.0). См. `03_roadmap_and_license.md`.
