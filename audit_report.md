# Computer-Use & Browser Donor Audit (E:\jarvis-donors)

Read-only static analysis. Protected user dirs EVA/jarvis/jarvis-py NOT touched.

## Per-Donor Mechanism Findings

### everywhere (C#/.NET Avalonia desktop assistant) — LICENSE: BSL 1.1 (non-competing use only)
- Mechanism: OS-native screen capture + visual-element tree + accessibility-DOM-to-markdown.
  - File: `everywhere/src/Everywhere.{Windows,Linux,Mac}/Interop/VisualElementContext.Screenshot.cs` — per-OS screenshot (Windows UIA/Win32, X11, macOS).
  - File: `everywhere/src/Everywhere.Core/Web/WebAccessibilityMarkdownConverter.cs` — converts CDP accessibility tree → markdown for the LLM ("screen understanding" via AX tree, not pixels).
  - File: `everywhere/src/Everywhere.Windows/Interop/AutomtionVisualElementImpl.cs` — Windows UI Automation element tree (active window / application detection + control invocation).
  - File: `everywhere/src/Everywhere.Core/Views/ScreenSelection/ScreenSelectionWindow.cs` — overlay + screen/element selection (region picking).
- Problem solved: granular, pixel+DPI-correct desktop understanding and element-level control cross-platform.
- License: **RED** for closed commercial use (BSL 1.1, "Competing Use" prohibited 4 yrs; would compete with a desktop Jarvis). Cannot COPY/ADAPT into a commercial product.
- Recommendation: **REIMPLEMENT** only the ideas (AX→markdown converter, UIA element tree) after the change-date, or design around it. Do NOT copy code.

### ui-tars-desktop (ByteDance, Tars GUI agent) — LICENSE: Apache-2.0 (SPDX in files)
- Mechanism A (vision grounding / box parsing): `packages/ui-tars/action-parser/src/actionParser.ts` — parses `click(start_box='(x1,y1,x2,y2)')` model output into scaled screen coordinates; handles V1.5 smart-resize, multiple prompt formats.
- Mechanism B (desktop mouse/keyboard): `packages/ui-tars/operators/nut-js/src/index.ts` + `apps/ui-tars/src/main/agent/operator.ts` — `@computer-use/nut-js` operator: `screen.grab()` screenshot (with DPI/scale handling), mouse move/click/drag, keyboard, scroll, `parseBoxToScreenCoords`. Electron `desktopCapturer` for screenshots.
- Mechanism C (browser automation): `packages/ui-tars/operators/browser-operator/src/browser-operator.ts` — Playwright page screenshot, clickable-element highlighting, action execution.
- Problem solved: end-to-end VLM "box coordinate" computer-use loop (screenshot → model → coords → input) for desktop + browser.
- License: **GREEN** (Apache-2.0). 
- Recommendation: **ADAPT** the action-parser + nut-js operator as the desktop control backbone; the coordinate-box protocol is the cleanest reference.

### openai-cua-sample-app (OpenAI) — LICENSE: MIT
- Mechanism: Playwright browser control + screenshot capture + replay schema + responses-loop agent.
  - File: `packages/browser-runtime/src/index.ts` — `launchBrowserSession`, `captureScreenshot` (Playwright `page.screenshot`), `readState` (url/title).
  - File: `packages/runner-core/src/responses-loop.ts`, `scenario-runtime.ts` — agent loop that drives CUA model responses; `executor-registry.ts` maps scenarios to executors.
  - File: `packages/replay-schema` + `apps/demo-web/app/ui/operator-console/ScreenshotPane.tsx` — human-verifiable screenshot replay/verification UI.
- Problem solved: reference harness for OpenAI Computer-Use (CUA) responses API; screenshot-based action verification through replay.
- License: **GREEN** (MIT).
- Recommendation: **ADAPT** as the action-verification/replay layer (the "what happened after click" evidence trail) and the responses-loop pattern; COPY small helpers freely.

