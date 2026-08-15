# J.A.R.V.I.S. 3.0 — Архитектурная документация

> Цель: превратить сырой `E:\jarvis-project` в полноценного **desktop-resident
> general-purpose AI agent** для Windows как закрытый коммерческий продукт.
> J.A.R.V.I.S. — НЕ чат-бот и НЕ assistant. Это живая цифровая сущность,
> интерфейс — command bridge, а не messenger.

## Индекс документов

| Файл | Назначение |
|------|-----------|
| [00_current_state_and_gaps.md](./00_current_state_and_gaps.md) | Что реально есть в ядре сейчас: структура, карта компонентов, KEEP-ядро, критические блокирующие факторы, latency-бутылки, пути к файлам. |
| [01_donor_pattern_synthesis.md](./01_donor_pattern_synthesis.md) | Лучшие REIMPLEMENT-паттерны из 23 доноров: agent loop, tool registry, planning, computer-use, browser, memory/research + матрица REIMPLEMENT/ADAPT/BLOCKED. |
| [02_target_architecture.md](./02_target_architecture.md) | Предлагаемая целевая архитектура JARVIS: фиксы model routing, tool registry, fast/long-running, prompt-injection security, UI/voice, computer-use/browser — с приоритетами (P0/P1/P2). |
| [03_roadmap_and_license.md](./03_roadmap_and_license.md) | Лицензионные ограничения (3 блокера: BSL 1.1 / non-commercial / AGPL-3.0), полная матрица 23 доноров, поэтапная дорожная карта, риски. |

## Исходные материалы аудита (на диске, `E:\jarvis-project\`)

- `AUDIT_CURRENT_JARVIS.md` — аудит текущего ядра (AGENT A)
- `audit_computer_use_donors.md` — computer-use / browser доноры (AGENT B)
- `AGENT_RUNTIME_AUDIT_DONORS.md` — agent-runtime / planning доноры (AGENT C)
- `audit_memory_research_donors.md` — memory / research доноры (AGENT D)
- `audit_license_matrix.md` — лицензионная матрица 23 доноров (AGENT E)
- `audit_model_tool_ui_security.md` — model/tool/ui/security синтез (AGENT F)

> ⚠️ Файлы `audit_agent_runtime.md`, `audit_report.md`, `final_report.json` в
> корне описывают НЕ текущий JARVIS, а **донорские** репозитории — не
> использовать как описание текущего состояния.

## Ключевые принципы синтеза

1. **Эволюция, не reset**: сохранить проверенное KEEP-ядро
   (`verifier.py`, `repair.py`, `safety.py`, `capabilities.py`, `registry.py`,
   `llm/*`, `actions/*`, `memory/*`).
2. **REIMPLEMENT, не copy** (лицензии): адаптировать паттерны, не копировать код.
3. **Никакого «лимита мышления в 3 секунды»**: реальные таймауты только внутри инструментов.
4. **Фактическая верификация**: «готово» только после проверки факта.

## Статус

✅ Все 4 документа заполнены (на базе 6 отчётов-аудитов + прямого чтения `core/**` и 23 доноров).
