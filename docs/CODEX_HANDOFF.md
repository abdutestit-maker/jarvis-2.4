# CODEX HANDOFF — J.A.R.V.I.S. модельный слой + продукт «для всех»

> От: агент Postman. Кому: Codex.
> Контекст и обоснование — в `docs/JARVIS_REBUILD_PLAN.md`. Читай его первым.
> Цель владельца: (1) Джарвис быстрый и не тупой; (2) запускается у ЛЮБОГО
> пользователя; (3) **без платных API-ключей — только локальные модели**;
> (4) витринные сценарии: презентация, установка приложения «по видео»,
> мгновенный анализ.

---

## ЧТО Я УЖЕ СДЕЛАЛ (не переделывай, продолжай от этого)

1. `config/settings.example.json` + `config/settings.py` — починил битые пути:
   - Shadow `code_model_path` → `data/models/Qwen3-1.7B-Q6_K.gguf` (был несуществующий `qwen3-1.7b-instruct-q4_k_m.gguf`).
   - `LocalModelConfig.gguf_path` дефолт → `qwen3-4b-instruct-q5_k_m.gguf` (был `...q4_k_m.gguf`, файла нет).
2. `core/llm/hardware_profile.py` — НОВЫЙ модуль (никто ещё не импортирует, тесты не трогает). Даёт `detect_hardware()` и `recommend_profile(hw, models_dir)` → `ModelProfile{core_model, n_gpu_layers, n_ctx, n_batch, draft_model, download_required}`. Универсальная лестница 0.6B→14B. Проверен на спектре машин.

**Инвариант на все задачи ниже:** после КАЖДОГО изменения гоняй
`python -m pytest -o addopts="" -rA`. Система зрелая (Sprint 16), много тестов.
Не удаляй «мёртвый» код, пока тесты это не подтвердят зелёными.

---

## ЗАДАЧА 0 (СНАЧАЛА) — почини живой `config/settings.json`

Я НЕ могу его читать/править (он в `.gitignore`, заблокирован для ИИ). Именно
в нём, судя по всему, живёт «связка двух 1.7B, медленно и тупо». Сделай:

1. Открой `config/settings.json`. Убедись, что:
   - `local_model.gguf_path` = существующий файл (`data/models/qwen3-4b-instruct-q5_k_m.gguf`), `n_gpu_layers` под железо (или `-1` при наличии GPU).
   - `shadow.code_model_path` = `data/models/Qwen3-1.7B-Q6_K.gguf` (или `shadow.enabled=false`, если фон не нужен).
   - НЕТ конфигурации, где на каждый запрос гоняются ДВЕ модели (fast + отдельная reasoning). Если есть — убери reasoning из горячего пути.
   - `model_tiers.analyst/coder/architect` НЕ указывают на модель слабее FAST. Для no-API продукта проще: `offline_mode=true`, все тиры → локальный core.
2. Приёмка: `который час` / `привет` отвечают ≤2–3 с; в логах один локальный бэкенд, не два.

---

## ЗАДАЧА 1 — Model auto-download (без него «у каждого» не работает)

Файлы: `core/utils/model_manager.py` (есть — расширить), новый `config/models_manifest.json`.

- Манифест: для каждого `key` из лестницы (`qwen3-0.6b`, `qwen3-1.7b`, `qwen3-4b`, `qwen3-8b`, `qwen3-14b`) — прямой URL GGUF (Hugging Face), размер, SHA256.
- `model_manager.ensure_model(profile)`: если `profile.download_required` — качает `profile.core_model` (и `draft_model`) в `data/models/` с прогрессом и проверкой SHA. Идемпотентно, докачка с резюме.
- Приёмка: на чистой машине без GGUF первый старт сам скачивает нужную модель под железо; повторный старт — мгновенно.

## ЗАДАЧА 2 — Wire `hardware_profile` в конфиг/фабрику

Файлы: `config/settings.py` (или новый `core/llm/bootstrap.py`), `core/llm/factory.py`.

- При старте (когда `warmup_local_on_start`): вызвать `recommend_profile(detect_hardware(), settings.models_dir)` и, если пользователь НЕ задал значения явно, подставить `local_model.gguf_path/n_gpu_layers/n_ctx/n_batch`.
- Уважай явный выбор пользователя (не перетирай, если он сам прописал модель).
- Приёмка: на GPU-машине автоматически `n_gpu_layers=-1` и модель крупнее; на слабом CPU — 1.7B/0.6B и урезанный `n_ctx`. Логируй выбранный `ModelProfile.summary()`.

## ЗАДАЧА 3 — Speculative decoding в `LocalQwenBackend`

Файл: `core/llm/local_qwen.py`.

- Пробросить draft-модель в llama.cpp (`draft_model`, параметры `n_draft`/`draft`), когда `profile.draft_model` задан.
- Фича-флаг + graceful fallback: если сборка llama-cpp-python не поддерживает — работать без draft, не падать.
- Приёмка: замерь tok/s на 4B с draft и без на GPU-машине; draft не должен УХУДШАТЬ latency (иначе выключить по умолчанию).

## ЗАДАЧА 4 — Router + reasoning-по-требованию + streaming/ack

Файлы: `core/router/*`, `core/orchestrator.py`, `core/llm/*`.

- Роутер (правила + при желании 0.6B/1.7B) классифицирует: `command|chat|reasoning|tool`. `command` → без LLM; `reasoning` → включать `<think>` только тут.
- Убедись, что streaming токенов реально доходит до TTS/UI (в оркестраторе есть `install_stream_sink`) и instant-ack срабатывает на ВСЕХ небанальных запросах.
- Приёмка: простой вопрос — ack ≤100 мс + первый токен быстро; reasoning-режим не включается на «привет».

## ЗАДАЧА 5 — Нативный function-calling

Заменить regex `TOOL_CALL:{...}` на структурированные tool-calls Qwen3
(`core/actions/executor.py`, `core/llm/local_qwen.py`, `supports_tools`). Приёмка: инструмент вызывается стабильно без текстового маркера.

## ЗАДАЧА 6 — Витринные возможности (по приоритету владельца)

- **STT**: включить `faster-whisper` (`core/voice/stt.py` — сейчас заглушка). Модель STT — тоже через auto-download, размер по железу.
- **Artifact generation**: `python-pptx`/`python-docx` как инструменты → «сделай презентацию/документ».
- **Computer-use / браузер**: Playwright + set-of-marks (скриншот → клики по разметке) → «поставь приложение», «сделай в браузере». Тяжёлый VLM-пакет — опционально, только на способном железе.
- **Frontend transport**: довести `jarvis/` до живого WebSocket-моста к `core.ws_server`; удалить мёртвый `jarvis-ui/`.

---

## ГРАНИЦЫ И ЧЕСТНОСТЬ (обязательно соблюдать)

- **Никаких платных API по умолчанию.** Весь интеллект локальный. Удалённые тиры — опция, выключены без ключа.
- **Не обещай невозможного.** «1 ГБ ОЗУ и умеет всё» — недостижимо (см. план §3). На floor-железе Джарвис честно сообщает, что задача превышает локальные возможности, а не выдаёт мусор.
- **Не ломай зрелую систему.** Хирургия по слоям + `pytest` после каждого шага. Мёртвый код удаляй только с зелёными тестами.
- **Приоритет источников правды:** реальный код > `docs/JARVIS_REBUILD_PLAN.md` > `AUDIT_CURRENT_JARVIS.md` (устарел).
