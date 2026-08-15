# J.A.R.V.I.S. 3.0 — Core Architecture (COLD INTELLIGENCE / AGENTIC ENGINE)

> Документ описывает реальную архитектуру ядра J.A.R.V.I.S. после аудита
> существующего проекта и минимального архитектурного перехода (ТЗ §1–§30).
> J.A.R.V.I.S. — это НЕ чат-бот и НЕ assistant. Это персональная
> операционная интеллектуальная система, живущая внутри компьютера.

---

## 0. Философия (§1, §29)

Главная способность J.A.R.V.I.S. — **НЕ знать всё заранее, а уметь найти
путь к выполнению неизвестной задачи**:

```
USER GOAL → INTENT → RISK → CONTEXT → MODE → PLAN
           → TOOL RETRIEVAL → EXECUTION → VERIFICATION
           → REPAIR (при ошибке) → RESULT → MEMORY / SKILL
```

- Плохой J.A.R.V.I.S.: *"У меня нет такого инструмента."*
- Хороший: *"Готового способа нет. Сейчас найду."* → затем
  RESEARCH → BUILD → TEST → LEARN (§29).

**КРИТИЧЕСКОЕ ПРАВИЛО (§4):** никакого искусственного «лимита мышления
в 3 секунды». Нигде в ядре нет проверки вида `if elapsed > 3: fail`.
Реальные таймауты живут только внутри инструментов (сеть, процесс).
Долгая задача (5с, 2мин, 10мин) — НОРМА.

---

## 1. Аудит — что реально было (и что сделано)

### Что РАБОТАЛО (сохранено как есть, эволюция, не reset — §26):
| Модуль | Статус | Заметка |
|--------|--------|---------|
| `core/task_runtime.py` | ✅ отличный | `Mission`, `EventBus`, статусы, watchdog=опционален |
| `core/router/council.py` | ✅ хороший | выбор тира + graceful эскалация |
| `core/router/local_face.py` | ✅ хороший | Qwen как «лицо», classify по JSON |
| `core/llm/local_qwen.py` | ✅ работает | реально загружает Qwen3-4B, генерирует |
| `core/llm/factory.py` | ✅ хороший | кэш бэкендов |
| `core/llm/tiers.py` | ✅ хороший | эскалация tiers |
| `core/actions/*` | ✅ работает | 14 инструментов, registry |
| `core/memory/*` | ✅ работает | RAG, ChromaDB, graph, long-term |
| `core/repair.py` (до фикса) | ⚠️ частично | сломанный `__init__`, неверный fallback |
| `core/ingest.py` | ✅ работает | chunking, без привязки к LLM |

### Что было СЛОМАНО (исправлено в этом проходе):
| Баг | Где | Исправление |
|-----|-----|-------------|
| `core/agent.py` — `SyntaxError` (строка 57: `@dataclass_like := None`) | весь модуль не импортировался | переписан в полноценный mission loop (§8) |
| `core/verifier.py` — падает на `ActionResult.get()` (dataclass, не dict) | `verify_action_result` бросал `AttributeError` | переписан: работает с dataclass, реальные success_check |
| `core/repair.py` — `self._max = max(attempts := ...)` TypeError | `RepairLoop` не создавался | `int(max_attempts)` |
| `core/repair.py` — fallback `continue` всегда срабатывал | вечный цикл при смене инструмента | корректный switch + адаптация аргументов |
| `core/actions/app_control.py` — `shlex.split()` съедал `\` в Windows-путях | `open_app` НЕ запускал ни одно приложение | путь передаётся как есть, аргументы через `shlex.split(posix=False)` |
| `core/orchestrator.py` — `import time` в середине файла (после использования) | потенциальный NameError | перенесён наверх |

### Что было ЗАГЛУШКОЙ (реализовано):
- `core/agent.py` — был пустой заглушкой → теперь полный контроллер миссии.
- `core/capabilities.py` — **НОВЫЙ**: единый паспорт возможностей (§12).
- `core/structured.py` — **НОВЫЙ**: парсинг/ремонт/валидация JSON-решений (§13).
- `core/safety.py` — **НОВЫЙ**: risk-гейтинг + prompt-injection изоляция (§21, §22).
- `core/model_router.py` — **НОВЫЙ**: выбор модели ПО СЛОЖНОСТИ (§15, §17).
- `core/research.py` — **НОВЫЙ**: отдельный research workflow (§18).

---

## 2. Поток выполнения задачи (§3, §6)

```
submit_goal(goal)                          [Orchestrator — §5, §6]
   │
   ├─ §5  ACKNOWLEDGING (мгновенно, без LLM): "Принято, сэр." / "Разбираюсь."
   │
   └─ TaskRuntime.submit()  →  фоновый поток (MissionRunner)
                                  │
        agent.execute(goal, mission, cancel)
            ├─ INTENT      (keyword, офлайн)
            ├─ RISK        (assess_risk — §21)
            ├─ CONTEXT      (ingest при >6000 символов — §7)
            ├─ SKILL        (поиск готового навыка — §9)
            ├─ MODE/ROUTING (ModelRouter по сложности — §15)
            │
            ├─ §18 RESEARCH MODE?  → ResearchEngine (отдельный конвейер)
            │
            ├─ §3  FAST PATH?  (простая команда: open/volume/status)
            │       → _execute_verified (без планирования)
            │
            ├─ §12 TOOL RETRIEVAL (только релевантные инструменты модели)
            ├─ §13 PLAN (структурированное решение модели + validate)
            │
            ├─ §21 RISK GATE (HIGH → confirmation_required)
            └─ §14 EXECUTE → VERIFY → (§10/§11 REPAIR) → RESULT
                  верификация СТРОГАЯ: "готово" только после факта
