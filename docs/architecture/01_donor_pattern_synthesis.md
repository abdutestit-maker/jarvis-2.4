# 01 — Синтез паттернов доноров (REIMPLEMENT, не copy)

> Источники: `audit_computer_use_donors.md` (B), `AGENT_RUNTIME_AUDIT_DONORS.md` (C),
> `audit_memory_research_donors.md` (D, 🔲 ожидается), `audit_license_matrix.md` (E, 🔲).
> Принцип: адаптируем **паттерны и механизмы**, НЕ копируем код (лицензии).

## 1. Agent Loop — лучшие паттерны

| Паттерн | Donor | Где | Почему хорош | Адаптация |
|---------|-------|-----|--------------|-----------|
| Graph state-machine (ModelRequestNode→CallToolsNode→End) | pydantic-ai | `_agent_graph.py` | явный цикл, типобезопасный, лёгкий retry | ADAPT → заменить хрупкий keyword-intent |
| ReAct с `max_loops="auto"` | swarms | `swarms/structs/agent.py` | авто-остановка, нет «лимита 3 сек» | REIMPLEMENT |
| Внутренний tool-call loop | camel | `camel/agents/chat_agent.py` | вложенный planning внутри шага | REIMPLEMENT |
| Сменяемые planning-стратегии | autogpt | `prompt_strategies/` (plan_execute, reflexion, rewoo, lats) | стратегия = плагин | REIMPLEMENT |
| TaskPlannerAgent | camel | `TaskPlannerAgent` | отдельный планировщик | ADAPT |

**Синтез для JARVIS:** единый mission loop как state-machine (как pydantic-ai),
с REAct-итерациями внутри шага и сменяемой planning-стратегией (как autogpt).
Убрать мёртвый async-путь, объединить две копии routing.

## 2. Tool Registry — расширяемость

| Паттерн | Donor | Где | Почему хорош |
|---------|-------|-----|--------------|
| `@tool` → `Function` → `Registry` | agno | `agno/tools/`, `registry/registry.py` | декоратор + авто-схема |
| Динамические toolsets (`for_run_step`) | pydantic-ai | toolsets | контекстные тулзы на шаг |
| Декларативная регистрация | agent-zero | `agents/_example/tools/example_tool.py` | tool = python-модуль |

**Синтез для JARVIS:** `ToolRegistry` уже есть — надо устранить дублирование
метаданных (`capabilities.py` вручную дублирует `actions/*`). Единый источник
truth: регистрация tool автоматически порождает capability-паспорт.

## 3. Computer Use — лучший stack (Windows)

| Механизм | Donor | Лицензия | Где | Значение |
|----------|-------|----------|-----|----------|
| UI Automation `CUIAutomation8Class` + `VisualContextBuilder` (XML-траверсал UI-дерева с токен-бюджетом) + Win32 `SendInput`/screenshot | everywhere | **BSL 1.1 ⚠️** | `VisualElementContext.cs`, `VisualContextPlugin.cs` | ЭТАЛОН Windows desktop CU, НО код копировать НЕЛЬЗЯ — только reimplement паттерна |
| GUIAgent loop: screenshot→VLM→`NutJSOperator` (nut-js mouse/keyboard, DPI-aware координаты) | ui-tars-desktop | Apache | `GUIAgent.ts`, `operators/nut-js/` | REIMPLEMENT: VLM-loop + DPI-aware |
| Responses API computer tool + verification | openai-cua-sample-app | MIT | `responses-loop.ts` | REIMPLEMENT: verification-шаг после действия |
| Set-of-Marks (bid на DOM) + merged AXTree + action spaces | browsergym / webarena | Apache | eval harness | REIMPLEMENT для browser-наблюдения |

**Синтез для JARVIS (Windows desktop CU):**
- Screen understanding → VLM на screenshot (как ui-tars) + accessibility-tree
  (как everywhere `VisualContextBuilder`, но переизобретённый).
