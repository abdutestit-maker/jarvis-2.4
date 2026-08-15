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
- Коммит: (ниже).

## Следующий
- Q06: Computer-use слой (FAKE/dry-run backend). ЖЁСТКО: НИКАКОЙ реальной мыши/
  клавиатуры/скриншота (необратимые эффекты в 3 ночи). Tools записывают намерение
  и возвращают dry-run подтверждение; никаких pyautogui/ctypes/SendInput. Тесты НЕ
  двигают реальную мышь.