```

Простая задача (`"Открой Telegram"`) идёт по FAST PATH — минует
планирование и LLM-маршрутизацию тяжёлой модели (§3: цикл сокращается).

---

## 3. Компоненты ядра

### 3.1 Capability Registry — `core/capabilities.py` (§12)
Единый паспорт каждого инструмента: `name, description, examples, risk_level,
permissions, speed, cost, internet_required, file_access, success_check,
fallbacks, tags`. Метод `retrieve(goal, top_k)` возвращает ТОЛЬКО
релевантные инструменты (детерминированный офлайновый скоринг) — модели
не отдаются все тулзы сразу.

### 3.2 Structured Output — `core/structured.py` (§13)
`parse_structured` извлекает JSON из «грязного» ответа модели, механически
чинит (markdown-заборы, одинарные кавычки, `True`→`true`, голые значения,
невалидные ключи, недозакрытые скобки), валидирует против реальной схемы
инструмента. При провале возвращает текст ошибки для повторного запроса
(НЕ падает на плохом JSON).

### 3.3 Safety — `core/safety.py` (§21, §22)
`assess_risk` → `RiskLevel.LOW|MEDIUM|HIGH`. **HIGH требует подтверждения**
(удаление, отправка, оплата, пароли, реестр, неизвестный exe, питание).
`wrap_untrusted` оборачивает веб/PDF/письма в защитный конверт: контент —
ЭТО ДАННЫЕ, а не КОМАНДЫ. `detect_injection` ловит попытки переопределения
инструкций.

### 3.4 Model Router — `core/model_router.py` (§15, §17)
`estimate_complexity(goal)` → `route()`. Выбор тира ПО СЛОЖНОСТИ
(reasoning, code, architecture, privacy, size) — **НЕ по латентности** (§4).
Локальная Qwen3-4B для простых (local first); эскалация к analyst/coder/
architect при необходимости; приватные данные — принудительно локально;
внешний тир недоступен → graceful fallback на локальную.

### 3.5 Verifier — `core/verifier.py` (§14)
Реестр фактических проверок по имени инструмента: `file_exists`,
`process_running`, `page_loaded`, `search_results`, `reminder_registered` и т.д.
Каждый результат помечается `strict=True` (настоящая проверка) или
`strict=False` (доверились `ok`, честно). "Готово" только при `verified`.

### 3.6 Repair Loop — `core/repair.py` (§10, §11)
`EXECUTE → ERROR → DIAGNOSE → PATCH → RETRY → VERIFY`. До `max_attempts`
(по умолчанию 3, НЕ 1). Переключается на fallback-инструмент с
**адаптацией аргументов** под его схему (`_adapt_args` — слепая передача
аргументов запрещена, иначе валидация впустую сжигает попытку). Проверяет
ФАКТИЧЕСКИ даже при `ok=True` (§14). Исчерпав пути — честно `ok=False`, не
ложный успех.

### 3.7 Skill Forge — `core/skill_forge.py` (§9)
Неизвестная задача → `match` готового навыка → иначе создание **черновика**
(`status: draft`, НЕ stable — пока не проверен). Хранится в `data/skills/`
как markdown+YAML frontmatter.

### 3.8 Research Engine — `core/research.py` (§18)
Отдельный конвейер: `QUERY → SEARCH → COLLECT → READ → FILTER →
CROSS-CHECK → ANALYZE → SYNTHESIZE → VERIFY → REPORT`. Различает
`verified_fact / source_claim / opinion / uncertain / stale` (§18). Весь
сетевой контент оборачивается `wrap_untrusted` (§22).

### 3.9 Agent — `core/agent.py` (§3, §8, §9)
Контроллер одной миссии. Переиспользует (§26): `core.actions`,
`core.router`, `core.task_runtime`, `core.repair`, `core.verifier`,
`core.skill_forge`, `core.ingest`. Основной метод `execute()` —
полный цикл с авто-сокращением для простых задач.

### 3.10 Orchestrator — `core/orchestrator.py`
Старый `handle_input` (синхронный, CouncilRouter) **сохранён** для
обратной совместимости. **Добавлено** агентное ядро:
- `submit_goal(goal, on_event)` — асинхронный запуск миссии (§6);
  немедленно возвращает `Mission` с `task_id` (JARVIS-YYYY-NNNNN);
- `wait_for / cancel_mission / get_mission / list_missions` — управление (§24);
- `subscribe_events(callback)` — подписка на события (§23);
- `Agent` + `TaskRuntime(default_watchdog_sec=None)` — безлимит по времени.

---

## 4. Жизненный цикл миссии (§4, §6)

```
queued → acknowledging → analyzing → planning → executing
       → verifying → repairing → completed
