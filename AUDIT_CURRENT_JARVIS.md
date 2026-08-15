# CURRENT JARVIS AUDIT

> Read-only аудит реального исходного кода проекта `E:\jarvis-project`.
> Дата аудита: 2026-08-15. Прочитаны реально: `main.py`, `core/**` (все модули),
> `config/**`, `persona/**`, `hud/**`, `scripts/` (имена), `jarvis/**` (frontend),
> `jarvis-ui/**` (старый UI), `docs/**`, `pyproject.toml`, `requirements.txt`, `data/**`.
>
> ВАЖНО про существующие файлы аудита на диске (`audit_agent_runtime.md`,
> `audit_report.md`, `final_report.json`): они описывают НЕ этот проект, а
> **донорские репозитории** (`E:\jarvis-donors`: agent-zero, openhands, agno,
> swe-agent, camel, pydantic-ai, ui-tars-desktop, browser-use, browsergym и т.д.).
> В `final_report.json` запакован текст `audit_agent_runtime.md` целиком. Это
> контекст для синтеза архитектуры, а НЕ описание текущего состояния JARVIS.
> Все утверждения ниже проверены по реальным файлам проекта и, где нужно,
> расходятся с теми документами.

## 1. Структура проекта (дерево каталогов)

```
E:\jarvis-project\
├── main.py                 # точка входа: консольный REPL, баннер, signal handlers, интерактивные команды
├── pyproject.toml          # метаданные пакета, deps (границы), entry-point jarvis=main:main
├── requirements.txt        # точные версии; llama-cpp-python ставится отдельно (нет wheel на Windows)
├── config/
│   ├── settings.py         # Settings (pydantic): api_keys/endpoints/tiers/providers/local/voice/limits
│   ├── settings.json       # рабочий конфиг
│   └── settings.example.json
├── core/                   # ЯДРО агента (Python, без langchain/langgraph)
│   ├── agent.py            # Agent: контроллер миссии (intent→risk→mode→plan→exec→verify→repair)
│   ├── orchestrator.py     # Orchestrator: синхронный цикл REPL + асинхронные submit_goal/миссии
│   ├── model_router.py     # ModelRouter: выбор тира по сложности (regex-оценка)
│   ├── state.py            # JarvisState, Message, ActionResult-контейнеры
│   ├── structured.py       # parse_structured / validate_tool_call (JSON-решение модели)
│   ├── capabilities.py     # CapabilityRegistry: паспорта инструментов + TOOL RETRIEVAL (§12)
│   ├── safety.py           # assess_risk: RISK-классификация (LOW/MEDIUM/HIGH)
│   ├── verifier.py         # verify_action_result: фактическая проверка результата (§14)
│   ├── repair.py           # RepairLoop: self-healing при ошибке
│   ├── research.py         # ResearchEngine: отдельный research-конвейер (§18)
│   ├── skill_forge.py      # SkillForge: черновики/навыки (§9, §29)
│   ├── ingest.py           # chunking больших входов (§7)
│   ├── llm/                # LLM-абстракция
│   │   ├── backend.py      # LLMBackend (ABC) + исключения + нормализация сообщений
│   │   ├── factory.py      # get_llm_backend с кэшем инстансов
│   │   ├── local_qwen.py   # LocalQwenBackend: llama-cpp-python, Qwen3-4B
│   │   ├── remote_api.py   # RemoteAPIBackend: OpenAI-compatible + Anthropic dialect
│   │   └── tiers.py        # Tier enum + ESCALATION_ORDER (FAST→ANALYST→CODER→ARCHITECT)
│   ├── actions/            # Движок инструментов
│   │   ├── base.py         # Tool (ABC), ToolContext, ActionResult
│   │   ├── registry.py     # ToolRegistry + DEFAULT_REGISTRY
│   │   ├── executor.py     # execute_tool: валидация JSON Schema + retry
│   │   ├── app_control.py  # open_app / close_app (Windows, psutil)
│   │   ├── system.py       # volume / system_status (pycaw/pyautogui)
│   │   ├── web_search.py   # DuckDuckGo (requests)
│   │   ├── web_fetch.py    # скачивание+чистка страницы (bs4)
│   │   ├── filesystem.py   # list/read/write/search файлов (documents_dir)
│   │   ├── reminders.py    # add/list/cancel напоминаний
│   │   └── weather.py      # open-meteo
│   ├── memory/             # Слои памяти
│   │   ├── embedder.py     # Embedder (ChromaDB DefaultEmbeddingFunction, all-MiniLM-L6-v2)
│   │   ├── long_term.py    # ChromaDB long-term
│   │   ├── document_rag.py # ChromaDB RAG по документам
│   │   ├── knowledge_graph.py # граф знаний (SQLite)
│   │   ├── profile.py      # профиль пользователя (JSON)
│   │   ├── retrieval.py    # MemoryRetriever: сбор контекста из всех слоёв
│   │   └── short_term.py   # SessionManager (история сообщений)
│   ├── router/             # Совет мудрецов
│   │   ├── council.py      # CouncilRouter: keyword→local_face.classify→self/escalate
│   │   ├── local_face.py   # LocalFace: Qwen как «лицо», classify (JSON)
│   │   ├── intent_router.py # resolve_keyword_tool: keyword-категоризация (app/web/file/...)
│   │   └── tier_resolver.py # resolve_next_available_tier
│   ├── voice/              # Голос
│   │   ├── tts.py          # PiperTTS (реальный субпроцесс к piper.exe)
│   │   ├── tts_queue.py    # TTSQueue (очередь, pause/resume)
│   │   ├── stt.py          # STTEngine — ЗАГЛУШКА (NotImplementedError)
│   │   └── notifications.py # show_toast (pywin32)
│   ├── proactive/          # Проактивность
│   │   ├── proactor.py     # Proactor: фоновый цикл «скучающего» таймера + напоминания
│   │   └── background_tasks.py # BackgroundScheduler (ночная консолидация — заглушка)
│   └── utils/              # logger, paths, model_manager
├── persona/
│   ├── persona.md          # системный промпт-персона (Джарвис, саркастичный, «сёр»)
│   └── system_prompt.py
├── hud/
│   └── settings_panel_stub.py # SettingsPanel — ПУСТАЯ ЗАГЛУШКА (GUI не реализован)
├── scripts/                # диагностические/тестовые .py (много .pyc в __pycache__)
├── jarvis/                 # НОВЫЙ frontend: Tauri 2 + React + TypeScript (vite)
│   ├── src/                # App.tsx, компоненты (Atmosphere, ActivityStream, Composer...)
│   ├── src/integrations/backend.ts  # createMockBackend() — МОК-адаптер (скриптованный таймлайн)
│   ├── src/hooks/useBackendBridge.ts # точка интеграции frontend↔backend (использует МОК)
│   └── src-tauri/          # Rust-каркас Tauri, НО main.rs почти пустой (только window_effects)
├── jarvis-ui/              # СТАРЫЙ frontend: Tauri + React (отдельный репозиторий, .git)
│   ├── src/hooks/useIPC.ts # реальные invoke('send_query') к Tauri-командам
│   ├── src-tauri/src/main.rs # Tauri-команды: send_query/confirm_action/cancel_task — ЗАГЛУШКИ (println)
│   └── src/stores/*        # zustand-сторы (chatStore, appStore, settingsStore)
├── data/                   # реальные данные
│   ├── models/qwen3-4b-instruct-q5_k_m.gguf  # 2.9 ГБ — РЕАЛЬНАЯ модель (присутствует)
│   ├── models/piper/*.onnx # 2 голоса Piper (jarvis-medium, ru_RU-dmitri) — РЕАЛЬНЫЕ
│   ├── memory/chroma.sqlite3, data/memory/<uuid>/  # ChromaDB long-term (реальные файлы)
│   ├── documents/.chroma/  # ChromaDB документный
│   ├── graph/jarvis_graph.db # граф знаний (SQLite)
│   ├── ingest/JARVIS-2026-00005/ # пример ингеста
│   ├── profile/profile.json
│   ├── skills/отрендери_взрыва_в_blender_и.md # один навык от SkillForge
│   └── logs/jarvis.log      # активный лог (270 КБ)
└── docs/
    ├── jarvis_core_architecture.md  # описание «J.A.R.V.I.S. 3.0» архитектуры (самодокументация)
    ├── JARVIS_COMMAND_LIBRARY.md
    └── progress_report.md
```