### browser-use (Python browser agent) — LICENSE: MIT
- Mechanism A (accessibility/DOM grounding): `browser_use/dom/serializer/clickable_elements.py` (`ClickableElementDetector.is_interactive`) + `browser_use/dom/views.py` (XPath, selector_index, bounding boxes, coordinates). Detects interactive elements via JS click listeners, ARIA roles, form controls.
- Mechanism B (DOM snapshot + screenshot): `browser_use/browser/dom` serializers, `browser_use/agent/service.py` (screenshot resize for LLM, `llm_screenshot_size`), watchdogs/`screenshot_watchdog.py`.
- Mechanism C (high-level browser actions): `browser_use/controller/`, `browser_use/actor/` (element/mouse/page) — semantic click by index/selector rather than raw coords.
- Problem solved: robust browser understanding via interactive-element detection + set-of-marks-style indexing; screenshot + AX hybrid.
- License: **GREEN** (MIT).
- Recommendation: **ADAPT** `ClickableElementDetector` + DOM serializer for browser grounding; COPY the interactive-detection heuristics.

### openjarvis (voice AI desktop assistant) — LICENSE: MIT
- Mechanism: voice pipeline (mic → wake word → ASR → Redis bus → LLM → Tool Executor) + MCP/local tool support.
  - File: `openjarvis/openjarvis/tools/executor.py` — dispatches LLM tool calls to local Python tools + MCP servers.
  - File: `openjarvis/openjarvis/audio/capture.py` — microphone capture.
- Problem solved: always-on voice control framework; extensibility via MCP. NO native screen-understanding or mouse/keyboard computer-use in this snapshot (tool-driven, not pixel/coordinate CUA).
- License: **GREEN** (MIT).
- Recommendation: **REIMPLEMENT/ADAPT** only the voice→tool architecture and MCP tool-executor pattern; not a computer-use donor per se.

### isair-jarvis (desktop assistant, non-commercial) — LICENSE: Jarvis AI Assistant License (NON-COMMERCIAL)
- Mechanism A (OCR screen understanding): `src/jarvis/tools/builtin/screenshot.py` — `screencapture -i` region capture → pytesseract OCR → text returned to model. (macOS `screencapture`; Windows path would need substitution.)
- Mechanism B (tool selection): `src/jarvis/tools/selection.py` — ALL/KEYWORD/EMBEDDING/LLM strategies for picking relevant tools.
- Mechanism C (MCP): `src/jarvis/tools/external/mcp_runtime.py`, `src/desktop_app/mcp_catalogue.py` — MCP server catalogue (stateful browser servers noted as limited).
- Problem solved: lightweight OCR-as-screen-understanding + strong tool-routing; useful for "what is on screen" via text.
- License: **RED** for closed commercial use (explicit non-commercial clause; commercial needs separate license).
- Recommendation: **REIMPLEMENT** the OCR-screenshot + embedding tool-selection ideas; do NOT copy code/license.

### agent-zero (Python multi-agent) — LICENSE: MIT
- Mechanism A (remote computer-use): `plugins/_a0_connector/tools/computer_use_remote.py` — drives a connected desktop CLI via WebSocket: `capture`, `list_windows`, `get_window_state`, `ax_snapshot`/`ax_action` (accessibility tree), `uia_snapshot`/`uia_action` (Windows UI Automation), `move/click/scroll/key/type`. Built-in **action verification**: `_AUTO_CAPTURE_ACTIONS` + settle delays + `CAPTURE_VERIFICATION_NOTE` re-attaches a fresh screenshot after every action so the model must verify ("inspect the attached screenshot").
- Mechanism B (browser): `plugins/_browser/tools/browser.py` — Playwright-backed browser with `ref`/selector actions + screenshot history (quality 62, denylist).
- Mechanism C (multi-agent): `api/`, `plugins/` architecture; parallel/remote tool execution.
- Problem solved: production-grade computer-use WITH explicit post-action screen verification (the strongest "what happened after click" handling in the pool) + AX/UIA dual grounding + active-window detection (`list_windows`/`get_window_state`).
- License: **GREEN** (MIT).
- Recommendation: **ADAPT** `computer_use_remote.py` verification pattern (auto-capture + settle + forced visual check) as the action-verification reference; COPY the AX/UIA action vocabulary.

