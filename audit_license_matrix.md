# Лицензионная матрица donor-проектов JARVIS

**Дата аудита:** 2026-08-15
**Аудитор:** leaf-аудитор лицензий (read-only)
**Объём:** 23 donor-проекта из `E:\jarvis-donors` (папки `EVA`, `jarvis`, `jarvis-py` ИСКЛЮЧЕНЫ — не аудировались)
**Цель:** Закрытый коммерческий desktop agent JARVIS (Windows). Ищем **REIMPLEMENT паттернов, НЕ copy code**.
**Метод:** Прочитаны `LICENSE/COPYING/NOTICE` + манифесты (`pyproject.toml/setup.py/package.json/Cargo.toml`) по содержимому, а не по имени файла. Сканирование исключало `node_modules/`, `.git/`, `dist/`, `build/`, `venv/` и бинарные деревья JRE.

---

## 🔴 КРИТИЧНЫЕ БЛОКЕРЫ (коммерческое закрытое использование кода запрещено)

| Donor | Лицензия | Суть блокера |
|-------|----------|--------------|
| **everywhere** | Business Source License 1.1 (BUSL-1.1), Licensor: Sylinko Inc. | «Competing Use» запрещён — это включает коммерческий продукт-заменитель (в т.ч. SaaS/Paas). Change Date = +4 года → потом Apache-2.0. **Код копировать в закрытый продукт НЕЛЬЗЯ.** Только reimplement паттернов с максимальной осторожностью (ни одной строки исходника). |
| **isair-jarvis** | Custom «Jarvis AI Assistant License» (некоммерческая) | Коммерческое использование требует отдельной коммерческой лицензии у автора (baris@writeme.com). По умолчанию — только non-commercial. Копирование кода для коммерческого JARVIS недопустимо. |
| **khoj** | GNU Affero GPL v3 (AGPL-3.0) | Strong copyleft + network copyleft. Любой закрытый коммерческий продукт, включающий код khoj, обязан стать AGPL и опубликовать ВСЕ исходники. Несовместимо с закрытым JARVIS. |

---

## Полная матрица (23 проекта)

| # | Donor | Лицензия (точная, по содержимому) | Коммерческое использование разрешено? | Копирование кода разрешено? | Reimplement паттернов разрешён? | Риски / примечания |
|---|-------|-----------------------------------|----------------------------------------|------------------------------|----------------------------------|---------------------|
| 1 | agent-zero | MIT (c) 2025 Agent Zero, s.r.o. | ✅ Да | ✅ Да (с сохранением copyright notice) | ✅ Да | Низкий. Плагины (`plugins/*`) тоже MIT. |
| 2 | agno | Apache-2.0 (вкл. `libs/agno`, `libs/agnoctl`) | ✅ Да | ✅ Да (NOTICE + patent grant) | ✅ Да | Низкий. Сохранять `NOTICE` и атрибуцию. |
| 3 | autogpt | **СМЕШАННАЯ**: MIT (всё вне `autogpt_platform/`) + PolyForm Shield 1.0.0 (внутри `autogpt_platform/`) | ⚠️ MIT-часть Да; `autogpt_platform` — НЕТ (non-competitive, source-available) | ⚠️ MIT-часть Да; `autogpt_platform` — ограничено (нельзя делать конкурентный продукт) | ⚠️ MIT-часть Да; `autogpt_platform` — НЕТ | Средний. Брать только код вне `autogpt_platform/`. Папку платформы не трогать. |
| 4 | browsergym | Apache-2.0 (c) 2024 ServiceNow | ✅ Да | ✅ Да | ✅ Да | Низкий. |
| 5 | browser-use | MIT (c) 2024 Gregor Zunic | ✅ Да | ✅ Да | ✅ Да | Низкий. |
| 6 | camel | Apache-2.0 (`README.ja.md` — НЕ проблема, читается) | ✅ Да | ✅ Да | ✅ Да | Низкий. `package.json`/pyproject подтверждают Apache-2.0. |
| 7 | everywhere | **Business Source License 1.1 (BUSL-1.1)** — Licensor Sylinko Inc., Change Date +4 г. → Apache-2.0 | ❌ **НЕТ** (Competing Use запрещён, включая коммерческий продукт-заменитель) | ❌ **НЕТ** для Competing Use | ⚠️ Только reimplement паттернов, с осторожностью (без копирования строк) | 🔴 **БЛОКЕР**. См. таблицу выше. |
| 8 | gpt-researcher | **КОНФЛИКТ**: файл `LICENSE` = Apache-2.0 (полный текст, единственный маркер), но манифесты (`setup.py`/`pyproject` = MIT, `package.json` = MIT/ISC) | ✅ Да (Apache-2.0 по файлу LICENSE — авторитетно) | ✅ Да (Apache-2.0, с NOTICE) | ✅ Да | Средний. Официальная лицензия = Apache-2.0 (файл важнее манифеста), но поля в манифестах противоречат — уточнить у автора (assafelovic) перед релизом. |
| 9 | isair-jarvis | Custom «Jarvis AI Assistant License» (non-commercial) | ❌ **НЕТ** (коммерция требует отдельной лицензии) | ❌ Только non-commercial | ❌ Для коммерции — нет (риск обхода лицензии) | 🔴 **БЛОКЕР**. |
| 10 | khoj | **GNU Affero GPL v3 (AGPL-3.0)** | ⚠️ Да, но с copyleft (весь продукт→AGPL, публикация исходников при сетевом use) | ⚠️ Да, но весь производный продукт обязан стать AGPL | ⚠️ Да, но осторожно (функционально схожий код — свой) | 🔴 **ВЫСОКИЙ**. Закрытый JARVIS несовместим. |
| 11 | letta | Apache-2.0 | ✅ Да | ✅ Да | ✅ Да | Низкий. Манифест `package.json`=ISC, но файл LICENSE — Apache-2.0 (авторитетно). |
| 12 | mem0 | Apache-2.0 (все `integrations/*`, `skills/*` тоже Apache-2.0) | ✅ Да | ✅ Да | ✅ Да | Низкий. Вложенные package.json местами ISC/MIT — вторичные, игнорируем. |
| 13 | mirothinker | Apache-2.0 | ✅ Да | ✅ Да | ✅ Да | Низкий. |
| 14 | openai-cua-sample-app | MIT (c) 2025 OpenAI | ✅ Да | ✅ Да | ✅ Да | Низкий. Sample-код OpenAI. |
| 15 | openclaw | MIT (c) 2026 OpenClaw Foundation; `package.json`=MIT | ✅ Да | ✅ Да | ✅ Да | Низкий. Есть `THIRD_PARTY_NOTICES.md` — учесть атрибуцию Apple device IDs (MIT). |
| 16 | openhands | MIT (c) 2025 OpenHands contributors | ✅ Да | ✅ Да | ✅ Да | Низкий. |
| 17 | open-interpreter | Apache-2.0 (c) OpenAI; `package.json`/`Cargo.toml`=Apache-2.0 | ✅ Да | ✅ Да | ✅ Да | Низкий. `NOTICE` указывает Ratatui (MIT) как derived — атрибуция сохраняется. |
| 18 | openjarvis | MIT (c) 2025 OpenJarvis Contributors | ✅ Да | ✅ Да | ✅ Да | Низкий (но имя «openjarvis»/«Jarvis» — возможна trademark-осторожность при нейминге продукта). |
| 19 | pydantic-ai | MIT (c) Pydantic Services Inc.; `clai/`, `examples/`, `pydantic_ai_slim/`, `pydantic_evals/`, `pydantic_graph/` тоже MIT | ✅ Да | ✅ Да | ✅ Да | Низкий. |
| 20 | swarms | Apache-2.0 | ✅ Да | ✅ Да | ✅ Да | Низкий. |
| 21 | swe-agent | MIT (c) 2024 John Yang et al. | ✅ Да | ✅ Да | ✅ Да | Низкий. |
| 22 | ui-tars-desktop | Apache-2.0 (вкл. `multimodal/tarko/llm-client`) | ✅ Да | ✅ Да | ✅ Да | Низкий. |
| 23 | webarena | Apache-2.0 | ✅ Да | ✅ Да | ✅ Да | Низкий. |