## 2. Карта компонентов

| Компонент | Файл/модуль | Статус | Назначение |
|---|---|---|---|
| Entrypoint REPL | `main.py` | works | консольный цикл, signal, интерактивные команды |
| Orchestrator (sync) | `core/orchestrator.py` `handle_input` | works | синхронный виток REPL: intake→memory→council→tool→TTS |
| Orchestrator (async) | `core/orchestrator.py` `submit_goal` | works (изолирован) | асинхронные миссии через TaskRuntime |
| CouncilRouter | `core/router/council.py` | works | keyword→classify→self/escalate, graceful fallback |
| LocalFace | `core/router/local_face.py` | works | Qwen как «лицо», classify по JSON |
| Intent router | `core/router/intent_router.py` | works | keyword-категоризация (6 категорий) |
| ModelRouter | `core/model_router.py` | works | сложность→тир (regex) |
| LocalQwenBackend | `core/llm/local_qwen.py` | works | llama-cpp Qwen3-4B, реально грузит GGUF |
| RemoteAPIBackend | `core/llm/remote_api.py` | works | OpenAI+Anthropic, retry/backoff |
| LLM factory | `core/llm/factory.py` | works | кэш бэкендов |
| Agent (mission loop) | `core/agent.py` | works | intent→risk→mode→plan→exec→verify→repair |
| Capabilities/retrieval | `core/capabilities.py` | works (keyword) | паспорта + TOOL RETRIEVAL по тегам |
| Tool registry/executor | `core/actions/*` | works | 14 инструментов, JSON-Schema валидация, retry |
| Memory: long_term/RAG | `core/memory/long_term.py`, `document_rag.py` | works (если chromadb есть) | ChromaDB векторная память |
| Memory: embedder | `core/memory/embedder.py` | works | ChromaDB all-MiniLM |
| Memory: graph | `core/memory/knowledge_graph.py` | works | SQLite граф |
| Memory: profile/short-term | `core/memory/profile.py`, `short_term.py` | works | профиль JSON, сессия |
| Memory: retrieval | `core/memory/retrieval.py` | works | сбор контекста из слоёв |
| Verifier | `core/verifier.py` | works (частично) | проверка результата, регистрируемые verifier'ы |
| Repair loop | `core/repair.py` | works | self-healing (fallback-инструменты) |
| Research engine | `core/research.py` | partial | research-конвейер, зависит от web_search |
| Skill forge | `core/skill_forge.py` | partial | создаёт черновики навыков, materialization НЕТ |
| Ingest | `core/ingest.py` | works | chunking больших входов |
| Safety/risk | `core/safety.py` | works | оценка риска (HIGH→подтверждение) |
| TTS (Piper) | `core/voice/tts.py`, `tts_queue.py` | works | субпроцесс к piper.exe, очередь |
| STT | `core/voice/stt.py` | **mock/stub** | NotImplementedError, stt_enabled=False |
| Notifications | `core/voice/notifications.py` | partial | show_toast (pywin32, зависит от ОС) |
| Proactor | `core/proactive/proactor.py` | works | «скучающий» таймер + напоминания |
| Background scheduler | `core/proactive/background_tasks.py` | **stub** | `_nightly_consolidation` — заглушка (TODO) |
| TaskRuntime | `core/task_runtime.py` | works | Mission, EventBus, статусы, watchdog=None |
| HUD/SettingsPanel | `hud/settings_panel_stub.py` | **stub** | пустой класс, GUI не реализован |
| jarvis/ frontend (Tauri+React) | `jarvis/` | **mock** (UI only) | красивый UI, но backend = МОК-адаптер |
| jarvis-ui/ (old Tauri+React) | `jarvis-ui/` | **dead/legacy** | отдельный репозиторий, Tauri-команды = заглушки |
| Artifact generation | — | **ОТСУТСТВУЕТ** | нет docx/pptx/pdf-генераторов |
| Computer control (screenshot/mouse/keyboard) | `core/actions/system.py` (pyautogui fallback) | **partial/accidental** | только fallback громкости; нет screenshot/координат/CUA |
| Browser automation | `core/actions/web_fetch.py` | **partial** | только fetch URL, НЕТ Playwright/set-of-marks/CUA |
| Streaming | `core/llm/*` `streaming()` | **dead** | методы есть, НИГДЕ не вызываются (TTS/UI не потребляют) |
| Instant acknowledgement | `core/agent.py` `pick_acknowledgement` | **dead** | детерминированный ACK есть, но НЕ вызывается из REPL-пути |

