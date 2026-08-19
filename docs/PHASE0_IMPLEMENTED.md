# Phase 0 — runtime reality fixes

Дата: 2026-08-19. Ветка: `codex/universal-kernel`.

## Что закрыто

- `current_time` и `play_music` остаются отдельными deterministic tools;
  media-запрос не может превратиться в reminder.
- неизвестная рискованная цель получает Risk Gate до capability research;
  после подтверждения путь запускается повторно, а не маскирует mutation.
- один локальный backend создаётся через публичный FAST factory, поэтому
  Brain Fabric и legacy router делят одну модель и один cache key.
- warmup модели выполняется в daemon-потоке; WS/UI получает readiness сразу.
- `runtime_status` передаёт `starting/loading_model/ready/unavailable` и
  diagnostics (`backend`, модель, offload layers, warmup time).
- frontend использует настоящий WS connection state, exponential reconnect и
  не рисует READY при отсутствующем backend.
- ACK больше не запускает вторую inference: live mission получает canned ACK,
  а deliberate work продолжается после него.
- `hardware_profile` выбирает безопасный local tier 0.6B→14B; `ModelManager`
  использует pinned HTTPS manifest, resumable `.part` downloads, размер и
  SHA-256 перед atomic replace.
- speculative draft подключён как opt-in с graceful fallback для старых
  `llama-cpp-python` wheels; CPU runtime не притворяется CUDA.

## Доказательства

До патча на текущем дереве: `482 passed, 2 skipped, 4 failed`.
После патча: `492 passed, 2 skipped, 0 failed`.
Frontend: `5` protocol assertions, backend transport suite and `13` operator
assertions; `npm run build` и `cargo check` проходят.

Наблюдаемые исправленные регрессии:

1. high-risk unknown command теперь требует confirmation;
2. persisted software-version belief не становится ложным `stale` после
   обычного двухдневного offline restart, сохраняя строгую generic policy;
3. WS mission streaming использует тот же injectable FAST backend;
4. ACK не оплачивает загрузку/инференс модели.

## Что ещё не закрыто этой фазой

- release installer пока не содержит sidecar Python/llama/Piper и GGUF;
- реальный packaged Windows E2E, STT и Playwright live run требуют отдельного
  acceptance pass;
- текущая установленная `llama-cpp-python` сборка сообщает CPU-only, поэтому
  `n_gpu_layers=0` фиксируется честно.

## Rollback

Исполняемый откат: `artifacts/verification/phase0/rollback.ps1`.
Он восстанавливает только файлы этой фазы к baseline commit и не трогает
пользовательские модели, `config/settings.json` или другие workspace artifacts.
