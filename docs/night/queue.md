# NIGHT QUEUE — P1 continuation (autonomous, no owner-ask)

Источник очереди: P0/P1 DoD из `docs/architecture/02_target_architecture.md`
+ NEXT P1 backlog (интеграция команд из `docs/JARVIS_COMMAND_LIBRARY.md`,
computer-use слой, UI polish). Базовая линия тестов: `baseline_tests.txt` (17/17 PASS).

Правила:
- НЕ писать в чат с ожиданием ответа. Статус — в LOG.md / STATE.json.
- computer-use ТОЛЬКО через fake/dry-run (никаких реальных мыши/клавиатуры).
- HIGH-risk confirmation flow — НЕ трогать, держать регрессионный щит зелёным.
- 3 неудачи / 25 мин без прогресса → parked + причина в BLOCKERS.md.

## Статусы
- todo / doing / done / parked

## ОЧЕРЕДЬ

| id | задача | источник | DoD-критерий | статус |
|----|--------|----------|--------------|--------|
| Q01 | Гибридный tool-retrieval (keyword+embedding) | P1 §2 | retrieve() ловит синонимы («поставь будильник»→add_reminder); тест offline; без регрессий | done |
| Q02 | Единый источник truth tool-схем | P1 §2 | регистрация Tool авто-порождает capability-паспорт; capabilities.py не дублирует схемы вручную | done |
| Q03 | wrap_untrusted на все недоверенные источники | P0 §4 | web_fetch/web_search/read_file/rag-результат оборачиваются; тест: инъекция изолирована | done |
| Q04 | redact_secrets() в логах args | P0 §4 | verifier/repair/agent печатают args без секретов; тест | done |
| Q05 | SSRF-защита сетевых тулз | P0 §4 | web_fetch блокирует 127/10/192.168/169.254/localhost/file://; тест | done |
| Q06 | Computer-use слой (FAKE/dry-run backend) | P1 §6 + NEXT | mouse/keyboard/screenshot как tools с dry-run; тесты НЕ двигают реальную мышь | todo |
| Q07 | Интеграция 1000+ команд в тестовый корпус | NEXT P1 | скрипт парсит JARVIS_COMMAND_LIBRARY.md → реестр команд↔capabilities; подсчёт+маппинг+хот-споты | todo |
| Q08 | UI: createRealBackend (WS/мост) + маппинг статусов | P1 §5 | BackendAdapter реальный мост; EntityState/BackendEventType расширены; типы консистентны | todo |
| Q09 | Morning report + финальный checkpoint | — | docs/night/MORNING_REPORT.md | todo |
