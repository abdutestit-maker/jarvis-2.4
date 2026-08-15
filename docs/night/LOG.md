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

## Следующий
- Q05: SSRF-защита сетевых тулз (web_fetch блокирует 127/10/192.168/169.254/
  localhost/file://; тест). Check: уже есть ли валидация URL в web_fetch/web_search?