## 3. Что реально работает (проверено по коду)

- **LLM-backend абстракция** (`core/llm`): чистый `LLMBackend` ABC, две реализации
  (`LocalQwenBackend` на llama-cpp, `RemoteAPIBackend` OpenAI+Anthropic dialects), фабрика с
  кэшем, retry/backoff. Это самая зрелая часть. Реально грузит `data/models/qwen3-4b...gguf`.
- **Совет мудрецов / роутинг** (`core/router`): `CouncilRouter.route()` — keyword intent →
  `LocalFace.classify()` (Qwen решает self/escalate) → graceful эскалация с fallback на
  локальную. Хорошая обработка ошибок (нет исключений наружу).
- **Инструменты** (`core/actions`): 14 зарегистрированных инструментов, рабочий `execute_tool`
  с JSON-Schema валидацией и retry. `open_app`/`close_app` реально запускают/закрывают Windows-
  процессы (исправлен баг shlex на Windows-путях). `volume`/`system_status` реально работают
  (pycaw/psutil). `web_search` (DuckDuckGo), `web_fetch` (bs4), filesystem, reminders, weather —
  реальные реализации.
- **Многослойная память** (`core/memory`): ChromaDB long-term + RAG + graph (SQLite) +
  profile + short-term. `MemoryRetriever` собирает контекст устойчиво (per-layer try/except).
  `data/memory/chroma.sqlite3` и граф-БД реально существуют и записывались.
