# Аудит donor-проектов: MEMORY и RESEARCH паттерны

**Цель:** глубокий read-only аудит 4 donor-проектов (`letta`, `mem0`, `khoj`, `gpt-researcher`) в `E:\jarvis-donors` для изучения паттернов памяти и исследований (REIMPLEMENT, не copy code).
**Тип коммерции JARVIS:** закрытый коммерческий desktop agent (Windows).
**Дата аудита:** 2026-08-15.
**Режим:** read-only. Ничего в donor-каталогах не менялось, зависимости не ставились, код не запускался.

Лицензионная оговорка: паттерны извлекаются для **реимплементации** (переписывания своими словами/архитектурой). Только `mem0` и `letta` и `gpt-researcher` — Apache-2.0 (разрешает коммерческое использование паттернов и кода при сохранении атрибуции). `khoj` — **AGPL-3.0** (строгий copyleft, сетевое использование обязывает открыть исходники) → для закрытого desktop-агента код напрямую брать **нельзя**, только идеи/архитектуру.

---

## # DONOR: letta

### Идея / Лицензия / Структура
- **Идея:** «AI with advanced memory that can learn and self-improve over time» (бывш. MemGPT). Агентно-центричная долговременная память + кастомные инструменты. Акцент на именно *memory-first* агентах.
- **Лицензия:** `Apache License 2.0` (точно, строки 1-3 LICENSE). ✅ безопасно для коммерции.
- **Версия:** `0.16.8`. Примечание: в README сказано, что активная разработка переехала в `letta-code` (Letta Agent), а это — legacy V1 API server. Для нового JARVIS важнее паттерны, чем сам этот код.
- **Entrypoint:** `letta/main.py` (typer) → команда `server`. Легаси REST/WS сервер (`letta/server/`), `letta/agents/`.
- **Архитектурные директории:**
  - `agents/` — `agent_loop.py` (фабрика цикла), `letta_agent_v2/v3.py`, `voice_agent.py`, `voice_sleeptime_agent.py`
  - `functions/function_sets/` — встроенные инструменты, включая memory-инструменты
  - `groups/` — multi-agent: `dynamic_multi_agent.py`, `supervisor_multi_agent.py`, `sleeptime_multi_agent_v*.py`
  - `schemas/` — `memory.py`, `block.py`, `message.py`, `providers/`
  - `services/` — `summarizer/`, `tool_executor/`, `mcp/`, `memory_repo/`, `context_window_calculator/`
  - `llm_api/` — 20+ клиентов провайдеров
  - `monitoring/` — `event_loop_watchdog.py`
  - `prompts/system_prompts/` — `sleeptime_v2.py`, `memgpt_*`, `react.py`, `voice_*`

### Memory механизмы
Letta реализует **трёхуровневую** память агента, управляемую самим агентом:

1. **Core Memory (in-context)** — `schemas/memory.py` класс `Memory` из `Block` (помеченных секций). Блоки имеют `label` + `description` + `value`, разделение на read-only и read-write. Есть `file_blocks` (присоединённые файлы, git-backed). Размер блоков ограничен (`CORE_MEMORY_BLOCK_CHAR_LIMIT`).
2. **Archival Memory** — внешнее векторное хранилище (`orm/passage.py`, менеджеры `services/passage_manager.py`). Агент вставляет/ищет через инструменты `archival_memory_insert` / `archival_memory_search`.
3. **Recall Memory** — БД сообщений (`orm/message.py`, `orm/conversation_messages.py`). Агент ищет историю через `conversation_search`.

**Инструменты редактирования памяти** (файл `functions/function_sets/base.py`):
- `core_memory_append(agent_state, label, content)`
- `core_memory_replace(agent_state, label, old_content, new_content)`
- `archival_memory_insert(content, tags)`, `archival_memory_search(...)`
- `memory(agent_state, command, ...)` — мета-инструмент с подкомандами `create`/`str_replace`/`insert`/`delete`/`rename`
- `rethink_memory` / `memory_rethink`, `memory_replace`, `memory_insert`, `memory_apply_patch`, `memory_finish_edits` — тонкое и крупное редактирование блоков, «завершение правок».