### open-interpreter (fork = OpenAI Codex CLI) — LICENSE: Apache-2.0 (+ NOTICE)
- Mechanism: in THIS snapshot it is the Codex CLI fork (Rust `codex-rs` + `codex-cli`), NOT the classic `interpreter.computer` pixel-CUA. Per README "Computer Use" = drives web apps via `agent-browser` (Vercel) or native apps via `trycua/cua` (external deps). Exec/sandbox + ACP + skills/hooks/permissions/MCP.
  - File: `codex-rs/...` (Rust) — approval/`ReviewStatus::Approved` gating, desktop product client id; sandboxing on macOS/Linux/Windows.
- Problem solved: shell/code exec + external CUA orchestration + permission approvals; no in-repo screen-understanding/mouse module.
- License: **GREEN** (Apache-2.0 + NOTICE) for the code, BUT the actual CUA capability is delegated to 3rd-party `cua`/`agent-browser` (their own licenses apply).
- Recommendation: **ADAPT** the approval/sandbox/permission shell + MCP integration; treat computer-use as external (`trycua/cua`) dependency, not from this repo.

### browsergym (ServiceNow research bench) — LICENSE: Apache-2.0
- Mechanism A (set-of-marks grounding): `browsergym/core/src/browsergym/core/observation.py` — `mark_elements` injects `bid` attributes + dynamic value/checked; `extract_screenshot` via CDP at higher res (`bgym_scale_factor`) for VLM; `extract_dom_snapshot` via CDP DOM. This is the canonical "set-of-marks" browser grounding.
- Mechanism B (action space): `browsergym/core/src/browsergym/core/action/highlevel.py` — `click`, `dblclick`, `mouse_click`, `keyboard_insert_text`, `bid`/coord/element variants; `action/parsers.py` parses model output.
- Mechanism C (agent + obs): `demo_agent/agent.py` (`image_to_jpg_base64_url`, obs preprocessor merging chat + screenshot) + `experiments/src/browsergym/experiments/agent.py`.
- Problem solved: rigorous, benchmark-grade browser observation (SoM) + action parsing; ideal testbed for "what is on screen" + "did the click work".
- License: **GREEN** (Apache-2.0).
- Recommendation: **COPY/ADAPT** the `mark_elements` + CDP screenshot/DOM observation pipeline as the browser screen-understanding reference; it is the cleanest SoM implementation.

### webarena (benchmark) — LICENSE: Apache-2.0
- Mechanism A (observation): `browser_env/processors.py` — `TextObervationProcessor` (HTML/accessibility-tree → text) + `ImageObservationProcessor` (Playwright `page.screenshot` → numpy). `ObservationHandler` toggles text vs image.
- Mechanism B (action space): `browser_env/actions.py` — Playwright-backed action set (`PLAYWRIGHT_ACTIONS`/`LOCATORS`), `is_in_viewport` threshold check, ASCII/Unicode typing, special-key mapping; `envs.py` `ScriptBrowserEnv` with `observation_type` html/accessibility_tree/image.
- Mechanism C (eval): `evaluation_harness/evaluators.py` — functional success verification of actions.
- Problem solved: reproducible browser task environment with structured observations + deterministic evaluators (strong "did it work" signal).
- License: **GREEN** (Apache-2.0).
- Recommendation: **ADAPT** the observation processor + evaluator pattern for action verification; COPY `actions.py` key-mapping/coordinate logic.

## Comparative Matrix (0=absent … 5=exceptional)

