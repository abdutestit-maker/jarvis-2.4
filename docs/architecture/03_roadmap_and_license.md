# 03 — Дорожная карта и лицензионные ограничения

> Источники: `audit_license_matrix.md` (E, AGENT E, read-only аудит 23 доноров),
> собственная ground truth. Цель: поэтапный переход сырого JARVIS →
> desktop-resident general-purpose agent как закрытый коммерческий продукт.
> Дата: 2026-08-15.

## 1. Лицензионные ограничения (КРИТИЧНО)

**Правило:** адаптируем **паттерны и механизмы, НЕ копируем исходный код**.

### 1.1 🔴 БЛОКЕРЫ (коммерческое закрытое использование кода запрещено)

| Donor | Лицензия | Суть блокера |
|-------|----------|--------------|
| **everywhere** | Business Source License 1.1 (BUSL-1.1), Licensor: Sylinko Inc. | «Competing Use» запрещён (вкл. коммерческий продукт-заменитель). Change Date = +4 г. → потом Apache-2.0. **Код копировать в закрытый продукт НЕЛЬЗЯ.** Только reimplement паттернов (UI Automation + VisualContextBuilder), без строк исходника. |
| **isair-jarvis** | **Custom non-commercial** («Jarvis AI Assistant License») | Коммерция требует отдельной лицензии у автора (baris@writeme.com). Копирование кода для коммерческого JARVIS недопустимо. |
| **khoj** | **GNU Affero GPL v3 (AGPL-3.0)** | Strong copyleft + network copyleft. Любой закрытый коммерческий продукт, включающий код khoj, обязан стать AGPL и опубликовать ВСЕ исходники. Несовместимо с закрытым JARVIS. |

### 1.2 🟡 СМЕШАННАЯ / КОНФЛИКТ

| Donor | Лицензия | Примечание |
|-------|----------|-----------|
| **autogpt** | СМЕШАННАЯ: MIT (вне `autogpt_platform/`) + PolyForm Shield 1.0.0 (внутри `autogpt_platform/`) | Брать ТОЛЬКО код вне `autogpt_platform/`. Папку платформы не трогать (non-competitive, source-available). |
| **gpt-researcher** | КОНФЛИКТ: файл `LICENSE` = Apache-2.0, но манифесты (`setup.py`/`package.json`) = MIT/ISC | Официальная лицензия = Apache-2.0 (файл авторитетнее манифеста). Уточнить у автора (assafelovic) перед релизом. |

### 1.3 🟢 REIMPLEMENT-SAFE (19 проектов)

MIT (11): agent-zero, browser-use, openai-cua-sample-app, openclaw, openhands,
openjarvis, pydantic-ai, swe-agent.
Apache-2.0 (10, вкл. gpt-researcher по файлу): agno, browsergym, camel, letta,
mem0, mirothinker, open-interpreter, swarms, ui-tars-desktop, webarena,
gpt? — *gpt-researcher фактически Apache-2.0*.