**Sleeptime-консолидация (ключевой паттерн):** фоновый агент `groups/sleeptime_multi_agent_v4.py` + промпт `prompts/system_prompts/sleeptime_v2.py` («Letta-Sleeptime-Memory … runs in the background, organizing and maintaining the memories»). Sleeptime-агент периодически перечитывает диалог и **консолидирует/чистит/обновляет** core-блоки — аналог human sleep consolidation. Включается через `enable_sleeptime` + `multi_agent_group` (фабрика `agents/agent_loop.py` выбирает `SleeptimeMultiAgentV4`).

**Управление контекстным окном:** `services/summarizer/` — `self_summarizer.py` (self_summarize_all / sliding_window), `compact.py`, `summarizer_sliding_window.py`, `thresholds.py`. `services/context_window_calculator/` считает токены. `schemas/memory.py` `ContextWindowOverview` — полная сводка по токенам (system / core / messages / archival / recall / summary).

**Model abstraction:** `llm_api/` (anthropic, openai, bedrock, groq, xai, vertex, ollama, sglang, zai, minimax, deepseek…) + `schemas/providers/` (20+ провайдеров). Модель-агностичность.

### Research механизмы
Слабо выражены — Letta не ориентирован на web-research. Есть только `conversation_search` + `archival_memory_search` как самостоятельный retrieval. Для JARVIS это не source of truth по research.

### Оценки (0–5)

| Критерий | Оценка | Комментарий |
|---|---|---|
| AGENT LOOP | 5 | `agent_loop.py` + v2/v3 агенты, streaming, шаги, billing |
| TOOLS | 5 | богатый набор, sandbox (`tool_sandbox/`, e2b/local/modal), MCP |
| COMPUTER USE | 1 | нет нативного computer-use |
| BROWSER | 1 | нет нативного браузера (data_sources/ только коннекторы) |
| MEMORY | 5 | лучшая агент-контролируемая память из 4 |
| RESEARCH | 1 | не специализирован |
| MULTI-AGENT | 4 | supervisor/round_robin/dynamic/sleeptime группы |
| VOICE | 4 | voice_agent + voice_sleeptime |
| UI | 2 | legacy сервер; актуальный UI в отдельном letta-code |
| LONG TASKS | 4 | summarizer/compaction + sleeptime консолидaция |
| MCP | 4 | `services/mcp/`, oauth, sse, stdio, streamable_http |
| LICENSE | 5 | Apache-2.0 |
| VALUE FOR JARVIS | 4 | паттерн Core/Archival/Recall + sleeptime — прямой кандидат |

### Ключевые механизмы для JARVIS
| Механизм | Где реализован | Почему хорош | Проблема JARVIS | Сложность адаптации | Действие |
|---|---|---|---|---|---|
| Трёхуровневая память (Core/Archival/Recall) | `schemas/memory.py`, `functions/function_sets/base.py`, `orm/passage.py` | Чёткое разделение «что всегда в контексте» vs «что в векторе» vs «история» | JARVIS, вероятно, пока flat-память | Средняя | REIMPLEMENT: блоки в SQLite/JSON + векторный индекс |
| Агент-контролируемое редактирование памяти (инструменты) | `base.py` `core_memory_*`/`memory_*` | Агент сам решает, что запомнить — не нужен внешний оркестратор | Риск «галлюцинаций» записи | Низкая | ADAPT: переиспользовать интерфейсы инструментов |
| Sleeptime-консолидация | `groups/sleeptime_multi_agent_v4.py`, `sleeptime_v2.py` | Фоновая чистка/обновление → self-improvement без участия пользователя | Нужен отдельный фоновый процесс | Средняя | REIMPLEMENT: ночной/фоновый прогон суммаризации |
| Context-window overview + sliding-window compaction | `schemas/memory.py`, `services/summarizer/` | Предотвращает переполнение контекста | JARVIS длинные сессии | Средняя | ADAPT |
| Event-loop watchdog | `monitoring/event_loop_watchdog.py` | Детект зависаний event loop из отдельного треда | Desktop agent должен не «висеть» | Низкая | REIMPLEMENT (полезно для Windows) |

### Риски
- Это **legacy** V1-код; активная логика уехала в `letta-code` — копировать исходники не надо, брать паттерн.
- Очень тяжёлый стек (FastAPI, ORM, ClickHouse tracing, sandbox) — для desktop-агента избыточен; берём только идеи.
- Sleeptime требует отдельного агента/процесса — нагрузка на ресурсы.

---

## # DONOR: mem0