- **TTS (Piper)**: `PiperTTS` реально вызывает `piper.exe` субпроцессом, 2 голоса в
  `data/models/piper/` присутствуют.
- **Agent mission loop** (`core/agent.py`): полноценный цикл intent→risk→mode→plan→exec→
  verify→repair с fast-path и research-веткой. Хорошая философия (§4 нет time-limit, §14
  verify-before-done, §29 unknown≠impossible).
- **Safety/risk, verifier, repair, ingest, skill_forge(draft)**: все реализованы на уровне
  структур. `TaskRuntime` даёт Mission/EventBus/статусы.
- **Proactor**: фоновый «скучающий» таймер + напоминания работают.
- **Данные**: модель 2.9 ГБ, голоса Piper, ChromaDB, граф — всё на месте.

## 4. Что частично

- **Research engine** (`core/research.py`, 418 строк): движок cross-check/synthesize написан,
  но `ResearchEngine.run` внутри зовёт `get_llm_backend` и web-инструменты; без сети/ключей
  деградирует. `is_research_goal()` — простой keyword-детектор.
- **SkillForge** (`core/skill_forge.py`): создаёт/сохраняет черновики навыков (markdown +
  frontmatter), `match()` ищет по триггерам. Но **materialization/выполнение навыка отсутствует**
  — навык никогда не «становится рабочим способом», только draft. В `data/skills` — один
  пример-черновик.
- **Verifier** (`core/verifier.py`): инфраструктура `register_verifier`/`has_strict_verifier`
  есть, но **строгие verifier'ы зарегистрированы только для file-инструментов**
  (`verify_file_exists`); остальные — `strict=False` (честно пишет «проверка: …» без факта).
- **Notifications** (`notifications.py`): `show_toast` через pywin32, зависит от ОС; в
  `orchestrator._default_output` вызывается только если `voice.tts_enabled`.
- **Computer control**: единственное упоминание `pyautogui` — в `core/actions/system.py` как
  **fallback для громкости** (нажатие клавиш volumemute/volumeup). Нет screenshot, нет
  координатного CUA, нет UIA/AX. Это НЕ computer-use в смысле аудита.
- **Browser automation**: только `web_fetch` (скачать URL + bs4-чистка). Нет Playwright,
  нет set-of-marks, нет click-by-selector, нет браузерного CUA.

## 5. Mock / Stub

- **`core/voice/stt.py`** — `STTEngine` полностью заглушка: `stt_enabled=False`, методы
  бросают `NotImplementedError`. Голосовой ВВОД отсутствует.
- **`core/proactive/background_tasks.py` → `_nightly_consolidation`** — заглушка (TODO),
  только лог. Реальной ночной консолидации/самообучения нет.
- **`hud/settings_panel_stub.py`** — пустой класс `SettingsPanel`. GUI/HUD не реализован.
- **`jarvis/src/integrations/backend.ts` → `createMockBackend()`** — МОК-адаптер:
  скриптованный таймлайн (setTimeout), `createRealBackend()` просто возвращает тот же мок.
  `jarvis/src/hooks/useBackendBridge.ts` подключён к моку. **Новый красивый UI не имеет
  связи с реальным Python-бэкендом.**
- **`jarvis-ui/src-tauri/src/main.rs`** — Tauri-команды `send_query`/`confirm_action`/
  `cancel_task` — заглушки (`println!("[JARVIS] ...")`, возвращают `"Query received"`).
  `jarvis-ui/src/hooks/useIPC.ts` реально дёргает эти invoke, но бэкенд ничего не делает.
- **`jarvis/src-tauri/src/main.rs`** — почти пустой (только `window_effects`), invoke_handler
  не зарегистрирован → новый UI вообще не имеет транспорта к Python.

## 6. Dead code / неиспользуемое

