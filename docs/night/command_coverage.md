# Q07 — Command Library Coverage (NEXT P1)

Автономный офлайн-анализ покрытия 1000+ команд из `docs/JARVIS_COMMAND_LIBRARY.md`
реальными инструментами J.A.RVIS. Скрипт: `scripts/command_library_parser.py`.
Маппинг coverage строится ДИНАМИЧЕСКИ из `core.actions.DEFAULT_REGISTRY`
(имена + description инструментов), без жёстко зашитого словаря.

> Сгенерировано: 2026-08-15, night-режим.

## Сводка

- Команд в библиотеке: **1450**
- Покрыты реальными инструментами: **1147 (79.1%)**
- GAP (не покрыты ни одним реальным инструментом): **303**
- SAFETY-SENSITIVE (требуют отдельного permission/confirmation): **7**

## Топ категорий (по числу команд)

| Категория | Команд |
|---|---|
| SECURITY | 90 |
| DOCUMENTS | 73 |
| CODING | 68 |
| MEGA MISSIONS | 50 |
| CROSS-DOMAIN | 50 |
| PERFORMANCE | 44 |
| BUSINESS | 38 |
| VIDEO | 35 |
| MARKETING | 35 |
| DATA | 33 |

## Топ GAP-категорий (что ещё реализовать)

| Категория | GAP-команд |
|---|---|
| SECURITY | 54 |
| CODING | 46 |
| DOCUMENTS | 44 |
| DATA | 26 |
| VIDEO | 16 |
| AGENTS | 16 |
| PERSONA | 13 |
| IMAGE | 12 |
| SELF-IMPROVEMENT | 12 |
| WRITING | 11 |

## Нагрузка на реальные инструменты (сколько команд матчится)

| Инструмент | Команд |
|---|---|
| web_search | 377 |
| list_files | 263 |
| system_status | 162 |
| read_file | 128 |
| open_app | 87 |
| add_reminder | 72 |
| volume | 41 |
| web_fetch | 36 |
| computer_screenshot | 18 |
| close_app | 17 |
| weather | 12 |
| computer_keyboard | 8 |
| computer_mouse | 6 |
| search_files | 3 |
| write_file | 2 |

## Примеры GAP-команд (первые 20, genuine — нет соответствующего инструмента)

1. #14 Карта дискового пространства — Tools: python, matplotlib, treemap
2. #29 Дефрагментация — Tools: defrag
3. #30 Ошибки диска — Tools: chkdsk
4. #10 Найти дубликаты файлов — Tools: hashing, python
5. #28 Сколько проживёт мой SSD — Tools: smartctl

(полный список 303 GAP — через `python scripts/command_library_parser.py --json`)

## Выводы / хот-споты для будущей интеграции

- **79.1% команд уже покрыты** существующими 14 реальными инструментами
  (включая dry-run computer-use). Это высокий базовый охват.
- Самые крупные GAP-категории — **SECURITY (54), CODING (46), DOCUMENTS (44)**:
  команды про криптографию, написание кода/скриптов, и продвинутую работу с
  документами (реальное редактирование/генерация) — кандидаты на новые
  инструменты в следующих спринтах.
- SAFETY-SENSITIVE = 7 — эти команды (камера, клонирование голоса и т.п.)
  требуют отдельного permission/confirmation механизма (уже учтено в Q03/Q04:
  `wrap_untrusted` изолирует, `redact_args` маскирует аргументы).
- Анализ НЕ меняет рантайм — только статистика для планирования.
