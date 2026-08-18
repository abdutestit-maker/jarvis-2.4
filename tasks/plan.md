# Sprint 10 — Real-World Computer Operator

## Objective

Extend the existing Capability Engine into a verified Windows operator that can
resolve trusted software, install it, inspect an unknown application through
semantic UI Automation, derive desired state from references, apply only the
state delta, observe and repair the result, and persist reusable application
knowledge. No frontend work and no additional LLM models.

## Assumptions accepted by the user specification

1. Windows 11 is the target runtime.
2. Network acquisition is permitted for the explicitly requested safe live test.
3. Notepad++ is the default live-test candidate if it is not already installed;
   the resolver may select another official, free, removable application only if
   Notepad++ cannot provide a semantic UIA verification path.
4. The reference fixture may be text for the live mission; video support is
   independently proven with a local fixture and real ffmpeg extraction.
5. Existing Sprint 1–9, Voice Hardening, and Voice Runtime Hotfix state is the
   baseline and must remain intact.

## Architecture

```text
CapabilityEngine
  └─ OperatorMission
      ├─ ReferenceInterpreter / VideoReferenceProvider
      ├─ SoftwareResolver / InstallerEngine
      ├─ WindowsCapabilityLayer
      │   ├─ Native / COM / CLI / config / registry
      │   ├─ UIAutomationProvider (semantic UIA)
      │   └─ VisionFallbackProvider
      ├─ BrowserAutomationProvider (Playwright DOM)
      ├─ AppExplorer / AppKnowledgeStore
      ├─ ForegroundSession
      └─ Observe → DesiredStateDiff → targeted repair → learn
```

Raw coordinates are absent from the primary provider contracts and remain a
last-resort capability outside the verified live path.

## Contracts

- Providers return `ProviderResult(ok, value, error, provider)` consistently.
- UI selectors use automation id, control type, accessible name, semantic role,
  and hierarchy; no stored coordinates.
- Installer completion requires executable/version/process/window observation.
- Mission completion requires desired-state verification, not a successful tool
  return or installer exit code.
- AppKnowledge and CapabilityEpisode persistence exclude secret-shaped fields.

## Commands

```powershell
python -m pytest -o addopts='' -q
python -m compileall -q core config scripts
git diff --check
python scripts/sprint10_live_demo.py
```

Frontend and Tauri commands are not run unless those trees change; Sprint 10 is
backend-only by explicit requirement.

## Testing strategy

- TDD for each vertical slice with focused `tests/test_sprint10_*.py` runs.
- Real Playwright DOM run against a local HTML fixture.
- Real Windows UIA run against the selected application.
- Real installer pipeline with official-source resolution and independent
  post-install verification.
- Second run proves AppKnowledge/CapabilityEpisode reuse with fewer discovery
  operations.
- Full pytest/compileall/diff checks close the sprint.

## Safety boundaries

- Always: HTTPS/trusted source validation, architecture/type checks, checkpoints,
  secret redaction, observe-after-write, restore foreground.
- Confirm: high/critical risk and user-required credentials/UAC.
- Never: random download sites, password-store access, secret persistence,
  system-file mutation, installer-exit-only completion, coordinate-first GUI.

## Success criteria

1. Real semantic UI tree discovery and control operations succeed on Windows.
2. DOM-first browser provider runs with Playwright.
3. Trusted resolver and installer independently prove installed/launchable state.
4. Reference becomes desired state; only the current/desired delta is applied.
5. Failed settings trigger targeted repair only.
6. AppKnowledge and CapabilityEpisode are persisted only after verified success.
7. A safe real application completes install → launch → inspect → configure →
   observe → verify → learn.
8. A second run reuses knowledge and records fewer discovery steps.
9. Voice hotfix smoke and all baseline regressions remain green.