- **ДВЕ параллельных архитектуры обработки** (главный dead-weight):
  - **Путь A (REPL)**: `main.py` → `Orchestrator.handle_input()` → `CouncilRouter.route()`
    (keyword+local_face classify, единый chat-вызов модели, TOOL_CALL regex-парсинг, 1
    итерация reask). **Это то, что реально работает в консоли.**
  - **Путь B (async missions)**: `Orchestrator.submit_goal()` → `TaskRuntime` →
    `Agent.run_mission()` → `_decide_with_model()` (второй LLM-call для плана) →
    `CAPABILITIES.retrieve()` → `_execute_verified()` → verifier → repair.
    **`submit_goal` НИГДЕ не вызывается** (ни в `main.py`, ни в frontend). Весь богатый
    Agent (planning, repair, skill_forge, research) — мёртвый код с точки зрения работающего
    REPL. Две системы intent-routing (`resolve_keyword_tool` в A и B), две системы model-
    routing (`CouncilRouter` в A и `ModelRouter` в B) дублируют друг друга и **расходятся**.
- **`LLMBackend.streaming()`** во всех трёх бэкендах — реализован, но **никем не вызывается**
  (ни TTS, ни UI, ни orchestrator). Streaming функционально мёртв.
- **`pick_acknowledgement` / `ACK_PHRASES`** (`core/agent.py`) — мгновенный ACK есть, но
  вызывается только внутри мёртвого `submit_goal`. В работающем REPL-пути пользователь
  ждёт ПОЛНОГО ответа модели молча. **Instant acknowledgement отсутствует в живом пути.**
- **`primary_brain` (settings)** — поле добавлено в `config/settings.py` (`primary_brain=
  "analyst"`, комментарий «ГЛАВНЫЙ МОЗГ»), но **НИГДЕ не читается** ни `CouncilRouter`, ни
  `ModelRouter`. Мёртвая конфигурация.
- **`jarvis-ui/`** — целый второй frontend-проект (отдельный git), дублирующий `jarvis/`.
  Его Tauri-команды — заглушки. Кандидат на удаление.
- **`core/llm/tiers.py` `next_tier`/`tier_purpose`** — экспортируются, но мало используются
  (логика эскалации живёт в `council.py`/`tier_resolver.py`).
- **`ModelRouter`** (`core/model_router.py`) — используется ТОЛЬКО в мёртвом пути B
  (`Agent._decide_with_model`→`ModelRouter.route`). В живом пути A роутинг делает
  `CouncilRouter`.

## 7. Архитектурные блокирующие факторы

1. **Две конфликтующие архитектуры в одном репозитории** (`orchestrator.py` строки 144–196
   vs 202–272; `agent.py` vs `council.py`). Живой путь A (CouncilRouter) и мёртвый путь B
   (Agent) используют РАЗНЫЕ intent-классификаторы и РАЗНЫЕ model-router'ы. Невозможно
   развивать оба: любое изменение роутинга надо дублировать. → Нужно выбрать ОДИН путь
   (рекомендую: путь B как ядро, путь A — как fast/sync обёртка поверх него).
2. **Frontend полностью оторван от бэкенда.** `jarvis/` — красивый React/Tauri UI, но
   `backend.ts` = мок, `main.rs` пуст. `jarvis-ui/` — второй UI с заглушками-командами.
   Нет ни одного реального транспорта (Tauri invoke / WebSocket / IPC) от UI к Python.
   Блокирует коммерческий десктоп-продукт целиком.
3. **Нет стриминга в живом пути.** `streaming()` есть, но `handle_input`/`CouncilRouter`
   ждут полного `chat()` и печатают разом. Пользователь видит ответ только после
   генерации целиком → ощущение «зависания».
4. **Instant acknowledgement отсутствует в живом пути.** Реализован (`pick_acknowledgement`),
   но только в мёртвом `submit_goal`. В REPL пользователь молча ждёт 10+ сек на простой
   вопрос (см. §8).
5. **`primary_brain` задекларирован, но не подключён** — стратегия «remote-first vs
   local-first» не реализована фактически; `CouncilRouter` всегда стартует с local_face.
6. **Tight coupling Orchestrator↔конкретные классы.** `Orchestrator.__init__` жёстко
   инстанцирует `CouncilRouter`, `Agent`, `PiperTTS`, `TTSQueue`, `Proactor`,
   `BackgroundScheduler`, `MemoryRetriever` (cтроки 67–97). Нет dependency injection /
   интерфейса. Невозможно подменить backend или отключить модуль без правки ядра.
