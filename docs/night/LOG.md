# NIGHT LOG — P1 continuation (autonomous)

## 2026-08-15 05:0x — Q01+Q02 реализация (коммит ad08535)
- Гибридный tool-retrieval (keyword+embedding) + CapabilityRegistry из ToolRegistry.
- P1 §1.4 proxy-конфиг в Settings. FULL SUITE: 19 passed, EXIT=0.

## 2026-08-15 05:3x — Q03: wrap_untrusted на недоверенные источники (P0 §4)
- КРИТИЧЕСКОЕ УТОЧНЕНИЕ: `wrap_untrusted` УЖЕ существует в `core/safety.py:209`
  и применён в `research.py:285`. Создавать `core/security.py` = дублировать.
  Удалён мой дубликат `core/security.py`.
- Вместо новой утилиты — ПРИМЕНИЛ существующий `wrap_untrusted` на 4 границы:
  * `WebFetchTool.run` — оборачивает preview (source="web_fetch (url)").
  * `WebSearchTool.run` — оборачивает каждый snippet (source="web_search (url)").
  * `ReadFileTool.run` — оборачивает содержимое файла (source="read_file (path)").
  * `DocumentRAG.search_documents` — оборачивает каждый RAG-чанк (source="RAG").
  Единая точка обёртки на границе инструмент/rag→модель (§22).
- Сделал `wrap_untrusted` ИДЕМПОТЕНТНОЙ: повторный вызов (напр. из research.py
  поверх web_fetch-вывода) НЕ создаёт вложенных конвертов (маркер "--- КОНЕЦ
  ДАННЫХ ---" → возврат как есть).
- ДОБАВЛЕН `tests/test_security_q03.py`: структурная изоляция (маркеры границ +
  data-vs-instruction до начала данных), идемпотентность, read_file оборачивает,
  web_search оборачивает сниппеты.
- Верификация: FULL SUITE = **23 passed, EXIT=0** (19 + 4 Q03). Без skip/удаления
  ассертов.
- secret_filter.py НЕ трогал (это про память, P1 §1.5 — комплиментарно, не дублировать).

## Следующий
- Q04: redact_secrets() в логах args (verifier/repair/agent печатают args без секретов).