а также: paused / cancelled / failed
```
События (§23) с `task_id`: `task_started, acknowledged, plan_ready,
step_started, step_completed, tool_called, tool_result, verification,
repair_started, repair_completed, delegated, stream_chunk, stream_end,
confirmation_required, error, task_completed, task_failed, task_progress`.

`Mission` содержит: `status, created_at, updated_at, progress, current_step,
model_used, tools_used, result, errors, verification, acknowledgement`.

---

## 5. Qwen3-4B (§16)

- Источник: `C:\Users\WwW\Downloads\Qwen3-4B-Instruct-2507-Q5_K_M.gguf`
- Скопирован (НЕ перемещён) в `data/models/qwen3-4b-instruct-q5_k_m.gguf`
- **MD5 идентичен** (проверено: `bfc249288df1576...` совпадает с оригиналом)
  → оригинал в Downloads НЕ тронут.
- Реально загружается (llama-cpp 0.3.16) и генерирует.
- Роль: **FAST LOCAL BRAIN** — intent, extraction, short planning,
  tool selection, structured output, local ops, short answers.

---

## 6. Файлы

```
core/
  agent.py            # контроллер миссии (§3, §8) — ПЕРЕПИСАН
  capabilities.py     # НОВЫЙ — паспорта инструментов + retrieval (§12)
  structured.py       # НОВЫЙ — JSON parse/repair/validate (§13)
  safety.py           # НОВЫЙ — risk gate + prompt-injection (§21, §22)
  model_router.py     # НОВЫЙ — выбор модели по сложности (§15, §17)
  research.py         # НОВЫЙ — research workflow (§18)
  verifier.py         # ФИКС — фактические проверки (§14)
  repair.py           # ФИКС — repair loop + adapt_args (§10, §11)
  task_runtime.py     # ДОПОЛНЕН — события §23, поля Mission §6
  orchestrator.py     # ДОПОЛНЕН — async missions, ACK, события
  actions/app_control.py  # ФИКС — shlex.split на Windows-путях
scripts/
  test_core_scenarios.py  # 11 сценариев ТЗ, 23/23 PASS (§25)
```

---

## 7. Ограничения (честно)

- External-модели (analyst/coder/architect) не настроены (нет API-ключей в
  `settings.json`) → маршрутизация корректно деградирует до локальной Qwen.
  Эскалация проверена на уровне логики роутера, не на реальных вызовах
  внешних API.
- Skill Forge создаёт черновики (`draft`), но автоматическая проверка
  (`mark_verified`) ещё не вызывается агентом (требует безопасного
  sandbox-тестирования процедур) — навык НЕ помечается `stable` до проверки
  (соответствует §9).
- TTS/STT не тестировались в этом проходе (требуют голосовых файлов/устройств);
  ядро интеллекта от них не зависит.
- ChromaDB выдаёт warning `capture() takes 1 positional argument but 3 were
  given` (обёртка телеметрии) — безвредно, не влияет на работу памяти.