7. **Tool-calling через regex-маркер `TOOL_CALL:{...}`** (`orchestrator.py` строки 44–47,
   333–376) вместо нативного function calling. LocalQwenBackend имеет `supports_tools=False`.
   Это хрупко (модель может не вернуть маркер), лимит 1 итерация reask.
8. **Нет artifact generation** (docx/pptx/pdf) — блокирует ключевой сценарий «сгенерируй
   презентацию/документ».
9. **Нет computer-use / browser CUA** — только слабые зачатки (pyautogui fallback громкости,
   web_fetch). Блокирует сценарии «кликни туда / заполни форму / сравни цены в браузере».

## 8. Latency bottlenecks

- **Главный**: в живом REPL-пути (`handle_input`) на ПРОСТОЙ вопрос (например «привет»)
  вызывается `CouncilRouter.route()` → `LocalFace.classify()` (ВТОРОЙ вызов модели,
  хотя для intent app/system/none он shortcut'ится в `local_face.py:167` и возвращает self
  БЕЗ вызова — ОК) → затем `LocalFace.respond()` (ТРЕТИЙ/основной вызов) на Qwen3-4B 2.9ГБ
  на CPU (`n_gpu_layers=0` по умолчанию в `settings.py:173`). На CPU Qwen3-4B генерирует
  медленно → **пользователь ждёт 10+ сек молча**, без ACK и без стрима.
  Проверка: `settings.py` `local_model.n_gpu_layers=0`, `local_latency_target_sec=1.5` (только
  телеметрия, не влияет). `LimitsConfig.response_timeout_sec=15` — но это таймаут, а не
  индикатор.
- **Отсутствие ACK в живом пути** (см. §7.4): даже если модель быстрая, UI не показывает
  «принято/думаю» до первого токена.
- **Memory retrieval до каждого ответа** (`handle_input` строка 165 → `MemoryRetriever.
  retrieve`): ChromaDB embed + поиск по 3 коллекциям на КАЖДЫЙ запрос, включая «привет».
  Без кэширования эмбеддинга query.
- **Двойной LLM-call в мёртвом пути B**: `classify` + `respond` (council) И `decide_with_
  model` (agent). Если путь B когда-то оживят — latency удвоится.
- **`response_timeout_sec=15`** на удалённый вызов (`remote_api.py:82`) — при недоступном
  провайдере 3 retry с exp backoff (до 10с) × 15с таймаут = потенциально 45с молчания.

## 9. Tight coupling

- `Orchestrator` жёстко связан с `CouncilRouter`, `Agent`, `PiperTTS`, `TTSQueue`, `Proactor`,
  `MemoryRetriever` (прямые импорты + инстанциация в `__init__`). Нет абстракции/DI.
- `CouncilRouter` знает про `LocalFace`, `tier_resolver`, `intent_router`, `local_qwen`
  напрямую; `LocalFace` знает про `LLMBackend` и `settings.limits`.
- `Agent` дублирует intent (`resolve_keyword_tool`) и model-routing (`ModelRouter`) вместо
  переиспользования `CouncilRouter` → две копии логики роутинга, которые расходятся.
- `capabilities.py` копирует список инструментов из `actions/` вручную (`_CAPABILITY_LIST`)
  вместо генерации из `ToolRegistry` → рассинхрон (добавишь tool в `actions/`, забудешь в
  `capabilities.py`). Сейчас списки совпадают, но поддержка хрупкая.
- `core/llm/factory.py` `_build_backend` вручную ищет тир по `model_tiers` (строки 64–68) —
  хрупкая обратная зависимость.

## 10. Модельная зависимость / routing проблемы

- **Локальная модель жёстко зашита как Qwen3-4B 4B** в `settings.py` (`fast="qwen-4b-local"`,
  `gguf_path="...qwen3-4b-instruct-q4_k_m.gguf"`), хотя на диске лежит `qwen3-4b-instruct-
  q5_k_m.gguf` (несовпадение q4/q5 — старый путь в конфиге!). `LocalQwenBackend` не имеет
  нативного function-calling (`supports_tools=False`) → весь tool-calling идёт через regex.
- **Роутинг в живом пути**: `CouncilRouter` всегда стартует с local_face; `LocalFace.
  classify` shortcut'ит app/system/media/none → self (без вызова модели), но web/browser/
  file идут через Qwen-classify (доп. вызов). `decision.tier` из classify (analyst/coder/
  architect) используется как запрошенный тир при escalate. Это работает, НО:
  - **model_id'ы в `settings.py` — вымышленные**: `analyst="deepseek-v4-flash"`,
    `coder="kimi-k3"`, `architect="claude-opus-5"` (таких моделей нет у провайдеров). Без
    реальных ключей/endpoint'ов все внешние тиры `is_tier_available=False` → graceful
    fallback на локальную. То есть **реально работает ТОЛЬКО локальная Qwen3-4B**; «совет
    мудрецов» деградирует до single-model.
  - `ModelRouter` (в мёртвом пути B) оценивает сложность regex'ом и выбирает тир, но
    `private`-логика (§15 «приватное → только локально») опирается на keyword
    «пароль/снилс/ssn» — легко обходится, нет семантической фильтрации.