---

## Сводка по типам лицензий

| Тип лицензии | Кол-во | Donor-проекты |
|--------------|--------|----------------|
| MIT | 11 | agent-zero, browser-use, openai-cua-sample-app, openclaw, openhands, openjarvis, pydantic-ai, swe-agent |
| Apache-2.0 | 9 | agno, browsergym, camel, letta, mem0, mirothinker, open-interpreter, swarms, ui-tars-desktop, webarena *(прим.: gpt-researcher тоже по файлу Apache-2.0 → фактически 10)* |
| Смешанная (MIT + PolyForm Shield) | 1 | autogpt |
| BUSL-1.1 (source-available) | 1 | everywhere 🔴 |
| Custom non-commercial | 1 | isair-jarvis 🔴 |
| AGPL-3.0 (strong copyleft) | 1 | khoj 🔴 |

**Итого:** 19 проектов — свободно для reimplement в закрытом коммерческом продукте (permissive/Apache, при соблюдении атрибуции). **3 БЛОКЕРА**: `everywhere` (BUSL-1.1), `isair-jarvis` (non-commercial), `khoj` (AGPL-3.0). 1 смешанный (`autogpt` — брать только вне `autogpt_platform/`). 1 конфликт манифестов (`gpt-researcher` — фактически Apache-2.0).

---

## Общие правила интеграции (reimplement, не copy)

1. **MIT / ISC / BSD / Apache-2.0** — можно брать идеи/паттерны и писать собственный код. Сохранять copyright notice и (для Apache) `NOTICE` при прямом заимствовании фрагментов.
2. **Apache-2.0** — есть явный patent grant; при reimplement паттернов патентные риски минимальны, но атрибуция обязательна.
3. **AGPL-3.0 (khoj)** — НЕ включать ни код, ни значимые заимствования в закрытый бинарник. Только абстрактные архитектурные идеи, реализованные с нуля.
4. **BUSL-1.1 (everywhere)** — НЕ копировать код. Паттерны UI/архитектуры можно reimplement, но избегать структурного/побуквенного сходства (риск трактовки как Competing Use).
5. **Custom non-commercial (isair-jarvis)** — исключить из источников для коммерческого продукта; при необходимости запросить коммерческую лицензию у автора.
6. **PolyForm Shield (autogpt_platform/)** — папку не использовать; брать только агента вне платформы (MIT).

---

*Аудит read-only: donor-проекты не изменялись. Запись только в `E:\jarvis-project\audit_license_matrix.md`.*