- Мышь/клавиатура → Win32 `SendInput` с DPI-aware координатами.
- Action verification → обязателен шаг проверки (как openai-cua + наш `verifier.py`).
- ⚠️ everywhere **BSL 1.1** — код КОПИРОВАТЬ НЕЛЬЗЯ, только паттерн.

## 4. Browser Automation

| Механизм | Donor | Где | Почему хорош |
|----------|-------|-----|--------------|
| «Пронумерованные интерактивные элементы» (DOM serializer) | browser-use | `browser_use/dom/serializer/serializer.py`, `ClickableElementDetector.is_interactive` (`clickable_elements.py`), `controller/service.py` + `controller/views.py` | LLM видит `click [12]` вместо raw DOM |
| Set-of-Marks + merged AXTree | browsergym | eval harness | стабильная наблюдаемость |

**Синтез:** адаптировать паттерн browser-use (пронумерованные элементы +
controller registry с `@action`) поверх Playwright. Дополнить нашим
`verifier.py` (фактическая проверка загрузки страницы).

## 5. Memory / Research

> Примечание: субагент D изначально упал на записи отчёта, но
> `audit_memory_research_donors.md` (D) в итоге дописан (38 KB); секция ниже
> синхронизирована с ним и с аудитами B/C. Лицензии см. `03_roadmap_and_license.md` (E).

### 5.1 Memory-механизмы (по донорам)

| Donor | Лицензия | Memory-механизм | Где (файл) | Что хорошего | Адаптация для JARVIS |
|-------|----------|-----------------|------------|--------------|----------------------|
| **letta** (MemGPT) | Apache-2.0 ✅ | «Self-editing memory»: блоки (CORE/ARCHIVAL/RECALL), агент переписывает свою память через tool-calls, context-window management | `letta/agent.py` (1758 строк, `step()` loop), `letta/schemas/memory.py` | Долгосрочная память агента, self-improvement, аккуратный `StepStatus` | REIMPLEMENT: отдельный `MemoryAgent`/`memory_tool` для редактирования `core/memory/long_term.py` |
| **mem0** | Apache-2.0 ✅ | Абстрактный `MemoryBase` (get/get_all/update/delete/history/search) + `configs/vector_stores/*` (chroma/elasticsearch/…) + граф-память | `mem0/memory/base.py` (`MemoryBase` ABC), `mem0/configs/vector_stores/chroma.py` | Чистый слой абстракции над vector/graph; легко своя реализация | REIMPLEMENT: `MemoryBase` → адаптер поверх нашего `core/memory/long_term.py` (ChromaDB уже есть) |
| **khoj** | **AGPL-3.0 🔴** | RAG over documents/notes: `embeddings.py` + `search_type/text_search.py` + `search_filter/*` + `routers/research.py` (`ResearchIteration`, `OperatorRun`) | `khoj/src/khoj/processor/embeddings.py`, `routers/research.py` | Сильный локальный RAG + research-итерации + operator (code/веб) | ⚠️ **ТОЛЬКО абстрактные идеи** (AGPL несовместим с закрытым JARVIS). RAG у нас уже есть (`core/memory/document_rag.py`) — расширить паттерном `ResearchIteration` |
| **gpt-researcher** | Apache-2.0 ⚠️ (конфликт манифестов) | Deep research pipeline: `ResearchConductor` (сбор источников → scrapers → Draft (`memory/draft.py`) → report_assembly), `report_type/deep_research/` | `backend/memory/research.py`, `backend/memory/draft.py`, `backend/report_type/deep_research/` | Полный «deep research» конвейер: план→поиск→чтение→синтез отчёта | REIMPLEMENT: наш `core/research.py` (ResearchEngine, `core/research.py`) расширить orchestration-циклом (conduct → draft → report) |

### 5.2 Research-механизмы