- **Противоречие в конфиге**: `primary_brain="analyst"` (комментарий «ГЛАВНЫЙ МОЗГ,
  удалённая модель основной ответчик») vs реальное поведение `CouncilRouter` (локальная
  всегда первична). Стратегия не реализована → конфиг врёт о поведении.

## 11. Расширяемость Tool системы

**Частично расширяема, но с трением:**
- Добавить НОВЫЙ tool = создать класс `Tool` в `core/actions/`, зарегистрировать в
  `DEFAULT_REGISTRY` (в `app_control.py` и др. сделано через `DEFAULT_REGISTRY.register` при
  импорте). Импорт в `core/actions/__init__.py` обязателен.
- **НО** чтобы tool появился в retrieval/planning (путь B), надо ещё дописать `Capability`
  вручную в `core/capabilities.py:_CAPABILITY_LIST` (дублирование описания/тегов/риска).
  Забудешь — модель его не увидит в пути B.
- В живом пути A tool-calling идёт через regex `TOOL_CALL` в ответе модели + `_maybe_
  execute_tool` (1 итерация). Новый tool должен уметь вызываться этим механизмом.
- **Писать tool нужно вручную** (нет декоратора `@tool`, нет авто-генерации schema из
  типов, нет MCP-слоя). «Добавить tool без переписывания core» — условно да, НО: schema
  дублируется в 2 местах (`Tool.input_schema` и `Capability`), risk/теги — в 3-м. Нет
  централизованного реестра метаданных. Для коммерческого продукта нужен декларативный
  реестр (один источник правды) + опционально MCP-адаптер.

## 12. Ключевые выводы

1. **Бэкенд-ядро (LLM, routing, tools, memory, TTS) — удивительно зрелое** для «сырого»
   проекта: чистые абстракции, graceful degradation, реально грузящаяся модель и голоса.
   Это спасаемый фундамент.
2. **Главная проблема — раскол на две архитектуры** (CouncilRouter-REPL vs Agent-missions)
   и **полное отсутствие связи frontend↔backend**. Продукт «не собирается»: UI — мок,
   Tauri-команды — заглушки.
3. **Latency-проблема «10+ сек молча» реальна**: CPU-Qwen3-4B + отсутствие ACK/стриминга в
   живом пути + memory-retrieval на каждый «привет». Лечится: GPU-слои (n_gpu_layers=-1),
   включить `pick_acknowledgement` в живой путь, включить `streaming()` в оркестратор/UI,
   кэшировать query-embedding.
4. **Модельная зависимость**: реально работает только локальная Qwen3-4B; «совет мудрецов»
   деградирует до single-model из-за вымышленных model-id и отсутствия ключей. Нужны
   реальные model-id + provider-abstraction уже есть (готово к подключению ключей).
5. **Отсутствуют ключевые возможности коммерческого desktop-agent**: STT (голосовой ввод),
   computer-use (screenshot/CUA), browser automation (Playwright), artifact generation
   (docx/pptx), ночная консолидация. Всё это — net-new, архитектура ядра их НЕ блокирует,
   но и не облегчает (нет CUA-интерфейса, нет MCP).
6. **Tool-система расширяема, но с ручным дубляжом метаданных** — нужен единый декларативный
   реестр + декоратор, иначе поддержка развалится при росте числа tools.
7. **`jarvis-ui/` — мёртвый дубликат** старого UI; рекомендуется удалить, оставив `jarvis/`
   как единственный frontend и подключив к нему реальный Python-транспорт.
8. **Документация на диске (`audit_*.md`, `final_report.json`) вводит в заблуждение** —
   это аудит доноров, а не текущего проекта. Для синтеза новой архитектуры использовать
   как источник паттернов (agno/pydantic-ai/swe-agent), но НЕ как описание JARVIS.
9. **Спасать**: `core/llm/*`, `core/router/council.py`, `core/actions/*`, `core/memory/*`,
   `core/voice/tts.py`, `config/settings.py`, `persona/`. **Переписывать/консолидировать**:
   `orchestrator.py` (слить пути A/B), `agent.py` (сделать единственным ядром), frontend-
   транспорт (с нуля), `capabilities.py` (слить с `ToolRegistry`), добавить STT/CUA/
   browser/artifacts.
