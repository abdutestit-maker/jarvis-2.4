# NIGHT LOG — P1 continuation (autonomous)

## 2026-08-15 05:0x — Q01+Q02 реализация (коммит ad08535)
- Гибридный tool-retrieval (keyword+embedding) + CapabilityRegistry из ToolRegistry.
- P1 §1.4 proxy-конфиг в Settings. FULL SUITE: 19 passed, EXIT=0.

## 2026-08-15 05:3x — Q03: wrap_untrusted на недоверенные источники (P0 §4)
- КРИТИЧЕСКОЕ: `wrap_untrusted` УЖЕ существует в `core/safety.py:209` (применён в
  `research.py:285`). НЕ создавать `core/security.py` (дубль/уязвимость).
- ПРИМЕНИЛ существующий `wrap_untrusted` на 4 границы: WebFetchTool, WebSearchTool
  (сниппеты), ReadFileTool, DocumentRAG.search_documents. Сделал идемпотентной.
- Тесты: tests/test_security_q03.py. FULL SUITE = 23 passed (19+4), EXIT=0.
- Коммит b776060.

## 2026-08-15 05:4x — Q04: redact_secrets() в логах args (P0 §4)
- Создал `core/redact.py`: `redact_args` (рекурсивно маскирует секреты в структуре
  args) + `redact_secrets` (маскирует строку). Переиспользует `_RE_SECRET` из
  `core/memory/secret_filter.py` (НЕ дублирует паттерн секретов; secret_filter
  отвечает за очистку КОНТЕНТА для памяти, P1 §1.5 — комплиментарно).
- Применил `redact_args` на 3 точки печати args:
  * core/agent.py:632  FAST PATH лог
  * core/orchestrator.py:427  tool_call лог
  * core/repair.py:135  repair лог
- Логирует НЕ мутируя исходные args (копия). Идемпотентно.
- Тесты: tests/test_security_q04.py (маскировка api_key/token/password, рекурсия,
  идемпотентность, caplog: секрет НЕ попадает в лог открыто).
- Верификация: FULL SUITE = **27 passed (23+4), EXIT=0**. Без skip/удаления ассертов.
- ИСПРАВЛЕНИЕ: первый вариант теста имел неверный assertion (ждал "api_key=***",
  реально "<secret>" — весь секретный кусок маскируется единым маркером, это
  корректное поведение). Поправлен assertion, НЕ код.
- Коммит 898f7c7.