### Идея / Лицензия / Структура
- **Идея:** «The Memory Layer for Personalized AI» / «Long-term memory for AI Agents». Это **централизованный memory-SDK/сервис**, а не агент. Извлекает факты из диалогов, хранит, ищет, обновляет, удаляет.
- **Лицензия:** `Apache License 2.0` (строки 1-3 LICENSE). ✅ безопасно.
- **Версия:** `2.0.18`.
- **Entrypoint:** `mem0/main.py` (клиент), `mem0/server/`, `mem0/cli/`. Тонкие зависимости (`pyproject.toml`: qdrant-client, openai, sqlalchemy, pydantic, posthog, pytz, protobuf).
- **Архитектурные директории:**
  - `memory/` — `main.py` (класс `Memory`/`AsyncMemory`), `storage.py` (SQLite), `base.py`, `notices.py`, `utils.py`
  - `configs/` — `base.py`, `enums.py` (`MemoryType`), `prompts.py` (`ADDITIVE_EXTRACTION_PROMPT`, `PROCEDURAL_MEMORY_SYSTEM_PROMPT`)
  - `embeddings/` — OpenAI/Ollama/HF/Vertex/…
  - `llms/` — `litellm.py`, openai, anthropic, bedrock… (`LlmBase`)
  - `vector_stores/` — 20+ бэкендов (qdrant, chroma, pgvector, pinecone, faiss, weaviate, milvus, redis, supabase, s3_vectors, …)
  - `reranker/` — cohere, hf, sentence_transformer, llm, zero_entropy
  - `utils/` — `entity_extraction.py` (NER), `scoring.py` (BM25 + entity boost), `factory.py` (LlmFactory/EmbedderFactory/RerankerFactory/VectorStoreFactory)

### Memory механизмы
Центральный класс `Memory` (`memory/main.py`, 3856 строк). Конвейер `add()` → `_add_to_vector_store()`:

**Phased batch pipeline (V3):**
- **Phase 0 — Context gathering:** `db.get_last_messages(session_scope, limit=10)` (SQLite история) + `parse_messages`.
- **Phase 1 — Existing memory retrieval:** эмбеддинг запроса → `vector_store.search(top_k=10, filters={user_id/agent_id/run_id})`. Для защиты от галлюцинаций UUID→integer mapping (`uuid_mapping`).
- **Phase 2 — LLM extraction (single call):** промпт `ADDITIVE_EXTRACTION_PROMPT` (+`AGENT_CONTEXT_SUFFIX` если `agent_id`) → решает ADD / UPDATE / DELETE / NONE над существующими памятями.
- **Procedural memory:** отдельный путь `_create_procedural_memory` с `PROCEDURAL_MEMORY_SYSTEM_PROMPT`.

**Типы памяти** (`configs/enums.py`): `SEMANTIC`, `EPISODIC`, `PROCEDURAL`.

**Хранилище:** `SQLiteManager` (`storage.py`) — таблица history (add_history/get_history) + messages. Плюс векторный стор (фабрика, 20+ бэкендов). Эмбеддинги через `EmbedderFactory`.

**Поиск `search()`:** `top_k=20`, `threshold=0.1`, опц. `rerank`. Комбинирует: векторный поиск + **BM25** (лемматизированный, `scoring.py`) + **entity boosts** (`_compute_entity_boosts`, NER из `entity_extraction.py`) + reranker. Богатая фильтрация метаданных с операторами (`eq`, `ne`, `in`, `gt`, `AND/OR/NOT`). Поддержка истечения (`expiration_date`).