10. **Рекомендация по маршрутизации намерений**: текущий `resolve_keyword_tool` (6 категорий,
    regex) — слишком грубый для «general-purpose». Для новой архитектуры: лёгкий локальный
    классификатор (уже есть `LocalFace`) + семантический retrieval tools (уже есть
    `CAPABILITIES`) — основа хорошая, но нужно убрать дублирование с `ModelRouter`.

## 13. Конкретные пути к файлам, которые важно знать

- `E:\jarvis-project\main.py` — точка входа, REPL, интерактивные команды (строки 63–216).
- `E:\jarvis-project\core\orchestrator.py` — ДВЕ архитектуры: `handle_input` (строки 144–196,
  живой путь A) и `submit_goal`/`_mission_runner` (строки 202–295, мёртвый путь B).
- `E:\jarvis-project\core\agent.py` — мёртвый путь B; `pick_acknowledgement` (строки 87–93,
  детерминированный ACK, не используется в живом пути); `_decide_with_model` (строки 458+).
- `E:\jarvis-project\core\router\council.py` — `CouncilRouter.route` (строки 111–183),
  `_handle_escalate` (строки 207–250) — живая логика роутинга.
- `E:\jarvis-project\core\router\local_face.py` — `classify` (строки 132–234), shortcut
  intent→self (строка 167).
- `E:\jarvis-project\core\router\intent_router.py` — `resolve_keyword_tool` (строки 87–107).
- `E:\jarvis-project\core\model_router.py` — `ModelRouter.route` (строки 228–291), только
  в мёртвом пути B.
- `E:\jarvis-project\core\llm\local_qwen.py` — `LocalQwenBackend`, `supports_tools=False`
  (строка 58), загрузка GGUF.
- `E:\jarvis-project\core\llm\remote_api.py` — `RemoteAPIBackend`, retry/backoff (строки 260+).
- `E:\jarvis-project\core\llm\factory.py` — `get_llm_backend` (строки 88–124), кэш.
- `E:\jarvis-project\core\actions\registry.py`, `executor.py`, `base.py` — Tool-система.
- `E:\jarvis-project\core\capabilities.py` — `_CAPABILITY_LIST` (строки 103–244, ручной
  дубликат инструментов), `retrieve` (строки 300–342).
- `E:\jarvis-project\core\actions\app_control.py` — `open_app`/`close_app` (реальные,
  Windows), `_BUILTIN_APPS` (строки 39–84).
- `E:\jarvis-project\core\actions\system.py` — `volume`/`system_status`; `pyautogui` только
  как fallback громкости (строки 46–53, 98–160) — единственное упоминание computer-control.
- `E:\jarvis-project\core\voice\stt.py` — ЗАГЛУШКА (`NotImplementedError`).
- `E:\jarvis-project\core\voice\tts.py` — `PiperTTS` (реальный субпроцесс).
- `E:\jarvis-project\core\memory\retrieval.py` — `MemoryRetriever.retrieve` (строки 88–148),
  вызывается на КАЖДЫЙ запрос.
- `E:\jarvis-project\config\settings.py` — `Settings`, `primary_brain` (строка 394, мёртвый),
  `is_tier_available` (строки 458–485), вымышленные model-id (строки 132–135),
  `n_gpu_layers=0` (строка 173, CPU).
- `E:\jarvis-project\jarvis\src\integrations\backend.ts` — `createMockBackend` (МОК, строки 37–181).
- `E:\jarvis-project\jarvis\src\hooks\useBackendBridge.ts` — подключён к моку (строка 21).
- `E:\jarvis-project\jarvis\src-tauri\src\main.rs` — почти пустой (только window_effects).
- `E:\jarvis-project\jarvis-ui\src-tauri\src\main.rs` — Tauri-команды = заглушки (строки 6–57).
- `E:\jarvis-project\jarvis-ui\src\hooks\useIPC.ts` — реальный `invoke('send_query')`.
- `E:\jarvis-project\hud\settings_panel_stub.py` — пустая заглушка GUI.
- `E:\jarvis-project\docs\jarvis_core_architecture.md` — самодокументация «J.A.R.V.I.S. 3.0»
  (полезна, но описывает идеал, а не всегда реальность — сверяться с кодом).
- `E:\jarvis-project\audit_agent_runtime.md`, `audit_report.md`, `final_report.json` —
  аудит ДОНОРОВ (`E:\jarvis-donors`), НЕ текущего проекта. Не путать.
```
