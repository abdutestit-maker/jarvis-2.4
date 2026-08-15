# NIGHT LOG — P1 continuation (autonomous)

## 2026-08-15 05:0x — Q01+Q02 реализация
- Переписан `core/capabilities.py`: `CapabilityRegistry.retrieve` = гибридный
  keyword(0.4) + embedding(0.6) скоринг поверх эмбеддера проекта (all-MiniLM-L6-v2,
  ChromaDB). Embedding теперь и для web-тулз (локальный, без сети). Удалён
  неиспользуемый импорт `replace`.
- `CapabilityRegistry` авто-покрывает ВСЕ `Tool` из `ToolRegistry` (единый источник
  truth, Q02); ручной `_CAP_ANNOTATIONS` несёт только качественные поля
  (теги/примеры/риск/фолбэки), НЕ дублирует схему. `describe_tools_for_model`
  берёт схему аргументов из `ToolRegistry`.
- retrieval-smoke (офлайн): «поставь будильник»→`add_reminder`, «открой телеграм»→
  `open_app`, «какая погода»→`weather`, «напомни»→`add_reminder`, «выключи звук»→
  `volume`. `missing caps: []` (14/14 инструментов покрыты).

## 2026-08-15 05:xx — P1§1.4 proxy-фикс
- `test_p1_from_settings_proxy_mode` падал (`Settings.proxy` отсутствует) —
  предсуществующий баг (stash-доказано: падает на оригинале). `remote_api.from_settings`
  уже умел proxy-режим, но `Settings` не предоставлял блок `proxy`.
- Добавлен `ProxyConfig` + поле `proxy` в `Settings` + блок в `settings.example.json`.

## 2026-08-15 05:30 — Верификация
- FULL SUITE: **19 passed, EXIT=0** (`docs/night/tests_after_all_fixes.txt`).
- `config/settings.py` PARSE OK; `Settings().proxy.enabled=False`, `endpoint=''`.
- `class ProxyConfig` в settings.py — ровно 1 (дубль от sibling удалён).

## Sibling concurrency
- Удалён дубликат `ProxyConfig` от `20260815_035248_53bc98`.
- Никаких `skip`/удаления ассертов ради зелени не применялось.