> **camel** имеет `README.ja.md` — НЕ проблема, лицензия Apache-2.0 подтверждена
> из `package.json`/`pyproject`. **EVA / jarvis / jarvis-py** в `E:\jarvis-donors\`
> — пользовательские папки, НЕ доноры (исключены из аудита).

### 1.4 Матрица (полная, 23 донора)

| # | Donor | Лицензия | Коммерция | Copy code | Reimplement |
|---|-------|----------|-----------|-----------|-------------|
| 1 | agent-zero | MIT | ✅ | ✅ | ✅ |
| 2 | agno | Apache-2.0 | ✅ | ✅ | ✅ |
| 3 | autogpt | MIT + PolyForm Shield | ⚠️ MIT-часть | ⚠️ вне platform | ⚠️ вне platform |
| 4 | browsergym | Apache-2.0 | ✅ | ✅ | ✅ |
| 5 | browser-use | MIT | ✅ | ✅ | ✅ |
| 6 | camel | Apache-2.0 | ✅ | ✅ | ✅ |
| 7 | **everywhere** | **BSL 1.1** | ❌ | ❌ | ⚠️ паттерн только |
| 8 | gpt-researcher | Apache-2.0 (конфликт манифестов) | ✅ | ✅ | ✅ |
| 9 | **isair-jarvis** | **Custom non-commercial** | ❌ | ❌ | ❌ |
| 10 | **khoj** | **AGPL-3.0** | ⚠️ copyleft | ⚠️ →AGPL | ⚠️ осторожно |
| 11 | letta | Apache-2.0 | ✅ | ✅ | ✅ |
| 12 | mem0 | Apache-2.0 | ✅ | ✅ | ✅ |
| 13 | mirothinker | Apache-2.0 | ✅ | ✅ | ✅ |
| 14 | openai-cua-sample-app | MIT | ✅ | ✅ | ✅ |
| 15 | openclaw | MIT | ✅ | ✅ | ✅ |
| 16 | openhands | MIT | ✅ | ✅ | ✅ |
| 17 | open-interpreter | Apache-2.0 | ✅ | ✅ | ✅ |
| 18 | openjarvis | MIT | ✅ | ✅ | ✅ |
| 19 | pydantic-ai | MIT | ✅ | ✅ | ✅ |
| 20 | swarms | Apache-2.0 | ✅ | ✅ | ✅ |
| 21 | swe-agent | MIT | ✅ | ✅ | ✅ |
| 22 | ui-tars-desktop | Apache-2.0 | ✅ | ✅ | ✅ |
| 23 | webarena | Apache-2.0 | ✅ | ✅ | ✅ |

### 1.5 Общие правила интеграции

1. MIT/ISC/BSD/Apache-2.0 — брать идеи/паттерны, писать свой код. Сохранять
   copyright notice и (Apache) `NOTICE` при прямом заимствовании фрагментов.
2. AGPL-3.0 (khoj) — НЕ включать ни код, ни значимые заимствования в закрытый
   бинарник. Только абстрактные архитектурные идеи с нуля.
3. BSL 1.1 (everywhere) — НЕ копировать код. Reimplement паттернов, избегать
   структурного/побуквенного сходства (риск Competing Use).
4. Custom non-commercial (isair-jarvis) — исключить; при необходимости запросить
   коммерческую лицензию.
5. PolyForm Shield (autogpt_platform/) — папку не использовать.

## 2. Дорожная карта (фазы)

### Фаза 1 — Чиним ядро (блокирующие факторы, P0)
- [ ] Убрать мёртвый async-путь `submit_goal`→`Agent.run_mission` (§7.1)
- [ ] `Agent._decide_with_model` → `routing.tier` + fallback-цепочка (§1, F §1.3)
- [ ] Объединить две копии intent/model-роутинга
- [ ] `ACKNOWLEDGING` мгновенный отклик + `confirm_mission` (подтверждение HIGH-risk end-to-end)
- [ ] Применить `wrap_untrusted` ко всем недоверенным источникам + SSRF + redact

### Фаза 2 — Tool-система (P1)
- [ ] Единый источник truth: регистрация tool → авто capability-паспорт
- [ ] Гибридный semantic retrieval (embedding поверх ChromaDB-эмбеддера)

### Фаза 3 — Computer Use (Windows)
- [ ] VLM screen understanding (ui-tars паттерн) + accessibility-tree (everywhere, reimplement)
- [ ] Win32 `SendInput` + DPI-aware координаты
- [ ] Action verification (openai-cua + наш `verifier.py`)

### Фаза 4 — Browser Automation
- [ ] Playwright + пронумерованные элементы (browser-use паттерн)
- [ ] Controller registry с `@action`

### Фаза 5 — Memory / Research
- [ ] Vector/RAG/long-term user memory (letta/mem0/khoj-паттерны, БЕЗ кода khoj)
- [ ] Deep research pipeline (gpt-researcher паттерн, Apache-2.0)

### Фаза 6 — Voice (STT)
- [ ] `STTEngine` (faster-whisper/whisper.cpp) → `submit_goal`; кнопка микрофона

### Фаза 7 — Artifacts
- [ ] Генерация презентаций/документов

### Фаза 8 — UI polish
- [ ] `createRealBackend()` (Tauri/WS-мост) + маппинг MissionStatus→UI
- [ ] proactive/background поведение (`core/proactive.py`, `task_runtime.py`)

## 3. Риски

- **BSL 1.1 (everywhere):** единственный жёсткий блокер для copy. Только reimplement.
- **AGPL-3.0 (khoj):** исключить код/заимствования из закрытого бинарника.
- **isair-jarvis:** исключить из коммерческих источников.
- **autogpt:** только вне `autogpt_platform/`.
- **gpt-researcher:** конфликт манифестов — уточнить у автора перед релизом.
- **Stale truth:** `audit_agent_runtime.md`/`audit_report.md`/`final_report.json`
  описывают доноров, НЕ текущий JARVIS — не путать.
- **Write-path drift:** субагенты иногда писали не по тому пути — проверять
  наличие файлов по абсолютному пути.
- **camel README.ja.md:** читать его, лицензия Apache-2.0 подтверждена.
- **EVA / jarvis / jarvis-py:** пользовательские папки, НЕ доноры.
- **openjarvis:** MIT, но имя «Jarvis» — возможна trademark-осторожность при
  нейминге продукта (не юридический блок, чисто брендинг).