## 2026-08-15 05:5x — Q05: SSRF-защита сетевых тулз (P0 §4)
- Создал `core/network_guard.py`: `is_ssrf_blocked(url)`, `assert_safe_url(url)`,
  `SSRFBlocked(ValueError)`. Блокирует loopback/127.0.0.0/8, private (10/8, 172.16/12,
  192.168/16), link-local/cloud-metadata (169.254.0.0/16, вкл. 169.254.169.254),
  unspecified (0.0.0.0/::), а также не-http(s) схемы (file://, ftp://, gopher://) и
  явные опасные имена (localhost, metadata.google.internal). Резолвит имя хоста в IP
  и проверяет результирующий IP (ловит внутреннее имя/DNS-имя), не только литерал.
- Применил в `core/actions/web_fetch.py:fetch_page` — `assert_safe_url(url)` ДО
  `requests.get`. `web_search.py` только парсит DDG (не фетчит URL) — поверхность
  атака только web_fetch.
- Тесты: tests/test_security_q05.py — блокировка internal/metadata/file/ftp + пропуск
  public + WebFetchTool.run возвращает ok=False на заблокированный URL (не уходит в
  сеть, не падает).
- Верификация: FULL SUITE = **32 passed (27+5), EXIT=0**. Без skip/удаления ассертов.
- ИЗВЕСТНОЕ ОГРАНИЧЕНИЕ (non-blocking): DNS-rebinding TOCTOU — `network_guard`
  резолвит, а `requests.get` резолвит повторно; между проверкой и коннектом имя
  теоретически может сменить IP. Для P0 §4 (офлайн/тест, блокируются все private
  диапазоны) приемлемо. Для полной стойкости нужно пинить резолвленный IP —
  оставлено на будущий харденинг.
- Коммит 36dcb9a.

## 2026-08-15 05:6x — Q06: Computer-use слой (FAKE/dry-run, P1 §6 + NEXT)
- ЖЁСТКО: НИКАКОЙ реальной мыши/клавиатуры/скриншота (необратимые эффекты в 3 ночи).
- Создал `core/actions/computer_use.py`: `DryRunInputController` (накопитель
  намерений) + 3 инструмента `computer_mouse` / `computer_keyboard` /
  `computer_screenshot`. `run` ТОЛЬКО записывает намерение и возвращает
  `[dry-run] ... реальный ввод НЕ выполнен`. НЕ импортирует pyautogui/ctypes/
  pynput/win32api/SendInput — кода для реального ввода физически НЕТ.
- Инструменты авто-регистрируются в DEFAULT_REGISTRY (появляются в retrieval
  агента, но выполняются как симуляция). `system.py` (pyautogui для громкости) НЕ
  трогал — законный фоллбэк, не computer-use.
- Тесты: tests/test_security_q06.py — инструменты зарегистрированы, возвращают
  ok=True с пометкой dry-run, намерения записываются, контроллер помечен dry_run,
  и AST-анализ подтверждает отсутствие импортов/вызовов реальных библиотек ввода
  (docstring-упоминания игнорируются).
- Верификация: FULL SUITE = **38 passed (32+6), EXIT=0**. Без skip/удаления ассертов.
- ИСПРАВЛЕНИЕ: первый вариант test_no_real_input_libraries_imported падал (проверял
  'pyautogui' not in sys.modules — но он импортирован в среде через system.py).
  Переписан на AST-анализ (нет импортов + нет ссылок в коде вне docstring).

## 2026-08-15 05:59 — Q07: Интеграция 1000+ команд (NEXT P1)
- Чистый офлайн-парсинг docs/JARVIS_COMMAND_LIBRARY.md (1450 записей) →
  реестр команд↔capabilities. `scripts/command_library_parser.py`.
- КРИТИЧЕСКОЕ (как с core/security.py): НЕ зашивать keyword-map → сделал
  ДИНАМИЧЕСКИ из `core.actions.DEFAULT_REGISTRY` (имена + description).
  Убрал dead `_REAL_TOOLS`. Gap-анализ отражает АКТУАЛЬНЫЕ возможности,
  не дрейфует при добавлении инструментов.
- Результат: 1450 команд, покрыто 1147 (79.1%), GAP 303, SAFETY-SENSITIVE 7.
  Топ GAP-категорий: SECURITY(54), CODING(46), DOCUMENTS(44). Отчёт в
  docs/night/command_coverage.md (полный + --json dump). GAP-записи genuine
  (проверено: #14 python/matplotlib, #29 defrag, #30 chkdsk — нет инструментов).
- Тесты: tests/test_command_library_q07.py (count>1000, #001 parse, stats dict,
  dynamic-registry index, _REAL_TOOLS удалён). Изолированно ЗЕЛЁНЫЙ (4 passed).
- ИЗВЕСТНЫЙ BLOCKER (НЕ мой): sibling-агент изменил core/agent.py (M, unstaged)
  — добавил вызов `self._start_confirmation_watchdog(conf_id)` в confirm-ветке
  (~строка 400), метод НЕ существует → `test_p0_sprint::test_p0_high_risk_
  confirmation_loop` падает AttributeError. Это HIGH-risk confirmation flow
  (правило queue: НЕ трогать) — я его НЕ чиню и НЕ коммичу. Мой Q07 от agent.py
  не зависит и зелёный в изоляции. Зафиксировано для координации.

## 2026-08-15 06:0x — Q08: UI `createRealBackend` (реальный мост) + маппинг статусов (P1 §5)
- КРИТИЧЕСКОЕ (как с core/security.py): `createRealBackend()` УЖЕ существует
  в `jarvis/src/integrations/backend.ts:190` как ЗАГЛУШКА. НЕ дублировал —
  реализовал транспорт ВНУТРИ неё. `EntityState`/`BackendEventType`/
  `BackendAdapter` уже определены в `types/index.ts` (НЕ создавал заново).
- Реализация: биндинг к Tauri event bus — inbound `jarvis://event`
  (→ `mapTransportEvent` → `BackendEvent`), outbound команды `jarvis://command`
  + `jarvis://interrupt`. Mock-fallback вне Tauri (vite dev/preview), чтобы UI
  не ломался без рантайма. Channel-имена (`jarvis://*`) — контракт с core;
  если core шлёт иначе, сверить на стыке.
- Статус-маппинг вынесен в ЕДИНЫЙ источник `TRANSPORT_STATE_MAP`
  (`backend.ts`) + `mapTransportEvent()`; `useBackendBridge.ts` теперь
  импортирует `TRANSPORT_STATE_MAP` вместо дублирующегося локального `STATE_MAP`
  (DRY). `STATE_LABEL` (UI-лейблы) оставлен как есть.
- `jarvis-ui/src` — НЕ живой корень (в `jarvis/package.json` те же скрипты +
  `@tauri-apps/api`; правил по grep-совпадениям в `jarvis/src`). Патчил
  только `jarvis/`.
- Верификация: TS-test-runner отсутствует (нет vitest/jest/`test` в
  package.json) → НЕ фейково green. Честный verification = `tsc --noEmit`
  по `jarvis/`: **TSC_EXIT=0 (чисто)**. Одиннадцатая ошибка type-fix
  (`fallback: BackendAdapter | null`) исправлена.
- ИЗВЕСТНЫЙ BLOCKER (verification): full TS-сборка `npm run build` не гнал
  (нет гарантии, что остальной `jarvis/` tree типобезопасен вне tsc-проверки
  моих файлов) — ограничился `tsc --noEmit` на проекте (он проверяет весь
  `include`, вернул 0). Браузерный e2e/mount не запускал (нет рантайма Tauri).
- Коммит: только `jarvis/src/integrations/backend.ts`,
  `jarvis/src/hooks/useBackendBridge.ts`, `docs/night/LOG.md`,
  `docs/night/queue.md`. `core/agent.py` (sibling WIP) НЕ в staging.

## 2026-08-15 06:1x — Q09: Morning report + финальный checkpoint
- КРИТИЧЕСКОЕ (ловушка дублирования, как Q03/Q08): `docs/night/STATE.json`
  УЖЕ существовал (старый: branch night/p1-continuation, last_commit fe861cc).
  НЕ перезаписал вслепую — обновил поля (branch=main, last=eb09d3a,
  current=Q09, completed=[Q01..Q08], blockers) + добавил completed/blockers.
- Создал `docs/night/MORNING_REPORT.md`: итоговая таблица Q01–Q09, дисциплины
  (не дублировать / изолированный коммит / computer-use dry-run), известные
  блокеры (sibling core/agent.py), verification-статус (PY isolated green,
  TS tsc=0, baseline 17/17).
- Все Q01–Q09 ЗАВЕРШЕНЫ и (кроме Q09) ЗАКОММИЧЕНЫ. Night P1 continuation закрыт.
- Коммит: только docs/night/STATE.json, docs/night/MORNING_REPORT.md,
  docs/night/LOG.md, docs/night/queue.md. core/agent.py (sibling WIP) НЕ в staging.

## ФИНАЛ
- Night autonomous sprint Q01–Q09: выполнен полностью, без пауз.
- Полный `pytest` красный ТОЛЬКО из-за sibling-блокера в core/agent.py
  (HIGH-risk confirmation flow, НЕ трогал). Мои задачи зелёные в изоляции.
- Рекомендация дня: sibling-агенту добавить `_start_confirmation_watchdog`
  (или убрать вызов), чтобы вернуть full-suite зелёным.
