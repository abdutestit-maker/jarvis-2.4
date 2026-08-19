# J.A.R.V.I.S. — локальный исполнительный слой

J.A.R.V.I.S. — локальный Windows-ассистент с голосом, памятью, Shadow Engine,
Capability Engine, Brain Fabric и доказанным циклом `execute → observe → verify`.
Sprint 16 добавляет Executive Mind: он хранит не поток разговоров, а цели,
обязательства, актуальное состояние мира и проверенные способы действия.

## Быстрый запуск

```powershell
python -m core.ws_server
```

Для локального режима используется `config/settings.json` и один GGUF
`Qwen3-4B-Instruct-2507-Q5_K_M` из `data/models`. Все логические роли (fast,
analyst, coder, architect и research) ссылаются на этот же физический файл:
веса не дублируются и cloud API не вызывается по умолчанию. Параметр
`warmup_local_on_start` прогревает FAST-тир во время
старта процесса, поэтому первый пользовательский запрос не оплачивает
загрузку модели. В поставляемом offline-конфиге `auto_download_models=false`:
установщик уже содержит один 4B GGUF и не тянет тяжёлую модель на машину
пользователя. Если администратор явно включает загрузку, менеджер выбирает
профиль по RAM/VRAM, скачивает только из pinned `config/models_manifest.json`,
докачивает через `.part` и принимает файл только после SHA-256 проверки.
Диагностика доступна через `Orchestrator.runtime_diagnostics()` и WS-событие
`runtime_status` (`starting → loading_model → ready`); frontend больше не
показывает READY до фактического подключения.
Новые модели не нужны.

Провенанс текущего GGUF: [Unsloth Qwen3-4B-Instruct-2507-GGUF](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF).
Манифест закрепляет официальный HTTPS-источник и SHA-256 для чистой установки;
локально уже существующий файл не заменяется автоматически.

### Backend + frontend

```powershell
# backend
python -m core.ws_server

# frontend (отдельное окно)
cd jarvis
npm install
npm run tauri dev
```

Для проверки локального контура без сети:

```powershell
python scripts/_live_probe.py --dry-run
python scripts/wave0_verification.py
# реальные локальные проверки инструментов и модели (не fixture)
python scripts/quality_probe.py --real
```

`_live_probe.py --dry-run` — только регрессионная fixture. Для доказательства
реального поведения используйте `quality_probe.py`: он проверяет часы,
системный статус, media Risk Gate, неизвестную команду, relevance памяти и
после `--real` прогревает локальный GGUF с runtime/offload diagnostics.

### Портативный установщик без cloud API

Перед `npm run tauri:build` один раз подготовьте локальный runtime:

```powershell
python scripts/package_local_runtime.py
cd jarvis
npm run tauri:build
```

Скрипт кладёт в Tauri resources один 4B GGUF, официальный `llama-server` и
его Vulkan DLL, а также компактное дерево `core/config`. В сгенерированный
`settings.json` записаны `offline_mode=true`, `allow_cloud=false` и локальный
loopback runtime; API-ключи туда не копируются. Для слабых машин можно добавить
имеющийся 1.7B fallback флагом `--include-fallback`. Размер текущего 4B
пакета — около 2.99 GB; Git его не отслеживает.

На Windows с GGUF больше 2 GB штатный NSIS может упереться в 32-битный mmap.
Финальный установщик поэтому собирается отдельным 64-битным 7-Zip SFX-контейнером:

```powershell
python scripts/build_portable_installer.py
```

Он кладёт `jarvis-frontend.exe`, `runtime/jarvis-backend.exe`, Vulkan/llama-server,
русский Piper и GGUF в `%LOCALAPPDATA%\JARVIS`, создаёт ярлык и запускает GUI.
Backend собран PyInstaller `--noconsole`, а Tauri запускает его с
`CREATE_NO_WINDOW`: при старте приложения консольные окна не появляются.
Проверка архива: `7z t jarvis/src-tauri/target/release/bundle/nsis/J.A.R.V.I.S._3.0.0_x64-setup.exe`.

## Executive Mind

Пакет `core/executive/` предоставляет:

- `GoalGraph` — цели, зависимости, blockers, verified resume;
- `CommitmentEngine` — идеи, намерения, обещания и дедлайны;
- `UnifiedWorldState` — факты с источником, confidence, сроком и diff;
- `CommandOS` — канонические примитивы `OBSERVE → FIND → PLAN → EXECUTE → VERIFY`;
- `CapabilityGraph` — граф поверх существующих tools, без второго реестра действий;
- `DemonstrationLearner` — обучение семантическому workflow без координат;
- `ShadowRehearsal` — локальная репетиция плана без побочных эффектов;
- `TemporalMemory` и `SleepMode` — актуальность и bounded ночная консолидация;
- `SemanticUndo`, `AskOncePolicy`, `CounterfactualEngine`, `PersonalEvalLab`.
- `LocalPresenceMesh` — только подготовка явного handoff между доверенными
  локальными устройствами; сеть и секреты самопроизвольно не используются.

## Universal Intelligence Layer

`core/intelligence/` добавляет быстрый `UniversalIntake`, единый `TaskContract`,
`EvidenceRecord`, численные latency budgets, `TutorEngine`, локальное обучение и
`SkillManifest` с приоритетом Native API → CLI/PowerShell → UIA/DOM → Vision.
Fast path остаётся детерминированным; тяжёлые Intake/Research/Tutor-задачи идут
по deliberate или background path.

Состояние сохраняется атомарно в `data/executive/`. Фильтр памяти удаляет
пароли, токены, ключи и сырые traceback до записи.

## Быстрые локальные команды

- `Который час?` → `current_time` (локальные часы, без сети);
- `Поставь музыку ...` → `play_music`; reminder-путь не используется;
- `Открой блокнот` → существующий `open_app` fast path;
- `Продолжи с последнего проверенного шага` → Goal Graph resume.

Сетевой поиск остаётся явным и сообщает об отсутствии источника, а не выдаёт
непроверенный ответ. Опасные изменения по-прежнему проходят Risk Gate.

## Проверка

```powershell
python -m pytest -o addopts="" -rA
```

Верификационный отчёт Sprint 16: `docs/EXECUTIVE_MIND_VERIFICATION.md`.
Phase 0 evidence: `artifacts/verification/phase0/`.