**Скоупинг безопасности:** обязательный `user_id`/`agent_id`/`run_id`; `_strip_identity_keys` запрещает caller-метаданным менять scope (issue #4490/#6655). `detect_temporal_usage`/`decay`/`scale` notices.

**Entity store:** NER-кандидаты → `_link_entities_for_memory` → boosts при поиске. Хороший паттерн для «кто/что»-памяти.

### Research механизмы
Отсутствуют — это чистый memory-layer. Нет web-search, scrape, report generation.

### Оценки (0–5)

| Критерий | Оценка | Комментарий |
|---|---|---|
| AGENT LOOP | 1 | не агент, SDK |
| TOOLS | 2 | встроенные add/search/update/delete |
| COMPUTER USE | 0 | — |
| BROWSER | 0 | — |
| MEMORY | 5 | лучший memory-layer из 4 (extraction + vector + entity + scoping) |
| RESEARCH | 0 | — |
| MULTI-AGENT | 0 | — |
| VOICE | 0 | — |
| UI | 1 | только server API |
| LONG TASKS | 2 | history/versioning памяти |
| MCP | 2 | есть `mcp` упоминания, не центрально |
| LICENSE | 5 | Apache-2.0 |
| VALUE FOR JARVIS | 5 | главный donor по памяти |

### Ключевые механизмы для JARVIS
| Механизм | Где | Почему хорош | Проблема JARVIS | Сложность | Действие |
|---|---|---|---|---|---|
| LLM-извлечение фактов из диалога (ADD/UPDATE/DELETE) | `memory/main.py` `_add_to_vector_store`, `configs/prompts.py` `ADDITIVE_EXTRACTION_PROMPT` | Не надо вручную писать память; LLM сам консолидирует | Нужен вызов LLM на каждый add (латентность/цена) | Средняя | REIMPLEMENT: свой extraction-промпт + векторный стор |
| UUID→int mapping (anti-hallucination) | `memory/main.py` L936 | LLM не выдумывает чужие ID при UPDATE/DELETE | — | Низкая | ADAPT |
| Hybrid retrieval: vector + BM25 + entity boost + rerank | `utils/scoring.py`, `reranker/`, `_compute_entity_boosts` | Точность поиска выше чистого cosine | Сложнее индекс | Средняя | REIMPLEMENT |
| Scoping user/agent/run + identity-key stripping | `_build_filters_and_metadata`, `_strip_identity_keys` | Безопасное мультитенантное разделение | — | Низкая | ADAPT (критично для приватности desktop) |
| History/versioning памяти (SQLite) | `storage.py` `add_history` | Аудит изменений памяти | — | Низкая | ADAPT |
| Factory-абстракция LLM/Embedder/VectorStore/Reranker | `factory.py`, `configs/` | Легко менять провайдеров | — | Низкая | ADAPT |

### Риски
- Поиск/добавление требуют LLM-вызова (затраты). Для desktop можно делать асинхронно/батчами.
- `telemetry` (posthog) — для закрытого desktop надо отключить (есть флаги).
- Истечение памяти (`expiration_date`) — полезно, но в OSS отключено (decay/temporal — platform-only).

---

## # DONOR: khoj

### Идея / Лицензия / Структура
- **Идея:** «Your AI second brain». Персональный RAG-агент: индексирует личные заметки/документы/изображения, семантический поиск, чат, а также **итеративный research-цикл** с выбором инструментов.
- **Лицензия:** `GNU AFFERO GENERAL PUBLIC LICENSE Version 3` (AGPL-3.0, строки 1-3 LICENSE). ⚠️ **РИСК для закрытого коммерческого desktop-агента** — copyleft + сетевой trigger. Можно брать только **паттерны/идеи**, не код.
- **Entrypoint:** `src/khoj/main.py` (`run`, `start_server` FastAPI), `src/khoj/configure.py`. Есть кроссплатформенный desktop-клиент: `src/interface/desktop/` (Tauri-style: `main.js`, `preload.js`), плюс web/obsidian/emacs.
- **Архитектурные директории:**
  - `src/khoj/processor/embeddings.py` — `EmbeddingsModel` (sentence-transformers локально + OpenAI + HF)
  - `src/khoj/database/` — Django ORM модели (`models/`, `adapters/`)
  - `src/khoj/routers/` — `research.py` (research loop!), `api_memories.py`, `api_chat.py`, `api_content.py`
  - `src/khoj/search_filter/`, `src/khoj/search_type/`
  - `src/khoj/configure.py`

### Memory механизмы
Два слоя памяти:
1. **Индексированный контент (RAG):** личные данные эмбеддятся (`processor/embeddings.py`, модель `thenlper/gte-small` локально, `normalize_embeddings=True`) и хранятся в pgvector. Это «внешняя» память-знание.
2. **Пользовательская память (UserMemory):** модель `UserMemory` (Django) с полями `raw` + `embeddings`. Сохраняется через `UserMemoryAdapters.save_memory`, ищется через `search_memories()`:
   ```python
   relevant_memories = UserMemory.objects.filter(user=user, agent=agent) \
       .annotate(distance=CosineDistance("embeddings", embedded_query)) \
       .order_by("distance").filter(distance__lte=max_distance)
   ```
   `max_distance` берётся из `bi_encoder_confidence_threshold` модели поиска. Результаты (`relevant_memories`) подмешиваются в чат и в research-цикл.

API памяти: `routers/api_memories.py` — `get_memories`, `update_memory` (delete + re-create с новым `raw`), `delete_memory`. То есть память — **неявная** (индексированный контент + пользовательские raw-заметки), а не агент-контролируемые блоки как у Letta.

### Research механизмы
`routers/research.py` — **итеративный агентный research-цикл** (это главная ценность Khoj для JARVIS, наряду с GPT-Researcher):
- `research()` — async-генератор. `MAX_ITERATIONS = int(os.getenv("KHOJ_RESEARCH_ITERATIONS", 5))`. Лимиты: `max_document_searches=7`, `max_online_searches=3`, `max_webpages_to_read=1`.
- **Выбор инструмента:** `apick_next_tool()` решает следующий шаг (document search / online search / read webpage / operate computer / MCP). `execute_tool()` исполняет.
- **Прерывание пользователем:** `cancellation_event` (asyncio.Event) + `interrupt_queue` — пользователь может вмешаться mid-research (новая инструкция или abort). Отличный паттерн для interactive desktop agent.
- **MCP:** `McpServerAdapters.aget_all_mcp_servers()` → `MCPClient`.
- **Computer use:** `ConversationCommand.OperateComputer` → `operate_environment(...)`, streaming статус.
- **Продолжение:** предыдущие итерации (`previous_iterations`) переиспользуются при продолжении чата.

### Оценки (0–5)

| Критерий | Оценка | Комментарий |
|---|---|---|
| AGENT LOOP | 3 | research-loop с выбором инструментов |
| TOOLS | 3 | doc/online/computer/MCP инструменты |
| COMPUTER USE | 3 | `OperateComputer` (видел в коде) |
| BROWSER | 2 | online search + read webpage (не полноценный браузер) |
| MEMORY | 3 | RAG + UserMemory, но без агент-редактирования |
| RESEARCH | 4 | хороший итеративный цикл с прерыванием |
| MULTI-AGENT | 1 | нет явного multi-agent |
| VOICE | 2 | есть в экосистеме, не центрально |
| UI | 4 | кроссплатформенный desktop-клиент (важно для Windows!) |
| LONG TASKS | 3 | итерации research, continuation |
| MCP | 4 | MCP-серверы подключаются |
| LICENSE | 1 | AGPL-3.0 — РИСК для closed commercial |
| VALUE FOR JARVIS | 4 | desktop UI + research-loop паттерны (только идеи) |

### Ключевые механизмы для JARVIS
| Механизм | Где | Почему хорош | Проблема JARVIS | Сложность | Действие |
|---|---|---|---|---|---|
| Итеративный research-loop с выбором инструмента | `routers/research.py` `research`/`apick_next_tool` | Агент сам планирует шаги; не монолитный pipeline | Нужен оркестратор выбора | Средняя | REIMPLEMENT (идея) |
| Прерывание пользователем (cancel/redirect) | `cancellation_event`, `interrupt_queue` | Interactive desktop UX — юзер может остановить/направить | — | Низкая | ADAPT (критично для desktop) |
| Локальные эмбеддинги (sentence-transformers) | `processor/embeddings.py` | Офлайн-приватность, нет утечки в облако | Качество модели | Низкая | ADAPT |
| CosineDistance + confidence threshold | `database/adapters/__init__.py` `search_memories` | Фильтр мусорных совпадений | — | Низкая | ADAPT |
| Кроссплатформенный desktop-клиент | `src/interface/desktop/` | Готовый паттерн UI для Windows | AGPL — код брать нельзя | Средняя | REIMPLEMENT (только архитектура UI) |

### Риски
- **AGPL-3.0** — главный риск. Любой copy/paste кода → обязанность открыть исходники JARVIS. Строго паттерны.
- Django-heavy стек (ORM, migrations) — для desktop лучше легковеснее (SQLite + pgvector/sqlite-vec).
- Research-loop завязан на онлайн-поиск; для desktop нужен graceful offline-режим.

---

## # DONOR: gpt-researcher

### Идея / Лицензия / Структура
- **Идея:** «the first open deep research agent designed for both web and local research». Автономный агент глубокого исследования: план → параллельный поиск → scrape → синтез → отчёт с цитатами.
- **Лицензия:** `Apache License 2.0` (строки 1-3 LICENSE). ✅ безопасно.
- **Версия:** `0.14.7`.
- **Entrypoint:** `cli.py`, `main.py`, `langgraph.json`, `Dockerfile.fullstack`. 140 зависимостей (`pyproject.toml`).
- **Архитектурные директории (в `gpt_researcher/`):**
  - `agent.py` — класс `GPTResearcher` (`conduct_research`, `write_report`)
  - `skills/` — `researcher.py` (`ResearchConductor`), `deep_research.py` (`DeepResearchSkill`), `writer.py`, `curator.py`, `browser.py`
  - `actions/` — `report_generation.py`, `query_processing.py`, `web_scraping.py`, `retriever.py`, `markdown_processing.py`
  - `retrievers/` — 20+ поисковых бэкендов (tavily, google, bing, brave, duckduckgo, arxiv, pubmed_central, semantic_scholar, exa, serpapi, serper, searx, bocha, openalex, …)
  - `scraper/` — beautiful_soup, browser (nodriver), firecrawl, pymupdf, tavily_extract, web_base_loader
  - `context/` — `compression.py`, `retriever.py`
  - `memory/` — `embeddings.py` (`Memory` класс, LangChain-обёртка)
  - `llm_provider/`, `document/`, `utils/` (rate_limiter, workers, costs, enum)
  - `multi_agents/`, `mcp/` (client, research, streaming, tool_selector)

### Memory механизмы
**Минимальная** долговременная память. `memory/embeddings.py` — класс `Memory`: тонкая обёртка над LangChain-эмбеддингами (openai/cohere/ollama/hf…, lazy import). Используется для similarity документов внутри задачи. Нет персистентной用户-памяти между сессиями. Это **research-first**, а не memory-first проект.

### Research механизмы — ЭТАЛОН
Конвейер (`agent.py` `conduct_research`):
1. **Agent/role selection** — `choose_agent()` (из `actions/agent_creator.py`) подбирает персону под запрос.
2. **ResearchConductor** (`skills/researcher.py` `ResearchConductor.plan_research`):
   - генерация под-запросов (`get_search_results` → `query_processing.plan_research_outline`)
   - для каждого запроса: `retriever` (из 20+ бэкендов) → сбор URL → `scraper` (nodriver/firecrawl/bs4/pymupdf) → извлечение текста
   - `context/compression.py` сжимает контекст
   - `get_subtopics`, `generate_draft_section_titles`, `get_similar_written_contents_by_draft_section_titles` — структурирование отчёта
3. **Report generation** (`actions/report_generation.py` `generate_report` + `write_report_introduction`/`write_conclusion`): markdown-отчёт с цитатами (`add_references`, `add_research_sources`, `add_research_images`).
4. **Cost tracking** — `utils/costs.py`, step costs.

**Deep Research** (`skills/deep_research.py` `DeepResearchSkill.deep_research`): рекурсивное дерево глубины×ширины. `generate_search_queries(breadth)` → на каждом уровне создаёт вложенных `GPTResearcher` (рекурсия!), параллельно через `asyncio.Semaphore(concurrency_limit)`; накапливает `learnings` + `citations` + `followUpQuestions`. **Graceful degradation (#1579):** если ветка упала — ловит исключение, `return None`, фильтрует; если ВСЕ ветки провалились — останавливается (не генерит пустые follow-up).

**Multi-agent:** `multi_agents/` (langgraph, ag2) — параллельные researcher/editor/writer.
**MCP:** `mcp/` — `tool_selector.py`, research-интеграция.

### Оценки (0–5)

| Критерий | Оценка | Комментарий |
|---|---|---|
| AGENT LOOP | 3 | research-conductor loop (не общий agent loop) |
| TOOLS | 4 | web/scraper/document инструменты |
| COMPUTER USE | 0 | — |
| BROWSER | 5 | nodriver + firecrawl + множество scrapers |
| MEMORY | 1 | только task-scoped embeddings |
| RESEARCH | 5 | лучший research-pipeline из 4 |
| MULTI-AGENT | 4 | langgraph/ag2 параллельные агенты |
| VOICE | 0 | — |
| UI | 2 | web frontend (fullstack Docker) |
| LONG TASKS | 5 | deep-research дерево, параллелизм |
| MCP | 4 | `mcp/` клиент + tool_selector |
| LICENSE | 5 | Apache-2.0 |
| VALUE FOR JARVIS | 5 | главный donor по research |

### Ключевые механизмы для JARVIS
| Механизм | Где | Почему хорош | Проблема JARVIS | Сложность | Действие |
|---|---|---|---|---|---|
| Декомпозиция запроса → параллельные retrieval-ветки | `agent.py`, `ResearchConductor`, `retrievers/` | Широкий охват источников, скорость | Нужно много API-ключей/лимитов | Средняя | REIMPLEMENT |
| Множество search/scrape бэкендов (плагином) | `retrievers/`, `scraper/` | Легко добавить свой источник | Поддержка 20+ интеграций | Низкая | ADAPT (интерфейсы) |
| Context compression перед генерацией отчёта | `context/compression.py` | Экономия токенов при длинных источниках | — | Низкая | ADAPT |
| Структурирование отчёта (subtopics + draft titles) | `actions/report_generation.py`, `agent.get_subtopics` | Читаемый отчёт с цитатами | — | Низкая | ADAPT |
| Deep-research рекурсия + graceful stop | `skills/deep_research.py` `deep_research` | Глубина без бесконечного цикла | — | Средняя | REIMPLEMENT |
| Rate limiter + per-query exception isolation | `utils/rate_limiter.py`, `deep_research` try/except | Устойчивость к падению источников | — | Низкая | ADAPT |

### Риски
- 140 зависимостей; многое тянет LangChain/browser-движки — для desktop надо сильно урезать.
- Ориентирован на **online**; для desktop-агента нужен offline/local document режим (есть `document/` loader — можно адаптировать для локальных файлов).
- Нет долговременной пользовательской памяти — надо комбинировать с Mem0/Letta паттернами.

---

## СИНТЕЗ: ЛУЧШИЙ STACK ДЛЯ MEMORY / RESEARCH (для desktop general-purpose агента)

### Память (MEMORY) — гибрид «Letta × Mem0 × Khoj»
Рекомендуемая архитектура для закрытого desktop-агента (Windows, приватность, локально-по-умолчанию):

1. **Рабочая память (Working / Core Memory) — паттерн Letta.**
   - Помеченные блоки в контексте (`schemas/memory.py`, `functions/function_sets/base.py`): `persona`, `user`, `scratch`, `notes`.
   - Агент-контролируемое редактирование через инструменты (`core_memory_append`/`replace`/`memory_rethink`).
   - **Sleeptime-консолидация** (`sleeptime_multi_agent_v4.py` + `sleeptime_v2.py`): фоновый прогон, который чистит/обновляет блоки без юзера.
   - *Файлы-источники паттерна:* `letta/schemas/memory.py`, `letta/agents/agent_loop.py`, `letta/groups/sleeptime_multi_agent_v4.py`, `letta/prompts/system_prompts/sleeptime_v2.py`, `letta/services/summarizer/self_summarizer.py`.

2. **Семантическая память (Semantic / Fact Memory) — паттерн Mem0.**
   - LLM-извлечение фактов из диалога (ADD/UPDATE/DELETE) через `ADDITIVE_EXTRACTION_PROMPT` (`mem0/configs/prompts.py`) → векторный стор + SQLite history.
   - UUID→int mapping для защиты от галлюцинаций (`mem0/memory/main.py` L936).
   - *Файлы-источники:* `mem0/memory/main.py` (`_add_to_vector_store`), `mem0/configs/prompts.py`, `mem0/memory/storage.py`, `mem0/utils/entity_extraction.py`, `mem0/utils/scoring.py`.

3. **Гибридный поиск — паттерн Mem0 + Khoj.**
   - vector (cosine) + BM25 (лемматизированный) + entity boost + опц. reranker (`mem0/utils/scoring.py`, `mem0/reranker/`).
   - Локальные эмбеддинги (sentence-transformers) для приватности (`khoj/processor/embeddings.py`).
   - CosineDistance + `bi_encoder_confidence_threshold` для отсева шума (`khoj/database/adapters/__init__.py` `search_memories`).
   - *Файлы-источники:* `mem0/vector_stores/` (faiss/sqlite-vec локально), `khoj/processor/embeddings.py`, `khoj/database/adapters/__init__.py`.

4. **Скоупинг и приватность — паттерн Mem0.**
   - Обязательный `user_id`/`agent_id`/`run_id`, запрет caller-метаданным менять scope (`mem0/memory/main.py` `_strip_identity_keys`, `_build_filters_and_metadata`). Критично для мульти-профильного desktop.

5. **Хранение:** локальный SQLite + pgvector/sqlite-vec (не Django, не тяжёлый сервер). История версий памяти (`mem0/memory/storage.py` `add_history`).

### Исследование (RESEARCH) — гибрид «GPT-Researcher × Khoj»
1. **Итеративный research-loop с выбором инструмента — паттерн Khoj.**
   - `research()` генерирует, `apick_next_tool()` выбирает следующий шаг (локальный документ / онлайн-поиск / чтение веб / computer-use / MCP).
   - **Прерывание пользователем** (`cancellation_event` + `interrupt_queue`) — обязательно для interactive desktop UX.
   - *Файлы-источники:* `khoj/src/khoj/routers/research.py` (`research`, `apick_next_tool`, `execute_tool`), `khoj/src/khoj/configure.py`.

2. **Deep-research pipeline — паттерн GPT-Researcher.**
   - Декомпозиция → параллельные retrieval-ветки (`gpt_researcher/agent.py` `conduct_research`, `gpt_researcher/skills/researcher.py` `ResearchConductor`).
   - Плагинные retrievers/scrapers (`retrievers/`, `scraper/`) — легко добавить локальный файловый источник.
   - Context compression перед генерацией (`gpt_researcher/context/compression.py`).
   - Структурированный отчёт с цитатами (`gpt_researcher/actions/report_generation.py`).
   - Deep-research рекурсия + graceful stop при полном сбое веток (`gpt_researcher/skills/deep_research.py`).
   - *Файлы-источники:* `gpt_researcher/agent.py`, `gpt_researcher/skills/researcher.py`, `gpt_researcher/skills/deep_research.py`, `gpt_researcher/actions/report_generation.py`, `gpt_researcher/context/compression.py`, `gpt_researcher/utils/rate_limiter.py`.

3. **Устойчивость:** rate limiter + per-query exception isolation (GPT-Researcher `deep_research.py` try/except) — агент не падает при падении одного источника. Для desktop — плюс offline-режим (fallback на локальные документы Khoj, если нет сети).

### Итоговая рекомендация для JARVIS
- **MEMORY:** берём Core/Archival/Recall + sleeptime от **Letta** (архитектура) + extraction/incremental-update + hybrid-search + scoping от **Mem0** (реимплементация) + локальные эмбеддинги/cosine-threshold от **Khoj** (идея). Используем легковесный локальный стек (SQLite + sqlite-vec + sentence-transformers), НЕ Django/серверы.
- **RESEARCH:** берём research-loop с выбором инструментов + прерыванием от **Khoj** + deep-research pipeline/retrievers/compression/report от **GPT-Researcher**. Всё локально-по-умолчанию с онлайн-опцией.
- **ЛИЦЕНЗИИ:** letta/mem0/gpt-researcher — Apache-2.0 (✅ можно реимплементировать и коммерциализировать). **khoj — AGPL-3.0 (⚠️ только паттерны/идеи, НИКАКОГО copy code).**
- **Что НЕ брать целиком:** тяжёлые серверные стеки (FastAPI+ORM Letta, Django Khoj, 140-deps GPT-Researcher) — для desktop агента нужна компактная реимплементация ядра паттернов.

### Таблица итоговой ценности

| Donor | Роль в JARVIS | Лицензия | Memory | Research | Главный takeaway |
|---|---|---|---|---|---|
| letta | Core/Archival/Recall + sleeptime консолидация | Apache-2.0 | 5 | 1 | агент-управляемая память + фоновая чистка |
| mem0 | Semantic fact-extraction + hybrid search + scoping | Apache-2.0 | 5 | 0 | memory-layer «из коробки» паттернов |
| khoj | Локальные эмбеддинги + research-loop + interrupt + desktop UI | AGPL-3.0 ⚠️ | 3 | 4 | только идеи (лицензия!) |
| gpt-researcher | Deep-research pipeline + retrievers + report + resilience | Apache-2.0 | 1 | 5 | эталон research-пайплайна |

---
*Аудит завершён в режиме read-only. Исходники donor-проектов не изменялись. Все пути к файлам указаны относительно `E:\jarvis-donors`. Рекомендуется REIMPLEMENT (переписывание архитектуры/паттернов), а не copy code; особенно строго для khoj (AGPL-3.0).*
