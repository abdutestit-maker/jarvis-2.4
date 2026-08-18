# Voice/TTS Hardening verification

## Baseline

- Targeted voice/WS: **25 passed, 0 failed**.
- Full suite: **177 passed, 0 failed, 2 skipped**; exit status `0`.
- Two pre-existing `websockets` deprecation warnings.

## Modified build

- Targeted voice/WS/agent/Sprint 9: **99 passed, 0 failed**.
- Full suite: **211 passed, 0 failed, 2 skipped**; 213 collected; exit `0`.
- `python -m compileall -q core config tests`: exit `0`.
- `git diff --check` for Voice Hardening paths: exit `0`.
- Frontend source files were not changed, so no frontend build was required.

## Real Piper smoke

Command:

```powershell
python scripts\voice_hardening_smoke.py
```

Result: exit `0`.

- Provider: `piper`, local `true`.
- Voice: `ru_RU-dmitri-medium`, language `ru`, fallback `none`.
- Sample rate: 22050 Hz, mono.
- Cold synthesis: 2343.872 ms.
- Warm mean: 2948.106 ms.
- `Error 455`: `speech=None`.
- Recovered provider failure: `speech=None`.
- Queue interrupt/stop behavior: automated test passed.

Generated samples:

- `artifacts/voice_test/normal.wav`
- `artifacts/voice_test/focused.wav`
- `artifacts/voice_test/terminal_failure.wav`
- `artifacts/voice_test/smoke_report.json`