| DONOR | agent_loop | tools | computer_use | browser | memory | research | multi_agent | voice | ui | long_tasks | mcp | license | value(0-5) | justification |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| everywhere | 2 | 2 | 4 | 1 | 3 | 1 | 1 | 2 | 4 | 2 | 1 | BSL1.1(RED) | 2 | Strong native desktop CUA/AX but BSL non-compete blocks commercial reuse |
| ui-tars-desktop | 4 | 3 | 5 | 4 | 1 | 2 | 1 | 1 | 4 | 3 | 2 | Apache2(GREEN) | 5 | Cleanest box-coord VLM computer-use loop for desktop+browser, Apache |
| openai-cua-sample-app | 4 | 2 | 3 | 4 | 1 | 1 | 1 | 1 | 3 | 2 | 1 | MIT(GREEN) | 4 | Reference CUA replay/verification harness + responses-loop, MIT |
| browser-use | 4 | 4 | 1 | 5 | 2 | 2 | 1 | 1 | 3 | 3 | 2 | MIT(GREEN) | 4 | Best browser-only grounding (interactive detection + SoM), MIT |
| openjarvis | 3 | 4 | 0 | 0 | 3 | 0 | 1 | 5 | 3 | 2 | 4 | MIT(GREEN) | 3 | Voice+MCP tool framework, no native screen understanding |
| isair-jarvis | 3 | 4 | 1 | 0 | 4 | 1 | 1 | 4 | 4 | 3 | 4 | NC(RED) | 3 | OCR screenshot + embedding tool-selection, but non-commercial license |
| agent-zero | 4 | 4 | 4 | 4 | 3 | 2 | 4 | 1 | 3 | 4 | 3 | MIT(GREEN) | 5 | Strongest post-action verification (auto-capture+settle+AX/UIA), MIT |
| open-interpreter | 4 | 4 | 2 | 2 | 1 | 1 | 1 | 1 | 3 | 3 | 4 | Apache2(GREEN) | 3 | Codex-CLI fork: shell/MCP/approval; CUA delegated to cua/agent-browser |
| browsergym | 3 | 2 | 0 | 5 | 0 | 5 | 1 | 0 | 2 | 2 | 0 | Apache2(GREEN) | 4 | Canonical set-of-marks browser observation + action parsing, Apache |
| webarena | 3 | 2 | 0 | 4 | 0 | 5 | 1 | 0 | 2 | 2 | 0 | Apache2(GREEN) | 3 | Reproducible browser env + evaluators for action verification, Apache |

## Conclusion — Best stack for screen understanding + action verification

**Screen understanding (what is on screen):**
- Browser: **browsergym** `observation.py` (set-of-marks via `bid` injection + CDP hi-res screenshot + DOM snapshot) is the exceptional reference; pair with **browser-use** `ClickableElementDetector` for production interactive-element scoring.
- Desktop: **ui-tars-desktop** `action-parser` + nut-js operator gives the cleanest VLM box-coordinate model; **agent-zero** `computer_use_remote` adds AX (accessibility tree) + UIA (Windows UI Automation) grounding and active-window detection as a richer, non-vision fallback.

**Action verification (what happened after the click):**
- **agent-zero** `computer_use_remote.py` is the standout: every mutating action triggers an automatic fresh `capture` with per-action settle delays + a forced `CAPTURE_VERIFICATION_NOTE`, so the model must re-read the screen. 
- **openai-cua-sample-app** adds a human-verifiable screenshot **replay** UI (`ScreenshotPane.tsx` + `replay-schema`).
- **webarena** `evaluation_harness/evaluators.py` provides deterministic functional success checks.

**Recommended composite:** ADAPT ui-tars-desktop (desktop CUA loop) + browsergym (browser SoM observation) + agent-zero (post-action auto-capture verification + AX/UIA) + openai-cua-sample-app (replay trail). Avoid everywhere (BSL) and isair-jarvis (non-commercial) for any closed commercial build; treat open-interpreter's CUA as an external `cua` dependency.
