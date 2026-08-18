# Voice Runtime Hotfix — Verification

Date: 2026-08-17  
Workspace: `E:\jarvis-project`

## Defect reproduced from the recording

Input video:
`C:\Users\WwW\Videos\NVIDIA\Desktop\Desktop 2026.08.17 - 15.10.50.02.mp4`

Extracted audio:
`E:\jarvis-project\artifacts\voice_bug_video\audio.wav`

The recording contains tonal/digital output instead of intelligible Russian
speech. The model files are intact:

- `ru_RU-dmitri-medium.onnx` MD5:
  `589ccc91745a1e2353508ff62c5941b7`
- `ru_RU-dmitri-medium.onnx` SHA-256:
  `f073356ebc4bd0f80c5af58df2953a5988bd5bdab1eb38635ce960b071fbefcb`
- `ru_RU-dmitri-medium.onnx.json` MD5:
  `4eaf0d090190ecb8d958d40c76fd85e8`

## Root cause

JARVIS correctly encoded Russian text as UTF-8 bytes. Python Piper 1.3.0 read
redirected stdin using the active Windows code page when
`PYTHONIOENCODING`/`PYTHONUTF8` were absent. The resulting mojibake was then
synthesized successfully, so the old structural WAV tests could not detect the
semantic audio failure.

## Baseline command and literal result

Command:

```powershell
$env:PYTHONIOENCODING='utf-8'
python E:\jarvis-project\artifacts\voice_runtime_hotfix\baseline_encoding_probe.py
```

Input:

```text
Сэр, я вас понял. Это тестовый ответ Джарвиса.
```

Literal result:

```json
{
  "success": false,
  "input": "Сэр, я вас понял. Это тестовый ответ Джарвиса.",
  "runtime": "C:\\Users\\WwW\\AppData\\Local\\hermes\\hermes-agent\\venv\\Scripts\\piper.exe",
  "output": "E:\\jarvis-project\\artifacts\\voice_runtime_hotfix\\baseline_probe.wav",
  "process_exit": 0,
  "duration_seconds": 13.189,
  "error": "acoustic_smoke_failed"
}
```

Acoustic verification exit: `4`.

## Modified command and literal result

Command:

```powershell
$env:PYTHONIOENCODING='utf-8'
python E:\jarvis-project\scripts\voice_runtime_smoke.py E:\jarvis-project\artifacts\voice_runtime_hotfix\final_smoke.wav
```

The same input was used. Literal result:

```json
{
  "success": true,
  "input": "Сэр, я вас понял. Это тестовый ответ Джарвиса.",
  "runtime": "E:\\jarvis-project\\data\\runtime\\piper\\piper.exe",
  "expected_runtime": "E:\\jarvis-project\\data\\runtime\\piper\\piper.exe",
  "output": "E:\\jarvis-project\\artifacts\\voice_runtime_hotfix\\final_smoke.wav",
  "channels": 1,
  "sample_rate": 22050,
  "sample_width": 2,
  "frames": 70260,
  "duration_seconds": 3.186,
  "error": null
}
```

Modified verification exit: `0`.

The code-level UTF-8 fix was also exercised with the original Python Piper
1.3.0 binary selected explicitly. It generated a 2.821-second WAV and exited
with `0`, proving that the environment fix works independently of the pinned
runtime.

## Implementation

- `PiperTTS._resolve_binary`: explicit configured executable first, then the
  project-pinned runtime, then system locations/PATH.
- `PiperTTS.synthesize_to_file`: child environment always contains
  `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1`; stdin has a terminating newline.
- Added two regression tests: project-runtime priority and forced UTF-8 stdin.
- Added an offline acoustic smoke test with WAV format and duration gates.

## Test commands and results

```powershell
python -m py_compile core/voice/tts.py scripts/voice_runtime_smoke.py
```

Exit: `0`.

```powershell
python -m pytest tests/test_voice_hardening.py -q
```

Result: `36 passed`; exit `0`.

```powershell
python -m pytest -o addopts='' -q
```

Literal summary:

```text
213 passed, 2 skipped, 2 warnings in 69.12s (0:01:09)
```

Exit: `0`.

## Artifact roles

- Modified implementation:
  `E:\jarvis-project\core\voice\tts.py`
- Validated runtime:
  `E:\jarvis-project\data\runtime\piper\piper.exe`
- Patch:
  `E:\jarvis-project\artifacts\voice_runtime_hotfix\voice_runtime_hotfix.patch`
- Runtime checksum manifest:
  `E:\jarvis-project\artifacts\voice_runtime_hotfix\runtime_manifest.sha256`
- Verification audio:
  `E:\jarvis-project\artifacts\voice_runtime_hotfix\final_smoke.wav`
- Rollback:
  `E:\jarvis-project\scripts\rollback_voice_runtime_hotfix.ps1`

Patch reverse-check exit: `0`. Rollback was executed once, restored both
original hashes, removed the pinned runtime and smoke script, and the patch was
then reapplied. Final smoke and full tests were repeated after reapplication.
