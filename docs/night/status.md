# NIGHT STATUS — автономный прогон P1

Обновлено: 2026-08-15 ~05:30 (автономно, без остановки на подтверждение)

## Базовая линия (скорректирована)
- Ранее заявлялось «17/17 PASS» — НЕВЕРНО (ошибка раннего прогона).
- Честная базовая линия на оригинальном коде (до Q01/Q02): **18 passed + 1 pre-existing FAIL**
  — `test_p1_from_settings_proxy_mode` → `Settings has no attribute 'proxy'`.
  Доказано stash-тестом: падает и на оригинальном `capabilities.py`. Не регрессия Q01/Q02.
- После Q01/Q02 + proxy-фикса: **19 passed, EXIT=0** (`docs/night/tests_after_all_fixes.txt`).

## Выполнено
| id | что | статус | evidence |
|----|-----|--------|----------|
| Q01 | Гибридный tool-retrieval (keyword+embedding, ChromaDB MiniLM) | DONE | suite 19/19; synonym-тесты ловят синонимы; coverage 14/14 |
| Q02 | Единый источник truth (`CapabilityRegistry` авто-покрывает `ToolRegistry` + `_CAP_ANNOTATIONS` только для качественных полей) | DONE | `missing caps: []`; `describe_tools_for_model` берёт схему из `ToolRegistry` |
| P1§1.4 | Proxy-конфиг в `Settings` (`ProxyConfig` + поле `proxy` + `example.json`) | DONE | `test_p1_from_settings_proxy_mode` зелёный; `Settings().proxy` инстанциируется |

## Конкурентность sibling-агентов
- Sibling `20260815_035248_53bc98` вставил дубликат `class ProxyConfig` (line 169). Удалён; остался единственный (line 374).
- `git status` показывает много staged `AUDIT_*.md` / `audit_*.md` от sibling-агентов. Коммитим ТОЛЬКО свои файлы явными путями — НЕ `git add -A`, НЕ `git add .`.

## Git
- HEAD unborn (branch `master` без коммитов). `git checkout HEAD` падает (`invalid reference`) — ожидаемо.
- Коммит: только `config/settings.py`, `config/settings.example.json`, `core/capabilities.py`, `docs/night/`.

## Следующий
- Q03 (`wrap_untrusted` на недоверенные источники) — начат сразу после коммита.
