# Progress Report — J.A.R.V.I.S. 3.0 Core / Intelligence / Agentic Engine

**Дата:** 2026-08-14 (обновлено: исправление router / latency-escalation)
**Приоритет сессии:** CORE / INTELLIGENCE / AGENTIC ENGINE (НЕ UI).
**Подход:** сначала аудит существующего, затем минимальный архитектурный
переход (эволюция, не reset — §26).

---

## 0. ДОПОЛНЕНИЕ — FIX: Router / Latency Escalation (ТЗ отдельной задачи)

### Проблема (подтверждена реальными логами)
После `python main.py` локальная Qwen3-4B грузилась, но обычный запрос
("голос добавить", "привет") приводил к `scope=escalate tier=analyst`,
затем — из-за отсутствия ключа у analyst — к загрузке локальной **7B coder**
модели. Это делало систему непригодной: тяжёлая модель грузилась «на каждый
чих», а лог пестрил `classify() превысил бюджет задержки: 3.24 с > 1.50 с`.

### Корень (реальный, не догадка)
1. `core/router/local_face.py`: `_CLASSIFY_SYSTEM_PROMPT` явно инструктировал
   модель «Если сомневаешься — выбирай escalate/analyst», и сопоставлял
   `analyst` = анализ/объяснения/вопросы. Любой нетривиальный запрос
   классифицировался как escalate. К тому же нераспарсенный JSON падал в
   `escalate/analyst`.
2. `core/router/council.py`: `_handle_escalate` через
   `resolve_next_available_tier` поднимался ВВЕРХ по цепочке. При
   недоступном `analyst` (нет API-ключа) он падал на **локальный coder**
   (GGUF присутствует) — и грузил 7B.
3. `local_latency_budget_sec` в `local_face.py` (строка 165) сравнивал
   `elapsed > budget` и логировал WARNING — сам по себе НЕ эскалировал, но
   создавал ложное впечатление «slow == incapable». Семантика параметра была
   неверной (hard-budget вместо soft-target).

### Что изменено (минимально, без переписывания архитектуры)
| Файл | Изменение |
|------|-----------|
| `core/router/local_face.py` | Промпт классификатора переформулирован: **self ПО УМОЛЧАНИЮ**, escalate только при объективной нужде в capability другого тира; «если сомневаешься — self». Нераспарсенный JSON → **self** (не escalate). Латентность теперь ТОЛЬКО телеметрия (`_latency_target`), превышение НЕ влияет на scope. Параметр `_latency_budget` → `_latency_target`. |
| `config/settings.py` | `local_latency_budget_sec` → **`local_latency_target_sec`** (soft target/telemetry). Старое имя оставлено как deprecated alias и мигрируется при загрузке. Удалён ложный HARD-бюджет. |
| `config/settings.json`, `settings.example.json` | Ключ переименован в `local_latency_target_sec`. |
| `core/router/council.py` | `_handle_escalate` переписан: при недоступном запрошенном тире НЕ грузит тяжёлую локальную модель «просто так». Если выше по цепочке есть реально доступный и более мощный тир — берём; если следующий доступный — локальный тяжёлый (coder/architect), который не был запрошен — **деградируем до FAST** вместо загрузки 7B. Удалён неиспользуемый `next_tier_name`. |
| `core/memory/long_term.py`, `core/memory/document_rag.py` | Подавлена сломанная телеметрия ChromaDB (`capture() takes 1 positional argument but 3 were given`) — no-op адаптер `posthog.capture`, функциональность памяти/RAG не затронута. Также передан `anonymized_telemetry=False`. |

### Критерии успеха (ТЗ) — ВЫПОЛНЕНЫ
- `python main.py` + "привет" / "голос добавить" → **НЕ** ведёт к escalate→загрузке coder 7B.
- В логах допустимо: `classify latency: 3.24 s (цель 1.5 s — телеметрия, не влияет на роутинг)`. НЕТ: `escalation because latency exceeded`.
- Тест реальным запросом: "привет" → `tier=fast`, `NEW backends loaded: 0`.
- "напиши код на питоне" → `tier=fast` (локальная Qwen отвечает; coder не грузится без явной нужды).
- Телеметрия Chroma: шум **устранён** (0 WARNING).
- Старый тестовый прогон `scripts/test_core_scenarios.py`: **23/23 PASS** (без регрессий).
- Tier system (fast/analyst/coder/architect) сохранён; routing не отключён; escalation работает при РЕАЛЬНОЙ нужде (код/архитектура/внешняя модель с ключом).


Проект **не пустой** — есть зрелое ядро. Структура:

```
core/
  agent.py            ← ЗАГЛУШКА С БАГОМ (SyntaxError, модуль не импортировался)
  orchestrator.py     ✓ работает
  task_runtime.py     ✓ отличный (Mission, EventBus, статусы)
  router/             ✓ CouncilRouter, LocalFace, tiers
  llm/                ✓ local_qwen (реально грузит Qwen3-4B), factory, tiers
  actions/            ✓ 14 инструментов, registry, executor
  memory/             ✓ RAG, ChromaDB, graph, long-term
  verifier.py         ⚠ падает на ActionResult (dataclass)
  repair.py           ⚠ битый __init__ (TypeError) + неверный fallback
  ingest.py           ✓ works
  skill_forge.py      ✓ works
  model_router.py     — отсутствовал
  capabilities.py     — отсутствовал
  structured.py       — отсутствовал
  safety.py           — отсутствовал
  research.py         — отсутствовал
scripts/  config/  data/  persona/  main.py  hud/  jarvis/ (Tauri)  jarvis-ui/ (Tauri)
```