- **gpt-researcher**: `ResearchConductor` итеративно — генерит под-вопросы, ищет
  (Tavily/DuckDuckGo), скрейпит (`read_webpages_content`), пишет чёрновик
  (`backend/memory/draft.py`), собирает финальный отчёт. Self-improving loop.
- **khoj**: `routers/research.py` — `ResearchIteration` (yield-генератор итераций
  research: query→tool-calls→результат), `OperatorRun` (изолированный запуск
  code/веб-инструментов). Архитектура «research как поток итераций».
- **JARVIS уже имеет** `core/research.py` (ResearchEngine, `core/research.py`) — его надо
  поднять до уровня gpt-researcher/khoj: явный conduct-loop + draft + report.

### 5.3 Синтез для JARVIS (Memory/Research) — высокоценные паттерны

1. **Memory**: сохранить `core/memory/*` (ChromaDB + embedder all-MiniLM-L6-v2),
   добавить слой `MemoryBase`-подобной абстракции (как mem0) + self-editing
   memory-тулзы (как letta) для долгосрочного профиля пользователя.
2. **Sleeptime-консолидация** (letta, ключевой паттерн): фоновый агент
   периодически перечитывает диалог и **консолидирует/чистит/обновляет** core-
   блоки памяти (аналог human sleep consolidation). Для JARVIS — ночная/фоновая
   очистка профиля пользователя (`core/proactive.py` + `task_runtime.py`).
3. **User-scoping** (mem0): обязательный `user_id`/`agent_id`/`run_id`, запрет
   caller-метаданным менять scope (`_strip_identity_keys`). Критично для
   мульти-профильного desktop. История версий памяти (`add_history`).
4. **Interrupt пользователем** (khoj, `cancellation_event` + `interrupt_queue`):
   пользователь может остановить/направить research mid-flight. **Обязательно для
   interactive desktop UX** — связать с `Orchestrator.cancel_mission` / `mission.cancel()`.
5. **Research**: расширить `core/research.py` до conduct→draft→report (как
   gpt-researcher), переиспользовать наш `verifier` для факт-проверки источников.
   Добавить **graceful degradation**: per-query exception isolation + rate limiter
   (gpt-researcher `deep_research.py` try/except) — агент не падает при падении
   одного источника; при полном сбое веток — остановка, не генерация пустоты.
6. **Локальные эмбеддинги** (khoj, sentence-transformers) — офлайн-приватность,
   нет утечки в облако. У нас уже есть (`core/memory/embedder.py`).
7. **⚠️ khoj исключён** из кодовых заимствований (AGPL-3.0) — только абстрактные
   идеи (RAG/итерации/interrupt/desktop-UI), реализованные с нуля поверх нашего стека.
8. **Лёгкий локальный стек**: SQLite + sqlite-vec (не Django/FastAPI-серверы
   letta/khoj, не 140-deps gpt-researcher). Компактная реимплементация ядра
   паттернов для desktop.

## 6. Матрица «REIMPLEMENT / ADAPT / BLOCKED»

| Donor | Лицензия | Статус для закрытого продукта |
|-------|----------|------------------------------|
| everywhere | BSL 1.1 | 🔴 **BLOCKED для copy** — только reimplement паттерна |
| ui-tars-desktop | Apache | 🟢 REIMPLEMENT |
| openai-cua-sample-app | MIT | 🟢 REIMPLEMENT |
| browsergym / webarena | Apache | 🟢 REIMPLEMENT |
| browser-use | Apache/MIT | 🟢 REIMPLEMENT |
| agno / swarms / pydantic-ai / autogpt / camel / openclaw / openhands (фронт) / open-interpreter / agent-zero / mirothinker / swe-agent / khoj / letta / mem0 / gpt-researcher | Apache/MIT* | 🟢 REIMPLEMENT (точно — см. `audit_license_matrix.md`) |

\* camel имеет `README.ja.md` — читать его, лицензия проверена в `audit_license_matrix.md`.