Qwen3-4B: `C:\Users\WwW\Downloads\Qwen3-4B-Instruct-2507-Q5_K_M.gguf`
(2.89 GB) → скопирован в `data/models/` **без удаления оригинала**,
MD5 идентичен (было проверено).

**Архитектурные конфликты с новым концептом:** отсутствовали слои
Capability Registry, Structured Output, Safety, Research, Model Router
(по сложности). `agent.py` был нерабочей заглушкой. Найдено несколько
реальных багов (см. §3).

---

## 2. Изменения

### Новые модули
| Модуль | Назначение | ТЗ |
|--------|-----------|-----|
| `core/capabilities.py` | паспорта инструментов + tool retrieval | §12 |
| `core/structured.py` | parse/repair/validate JSON-решений модели | §13 |
| `core/safety.py` | risk-гейт + prompt-injection изоляция | §21, §22 |
| `core/model_router.py` | выбор модели по СЛОЖНОСТИ | §15, §17 |
| `core/research.py` | отдельный research workflow | §18 |
| `core/agent.py` | контроллер миссии (переписан с нуля) | §3, §8 |

### Исправления (реальные баги, подтверждены тестами)
| Баг | Файл | Исправление |
|-----|-----|-------------|
| `SyntaxError` — модуль не импортировался | `agent.py` | переписан в полный mission loop |
| `ActionResult.get()` — AttributeError | `verifier.py` | работа с dataclass, реальные verifier-ы |
| `TypeError` в `RepairLoop.__init__` | `repair.py` | `int(max_attempts)` |
| вечный цикл при смене fallback-инструмента | `repair.py` | корректный switch + `_adapt_args` |
| `open_app` НЕ запускал приложения (shlex ел `\`) | `app_control.py` | путь как есть, аргументы `shlex(posix=False)` |
| `import time` после использования | `orchestrator.py` | перенесён наверх |

### Дополнения
- `task_runtime.py`: расширен словарь событий (§23), поля `Mission` (§6:
  progress, model_used, tools_used, errors, verification, acknowledgement).
- `orchestrator.py`: **добавлен** async-API (`submit_goal`, `wait_for`,
  `cancel_mission`, `list_missions`, `subscribe_events`) поверх
  существующего `handle_input` (сохранён для обратной совместимости).
- `capabilities.py`: fallback-граф очищен от семантически мёртвых
  переходов (search_files→list_files мог ложно подтвердить успех).

---

## 3. Тесты (§25) — 11 сценариев ТЗ

Запуск: `python scripts/test_core_scenarios.py`
Реальные: настоящие инструменты, реальная Qwen3-4B (где нужна),
настоящая верификация. Никаких фиктивных PASS.

| # | Сценарий (ТЗ §25) | Результат |
|---|-------------------|-----------|
| 1 | "Привет." → быстрый local response | ✅ PASS |
| 1b| простая задача НЕ эскалирует к внешней модели | ✅ PASS |
| 2 | "Открой блокнот" → fast path + verify | ✅ PASS |
| 2b| используется fast path (без планирования) | ✅ PASS |
| 3 | "Найди файл X" → файловый поиск | ✅ PASS |
| 4 | "Создай документ" → plan → tool → verify | ✅ PASS |
| 5 | "Изучи проект" → research mission | ✅ PASS |
| 5b| без источников НЕ утверждает "готово" | ✅ PASS |
| 6 | Unknown task → учиться, НЕ "я не умею" | ✅ PASS |
| 6b| создаётся черновик навыка (draft) | ✅ PASS |
| 7 | Огромный ввод → НЕ отказ по размеру (ingest) | ✅ PASS |
| 8 | Tool failure → repair loop | ✅ PASS |
| 8b| repair честно сообщает неудачу (без ложного успеха) | ✅ PASS |
| 9 | Долгий ответ модели → НЕ fail по времени | ✅ PASS |
| 9b| в коде НЕТ лимита мышления (grep elapsed>3) | ✅ PASS |
| 10| External API недоступен → graceful fallback | ✅ PASS |
| 10b| приватные данные → принудительно локально | ✅ PASS |
| 11| Verification failure → НЕ "готово" | ✅ PASS |
| 11b| отсутствие строгой проверки помечено честно | ✅ PASS |
| S1| HIGH risk требует подтверждения (§21) | ✅ PASS |
| S2| prompt injection обнаружен и изолирован (§22) | ✅ PASS |
| S3| плохой JSON отремонтирован, не роняет систему (§13) | ✅ PASS |
| S4| выдуманный инструмент модели отклонён | ✅ PASS |

**ИТОГО: 23/23 PASS.**

### Конец-в-конец smoke-тест Orchestrator
- `submit_goal("Открой калькулятор")` → событие `acknowledged` ("Принято,
  сэр.") немедленно → fast path → `open_app` → процесс `calc.exe`
  подтверждён верификатором `process_running` → статус `completed`,
  `verified: True`. ✅

---

## 4. PASS / FAIL (честно)

- ✅ Agentic engine собран и работает (fast path, plan+execute+verify,
  repair, research, unknown-task, large-input).
- ✅ Все 11 сценариев ТЗ + безопасность пройдены (23/23).
- ✅ Qwen3-4B зарегистрирована, проверена (MD5), реально инференсит.
- ✅ Ни один «лимит мышления в 3 секунды» не внедрён (проверено grep + тест 9b).
- ⚠️ External model escalation (analyst/coder/architect) НЕ проверена
  реальными вызовами — API-ключи отсутствуют. Логика graceful-fallback
  проверена (тесты 10/10b). Это FAIL только по критерию «реальный вызов
  внешней модели», но КОРРЕКТНО деградирует.
- ⚠️ Skill Forge авто-проверка (`mark_verified` из `draft`→`stable`) ещё
  не вызывается агентом (требует безопасного sandbox) — навык остаётся
  `draft` (соответствует §9).
- ⚠️ TTS/STT не тестировались (вне scope ядра).

---

## 5. Ограничения

1. External-модели не настроены → эскалация проверена только на уровне
   логики роутера/маршрутизатора, не реальными HTTP-вызовами.
2. Skill Forge: черновики создаются, но автоматическая проверка процедур
   отложена до реализации безопасного sandbox-тестирования.
3. Frontend (Tauri) НЕ трогался — по ТЗ это был не приоритет. События
   `task_runtime` (§23) уже готовы к подключению UI.
4. ChromaDB telemetry warning (`capture() takes 1 positional argument but 3
   were given`) — безвредный баг обёртки, не влияет на память.

---

## 6. Следующий шаг

1. **External model escalation**: добавить реальные API-ключи в
   `config/settings.json` (deepseek/openrouter/...) и проверить живой
   вызов analyst/coder/architect через `CouncilRouter` + `ModelRouter`.
2. **Skill Forge авто-проверка**: sandbox-тест процедур → `mark_verified`
   (draft→stable), чтобы навыки реально переиспользовались.
3. **UI-подключение**: подписать фронтенд на `orchestrator.subscribe_events`
   и рендерить события (§23) как operational event timeline.
4. **Computer Control fallback hierarchy** (§19): добавить CLI/Python/
   UI-Automation уровни поверх существующих системных инструментов.

---

## 7. ДОПОЛНЕНИЕ — смена голоса + удаление 7B coder-модели (2026-08-14)

### Голос: irina -> dmitri
- Удалён женский `ru_RU-irina-medium` (плохая интонация). Русский голос теперь
  `ru_RU-dmitri-medium` (мужской, medium) — скачан и проверен реальным
  синтезом (WAV 2.68s, RIFF, без ошибок). ruslan НЕ использован (известный баг
  с чтением русского в rhasspy/piper).
- `voice.piper_voices[ru]` в `config/settings.json` -> `ru_RU-dmitri-medium.onnx`.
  Английский `jarvis-medium` не тронут. Логика anti-override
  (`use_model_tuning`/`_config_has_tuning`) работает для Dmitri автоматически:
  его `.onnx.json` содержит noise/length -> tuning применяется (не искажается).

### Удалена 7B coder-модель (qwen2.5-coder-7b-instruct-uncensored)
- Файл `data/models/qwen2.5-coder-7b-instruct-uncensored.gguf` (~5.3 ГБ) удалён
  с диска. Было временным решением, реально не требовался — coder-тир идёт
  через удалённые Kimi/DeepSeek.
- `config/settings.json`: `model_tiers.coder` -> `kimi-k3`,
  `tier_providers.coder` -> `kimi`, `local_coder_model.gguf_path` -> `""`.
  Архитектура локального coder-бэкенда сохранена (блок `local_coder_model`
  на месте) — убрана ТОЛЬКО конкретная регистрация ЭТОЙ модели.
- `config/settings.py`: default `LocalCoderModelConfig.gguf_path` -> `""`.
- `core/llm/factory.py` / `core/llm/tiers.py` — НЕ содержат захардкоженных
  имён файлов (полностью конфиг-драйвен), правок не требуют.
- `модели` / ModelManager.list_models(): coder больше НЕ числится как local.
- Проверено: "напиши функцию на Python для сортировки списка" -> tier=fast
  (Qwen3-4B), попыток загрузить удалённый gguf нет; coder-эскалация идёт на
  удалённый Kimi (или честно "недоступен" без ключа), без file-not-found.

### GPU-диагностика (см. отдельный раздел / Task 4)
- `llama_cpp.llama_supports_gpu_offload()` в активном venv вернул **False** ->
  установлена CPU-сборка llama-cpp-python (не CUDA). Подтверждено эмпирически
  (nvidia-smi + verbose лог загрузки) и устранено переустановкой CUDA-wheel.
