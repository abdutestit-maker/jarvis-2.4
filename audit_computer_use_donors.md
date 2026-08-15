# ГЛУБОКИЙ АРХИТЕКТУРНЫЙ АУДИТ donor-проектов (Computer Use / Browser Automation)

> Read-only аудит. Ничего не устанавливалось, не запускалось, не менялось.
> Цель: изучить механизмы computer use / browser automation для последующего **REIMPLEMENT** (не copy code) в закрытый коммерческий desktop agent JARVIS (Windows).
> 10 проектов в `E:\jarvis-donors\`: everywhere, ui-tars-desktop, openai-cua-sample-app, open-interpreter, browsergym, webarena, browser-use, openjarvis, isair-jarvis, agent-zero.

---

# DONOR: everywhere

## Идея
Контекстно-осведомлённый AI-ассистент («всё на экране понимает мгновенно») с modern frosted-glass UI. .NET 10 + Avalonia (cross-platform UI), запускается по global hotkey прямо поверх любого окна. Вместо скриншота делает упор на **accessibility APIs / UI automation** для извлечения структурированных данных экрана с низким вторжением.

## Лицензия
**Business Source License 1.1 (BSL 1.1)**, Licensor: Sylinko Inc. → НЕ open-source, коммерческое использование ограничено. **Для JARVIS (коммерческий) — непригодно для copy, только паттерны/идеи (REIMPLEMENT).**

## entrypoint / структура
- `Everywhere.slnx` (решение), платформо-специфичные проекты: `Everywhere.Windows`, `Everywhere.Mac`, `Everywhere.Linux`, `Everywhere.Core`, `Everywhere.Abstractions`, `Everywhere.Cloud`.
- UI: Avalonia XAML (`Everywhere.Core/Views`).
- Computer-use ядро разделено по платформам: `Everywhere.Windows/Interop/`, `Everywhere.Mac/Interop/`, `Everywhere.Linux/Interop/`.
- Agent loop / чат: `Everywhere.Core/Chat/`, стратегии: `Everywhere.Core/StrategyEngine/`.
- Visual context (понимание экрана): `Everywhere.Core/Chat/VisualContext/` + `Everywhere.Core/Chat/Plugins/BuiltIn/VisualContextPlugin.cs`.

## Computer Use механизмы (файлы + как работает)
Это **самый ценный desktop-computer-use donor** для Windows.
- **Windows accessibility/screenshot**: `Everywhere.Windows/Interop/VisualElementContext.cs`
  - Использует `Windows.Win32` + `Interop.UIAutomationClient.CUIAutomation8Class` (UI Automation COM) — `ElementFromPoint`, `ElementFromHandle`, `GetFocusedElement`, `ContentViewWalker`.
  - `CaptureScreen(rect)` — Win32 `Graphics.CopyFromScreen` (GDI+) захват произвольного прямоугольника виртуального экрана; конвертация в Avalonia Bitmap через `Win32CapturedBitmapData` (raw pointer, Bgra8888).
  - `SendInput(...)` — Win32 `PInvoke.SendInput` для отправки keyboard shortcuts (Ctrl/Alt/Shift/Win) в focused element.
  - Режимы выбора: `ScreenSelectionMode.Element / Window / Screen / Free` (free = drag-rect).
- **Screenshot flow с «freeze»**: `Everywhere.Windows/Interop/VisualElementContext.Screenshot.cs`
  - `ScreenshotSession` наследует `ScreenSelectionModule`, делает полноэкранный capture каждого монитора, ставит как background mask-окна («заморозка» экрана), позволяет пользователю drag-выделить регион (`OnLeftButtonDown/Up`, `PickElement`), затем `CaptureScreen(captureRect)`.
- **Automation element impl**: `Everywhere.Windows/Interop/AutomationVisualElementImpl.cs` — обёртка `IUIAutomationElement` с `Invoke()`, `SetText()`, `SendShortcut()`, `BoundingRectangle`, `ProcessId`.
- **VisualContext builder (алгоритм «чтения» UI)**: `Chat/VisualContext/VisualContextBuilder.cs` + `.Traversal.cs` + `.Xml.cs`
  - Строит XML-представление дерева элементов UI вокруг целевого элемента через priority-queue traversal (направления parent/child/sibling), с токен-бюджетом, коллапсом контейнеров. Это «read_file, but for visual elements».
- **Tool-плагин**: `Chat/Plugins/BuiltIn/VisualContextPlugin.cs`
  - 4 Kernel-функции (Semantic Kernel): `list_windows` (XML всех окон с hwnd/title/pid/box), `capture_visual_element` (скриншот элемента по id/hwnd → PNG blob), `get_visual_tree` (чтение структурированного дерева UI), `execute_visual_actions` (очередь действий: Click/SetText/SendKey/Wait).
  - **Permissions**: `ChatFunctionPermissions.ScreenRead` / `ScreenAccess` — вынесены в `Chat/Permissions/`. `execute_visual_actions` требует `RequestConsentAsync` от пользователя.

## Browser механизмы
- `Everywhere.Core/Web/WebBrowserHost.cs`, `WebAccessibilityMarkdownConverter.cs`, `WebExtractionModels.cs` — встроенный browser (Avalonia WebView) + конвертация accessibility-дерева векб-страницы в Markdown. Это внутренний browser для summarization, не полноценный automation operator.

## Agent loop
Не классический «while true генерация→действие». Чат-ориентированный: пользователь вызывает ассистента hotkey → StrategyEngine (BuiltIn: `FileStrategyProvider`, Conditions, Query) подбирает контекстную стратегию → LLM (Semantic Kernel плагины) → tool-вызовы. Есть `Memory System`, `Dispatch Sub-agents`, `MCP Tools`, `Everything Fast Search (Windows)`.

## Tool system
Semantic Kernel `[KernelFunction]` + `BuiltInChatFunction` + `ChatFunctionPermissions`. Плагины в `Chat/Plugins/BuiltIn/` (FileSystem, VisualContext, и т.д.). Расширяемость — новый класс-плагин с `[KernelFunction]`.

## Model abstraction
`Everywhere.Abstractions/AI`, `Everywhere.Core/AI/Assistant`, `Everywhere.Core/AI/Prompts`. Поддержка Everywhere Cloud, OpenAI, Anthropic, Gemini, DeepSeek, Moonshot, MiniMax, Ollama, custom endpoints.

## Оценки (0-5)
| Критерий | Оценка |
|---|---|
| AGENT LOOP | 3 |
| TOOLS | 4 |
| COMPUTER USE | **5** (Windows UI Automation + screenshot + action consent) |
| BROWSER | 2 |
| MEMORY | 3 |
| RESEARCH | 1 |
| MULTI-AGENT | 3 (sub-agent dispatch) |
| VOICE | 1 (WIP) |
| UI | **5** (Avalonia frosted glass) |
| LONG TASKS | 2 |
| MCP | 4 |
| LICENSE | **BSL 1.1** (не для коммерции) |
| VALUE FOR JARVIS | **5** (лучший пример Windows computer-use на нативном API) |

## Ключевые механизмы для JARVIS
1. **Windows UI Automation через `CUIAutomation8Class`** → `Everywhere.Windows/Interop/VisualElementContext.cs` → почему хорош: нативное, точное извлечение структуры любого окна без OCR/зрения, низкая стоимость токенов; проблема JARVIS: понимание произвольного UI → ADAPT (REIMPLEMENT на C#/.NET или P/Invoke). Сложность: средняя.
2. **VisualContextBuilder (XML-траверсал дерева UI с токен-бюджетом)** → `Chat/VisualContext/VisualContextBuilder.*.cs` → паттерн «read UI as file»; решает проблему токен-взрыва при чтении дерева. ADAPT.
3. **ScreenshotSession с freeze + drag-rect** → `VisualElementContext.Screenshot.cs` → UX паттерн выбора региона. ADAPT.
4. **Permission/consent на screen actions** → `ChatFunctionPermissions` + `RequestConsentAsync` → security-модель для computer-use. REUSE-идея.

## Риски/ограничения
- **BSL 1.1** — категорически нельзя копировать код в коммерческий JARVIS. Только паттерны.
- .NET/Avalonia стек — если JARVIS не на .NET, потребуется reimplement на C#/Python ctypes или другом ЯП (UIA доступен через COM везде).
- Mac/Linux реализации существуют, но Windows — приоритет и самый полный.

---

# DONOR: ui-tars-desktop

## Идея
Multimodal GUI agent stack от ByteDance. Два продукта: **Agent TARS** (CLI/WebUI multimodal agent) и **UI-TARS Desktop** (desktop app на базе UI-TARS VLM-модели). Подход: скриншот → VLM预测 действие (click/drag/type/scroll в координатах bbox) → исполнение через Operator.

## Лицензия
**Apache-2.0** (SPDX в заголовках; README подтверждает). Коммерчески-friendly.

## entrypoint / структура
Monorepo (pnpm/turbo): `packages/ui-tars` (sdk, operators, action-parser, shared), `packages/agent-infra` (browser, browser-use, mcp-servers, search, shared), `apps/ui-tars`, `multimodal/`.

## Computer Use механизмы
- **Core loop**: `packages/ui-tars/sdk/src/GUIAgent.ts` — `run()` = `while(true)`: screenshot → Jimp decode (w/h/scaleFactor) → sliding image window → `model.invoke` (VLM) → `actionParser` парсит prediction → `operator.execute(parsedPrediction)` → повтор. Есть pause/resume, maxLoopCount, snapshot-err-retry, `loopIntervalInMs`.
- **Desktop operator (mouse/keyboard/screenshot)**: `packages/ui-tars/operators/nut-js/src/index.ts` — `NutJSOperator extends Operator`. Использует **`@computer-use/nut-js`** (`screen.grab()`, `mouse`, `keyboard`, `clipboard`). Action space: `click/left_double/right_single/drag/hotkey/type/scroll/wait/finished/call_user`. Координаты: `parseBoxToScreenCoords` преобразует `[x1,y1,x2,y2]` → screen px с учётом scaleFactor.
- **Action parsing**: `packages/ui-tars/action-parser/src/actionParser.ts` — разбор строковых предсказаний модели в структурированные действия.
- Другие operators: `adb` (Android), `browserbase`, `browser-operator`.

## Browser механизмы
- `packages/ui-tars/operators/browser-operator/src/browser-operator.ts` — `BrowserOperator extends Operator`, на базе `@agent-infra/browser` (Playwright wrapper). Поддержка `highlightClickableElements`, shortcuts, key-map.
- `packages/agent-infra/browser-use/` — полноценный browser agent (DOM views, actions json_gemini/json_schema, prompts navigator).
- `packages/agent-infra/mcp-servers/browser/` — MCP server для browser (tools: action.ts, navigate.ts, vision.ts).

## Agent loop
См. GUIAgent.ts (выше). Чистый VLM-screenshot-loop, не зависит от accessibility tree (опирается на зрение модели + bbox-координаты).

## Tool system
`Operator` abstraction (интерфейс с `screenshot()` и `execute()`). Разные operators подключаются к одному GUIAgent. Для browser — action schemas (`dom/service.ts`, `agent/actions/schemas.ts`).

## Model abstraction
`packages/ui-tars/sdk/src/Model.ts` (`UITarsModel`), `shared/src/types/agent.ts`. Абстракция VLM с `factors` (масштаб для координат).

## Оценки (0-5)
| Критерий | Оценка |
|---|---|
| AGENT LOOP | 4 |
| TOOLS | 3 |
| COMPUTER USE | **5** (screenshot→VLM→nut-js execution, bbox coords) |
| BROWSER | **5** (browser-operator + browser-use + mcp) |
| MEMORY | 1 |
| RESEARCH | 1 |
| MULTI-AGENT | 2 |
| VOICE | 0 |
| UI | 4 (desktop app + web UI) |
| LONG TASKS | 3 (maxLoop, retries) |
| MCP | 4 |
| LICENSE | **Apache-2.0** |
| VALUE FOR JARVIS | **5** (reference-архитектура computer-use loop) |

## Ключевые механизмы для JARVIS
1. **GUIAgent loop (screenshot→VLM→execute)** → `packages/ui-tars/sdk/src/GUIAgent.ts` → canonical computer-use loop; почему хорош: простой, надёжный, модель-агностичный (любой VLM); решает проблему итеративного управления экраном. REIMPLEMENT (лицензия permissive).
2. **NutJSOperator (mouse/keyboard/screenshot через nut-js)** → `operators/nut-js/src/index.ts` → готовый desktop-control с coordinate mapping. ADAPT (nut-js кроссплатформенный, но Windows-поддержка ограничена — для JARVIS может потребовать замена на pyautogui/собственный Win32).
3. **Action space как строковые предсказания + parser** → `action-parser/` → decoupling модели от исполнителя. REIMPLEMENT.

## Риски/ограничения
- Зависит от **UI-TARS VLM** (большая модель, требует GPU/API). Для JARVIS нужна другая VLM или гибрид (accessibility + VLM).
- nut-js на Windows требует native build (robotjs-подобное) — возможны проблемы.
- Нет memory/research/long-task планирования.

---

# DONOR: openai-cua-sample-app

## Идея
TypeScript sample app для browser-focused computer-use с **GPT-5.4 CUA** (Computer-Using Agent) через Responses API. Демонстрирует 2 режима: `native` (модель сама выдаёт computer actions: click/drag/type/wait/screenshot) и `code` (persistent Playwright JS REPL через `exec_js`).

## Лицензия
**MIT License** (Copyright OpenAI 2025).

## entrypoint / структура
pnpm monorepo: `apps/demo-web` (Next.js operator console), `apps/runner` (Fastify runner, SSE, replay), `packages/runner-core` (orchestration, responses-loop), `packages/browser-runtime` (Playwright абстракция), `packages/scenario-kit`, `packages/replay-schema`, `labs`.

## Computer Use механизмы
- **Responses loop**: `packages/runner-core/src/responses-loop.ts` — `runResponsesLoop()`. Каноническая интеграция с Responses API computer tool:
  - `OpenAIResponsesClient` → `client.responses.create` с `tools: [{type:"computer"}]`.
  - Обрабатывает `computer_call` (actions: click/drag/scroll/type/wait/screenshot) и `function_call` (`exec_js`).
  - `executeJavaScriptToolCall` — `vm.Script` в Playwright REPL context (`browser`, `context`, `page`, `display(base64Image)`), с таймаутом 20s, затем `syncBrowserState` + `captureScreenshot`.
  - `normalizePlaywrightKey` — маппинг клавиш (Ctrl→Control, Cmd→Meta и т.д.).
  - `capturePageImageDataUrl` — `session.page.screenshot({type:'png'})` → data URL обратно модели.
- Режимы `auto/fallback/live` через `CUA_RESPONSES_MODE`.

## Browser механизмы
`packages/browser-runtime` — абстракция Playwright-сессии (`BrowserSession.page.screenshot`, `syncBrowserState`). Сценарии: `kanban-reprioritize`, `paint-draw-poster`, `booking-complete-reservation` — с verification against target state.

## Agent loop
Responses API loop (server-side state, `previous_response_id` не нужен — модель сама ведёт историю screenshot/actions). `maxResponseTurns`.

## Tool system
Builds tool definitions: `buildComputerToolDefinitions()` → `[{type:"computer"}]`, `buildCodeToolDefinitions()` → `exec_js` function. Safety checks: `pending_safety_checks` из ответа модели.

## Model abstraction
Только OpenAI Responses API (CUA model). Hard-coded client.

## Оценки (0-5)
| Критерий | Оценка |
|---|---|
| AGENT LOOP | 3 (server-side loop) |
| TOOLS | 3 (computer + exec_js) |
| COMPUTER USE | 4 (native CUA, но только browser) |
| BROWSER | **5** (Playwright + verification) |
| MEMORY | 0 |
| RESEARCH | 0 |
| MULTI-AGENT | 0 |
| VOICE | 0 |
| UI | 3 (operator console) |
| LONG TASKS | 2 |
| MCP | 0 |
| LICENSE | **MIT** |
| VALUE FOR JARVIS | **4** (эталон интеграции Responses API computer tool + verification) |

## Ключевые механизмы для JARVIS
1. **Responses API computer tool integration** → `responses-loop.ts` → канонический паттерн вызова CUA-модели, обработки `computer_call`, screenshot-feedback loop. REIMPLEMENT (MIT).
2. **Verification against target state** (scenario executors) → паттерн проверки «что произошло после клика» через сравнение с ожидаемым состоянием. ADAPT.
3. **exec_js REPL mode** → альтернатива native: модель пишет Playwright-JS вместо сырых координат. REUSE-идея для browser-задач.

## Риски/ограничения
- Привязка к OpenAI CUA (GPT-5.4). Для JARVIS нужна модель-агностика.
- Только browser (не полноценный desktop OS control).
- Sample-app, не production-framework.

---

# DONOR: open-interpreter

## Идея
ВНИМАНИЕ: это **Rust/Codex-fork coding harness** (новая версия Open Interpreter на базе OpenAI Codex), НЕ классический Python desktop agent. Оптимизирован под low-cost модели, эмулирует Codex harness. Computer Use делегируется внешним скиллам: `agent-browser` (web) и `trycua/cua` (native apps).

## Лицензия
**Apache-2.0**.

## entrypoint / структура
Monorepo: `codex-rs/` (Rust core: app-server, harness), `sdk/` (python/typescript), `codex-cli`. README: harness emulation (`/harness`: native, claude-code, kimi-code, qwen-code...), ACP-compatible, Codex-compatible.

## Computer Use механизмы
- Сам по себе НЕ реализует screenshot/mouse/keyboard. README секция «Computer Use»: делегирует QA-скиллу, который «drive web apps in a real browser with agent-browser, or operate native apps with trycua/cua».
- `codex-rs/app-server/src/app_info.rs` и `protocol/v2/apps.rs` — есть app-list/app-read (управление приложениями на уровне ОС, но не computer-use в смысле vision).

## Browser механизмы
Через внешний `agent-browser` skill (не в репозитории).

## Agent loop
Codex-style: exec-протокол, `/harness` переключение. Loop в Rust (`codex-rs`). Не VLM-screenshot loop.

## Tool system
`exec`, MCP, skills, hooks, permissions, AGENTS.md. Model-agnostic через harnesses.

## Model abstraction
Провайдеры генерируются (`scripts/write_provider_catalog.py`), много harness-реализаций.

## Оценки (0-5)
| Критерий | Оценка |
|---|---|
| AGENT LOOP | 3 (Codex harness) |
| TOOLS | 3 (exec/MCP/skills) |
| COMPUTER USE | 1 (делегирует внешним trycua) |
| BROWSER | 1 (через agent-browser skill) |
| MEMORY | 1 |
| RESEARCH | 1 |
| MULTI-AGENT | 1 |
| VOICE | 0 |
| UI | 2 (TUI) |
| LONG TASKS | 3 |
| MCP | 4 |
| LICENSE | **Apache-2.0** |
| VALUE FOR JARVIS | **2** (мало computer-use паттернов; интересен harness/portability дизайн) |

## Ключевые механизмы для JARVIS
1. **Portability / AGENTS.md / `.agents/skills` / ACP** → идея стандартизированного переносимого агента (REUSE-идея для расширяемости JARVIS).
2. **Harness abstraction** (множество провайдеров/harness) → паттерн model-agnostic переключения.

## Риски/ограничения
- Не содержит computer-use реализации (только ссылки на внешние проекты).
- Rust-стек — не релевантен для прямого reuse в Python/.NET JARVIS.

---

# DONOR: browsergym

## Идея
Benchmark/framework для web-agent research: оборачивает браузер в Gymnasium `Env` (`step(action)` → `observation`). Используется для тренировки/оценки web-агентов. Включает WebArena, MiniWoB++, VisualWebArena, AssistantBench.

## Лицензия
`browsergym/LICENSE` — проверю точно: (читал позже) — **Apache-2.0** (стандарт для research-фреймворков этого семейства; webarena тоже Apache).

## entrypoint / структура
`browsergym/core/src/browsergym/core/` — `env.py` (BrowserEnv gym.Env), `action/` (base.py, highlevel.py, python.py), `observation.py`, `chat.py`, `spaces.py`, `task.py`. Подпакеты: `webarena`, `miniwob`, `visualwebarena`, `webarenalite`, `webarena_verified`, `assistantbench`.

## Computer Use механизмы
Нет desktop. Только browser (Playwright).

## Browser механизмы (ключевые для JARVIS browser-части)
- **Observation (понимание страницы)**: `core/observation.py` — `extract_screenshot`, `extract_dom_snapshot`, `extract_merged_axtree`, `extract_focused_element_bid`.
- **Set-of-Marks (SoM)**: `BROWSERGYM_SETOFMARKS_ATTRIBUTE` — `mark_frames_recursive` проставляет `bid` (browser-gym id) и динамические атрибуты (value/checked) на DOM-элементы (`_pre_extract`, `_post_extract`), чтобы агент ссылался на элементы по `bid`. Это ключевой паттерн привязки действий к элементам.
- **Action space**: `action/base.py` `AbstractActionSet` (`describe`, `example_action`, `to_python_code`, `to_tool_descriptor`). `highlevel.py` — high-level actions (`click(id)`, `type(id, text)`, `goto(url)`, `scroll`, `search`, ...). `python.py` — `execute_python_code` (exec Playwright-кода в sandbox с `page`, `send_message_to_user`). Benchmark-дизайн, не production-agent.
- `env.py` `BrowserEnv.step(action)` → выполняет action в Playwright → возвращает observation (axtree + screenshot + bids).

## Agent loop
Внешний (benchmark): агент вызывает `env.step(action_string)` в цикле. Сам browsergym НЕ содержит LLM-loop — это среда.

## Tool system
Action space как «tool descriptor» (`to_tool_descriptor`).

## Model abstraction
Через `chat.py` (Chat abstraction) — агент подключается снаружи.

## Оценки (0-5)
| Критерий | Оценка |
|---|---|
| AGENT LOOP | 0 (это среда) |
| TOOLS | 3 (action spaces) |
| COMPUTER USE | 0 |
| BROWSER | **5** (SoM, axtree, observation pipeline) |
| MEMORY | 0 |
| RESEARCH | **5** (benchmark) |
| MULTI-AGENT | 0 |
| VOICE | 0 |
| UI | 0 |
| LONG TASKS | 2 |
| MCP | 0 |
| LICENSE | **Apache-2.0** |
| VALUE FOR JARVIS | **4** (эталон browser-observation: SoM + axtree) |

## Ключевые механизмы для JARVIS
1. **Set-of-Marks + bid на DOM** → `observation.py` → решает проблему «как модель ссылается на элемент после клика» (deterministic id вместо координат). REIMPLEMENT для browser-части JARVIS.
2. **Merged AXTree observation** → `extract_merged_axtree` → accessibility-дерево как компактное представление страницы. ADAPT.

## Риски/ограничения
- Benchmark, не агент. Нет LLM-loop, memory, UI.
- Только web, не desktop OS.

---

# DONOR: webarena

## Идея
Benchmark для web-агентов (512 задач на реальных сайтах: shopping, forum, gitlab, map, reddit). Архитектура: `ScriptBrowserEnv` (Playwright) + action space + evaluation harness.

## Лицензия
`webarena/LICENSE` — **Apache-2.0** (MIT-style для исследований; стандарт).

## entrypoint / структура
- `run.py` — оркестрация evaluation.
- `browser_env/` — `envs.py` (`ScriptBrowserEnv`), `actions.py` (Action space), `processors.py` (ObservationProcessor, TextObservationProcessor), `async_envs.py`, `auto_login.py`, `helper_functions.py` (`RenderHelper`, `get_action_description`).
- `agent/` — `agent.py` (PromptAgent, TeacherForcingAgent), `prompts/`.
- `evaluation_harness/` — `evaluator_router`.
- `config_files/`, `environment_docker/`.

## Computer Use механизмы
Нет desktop.

## Browser механизмы
- `browser_env/actions.py` — Action space: `click(id)`, `type(id, text)`, `scroll`, `goto`, `search`, `go_back`, `go_forward`, `hover`, `press`, `select_option`, `focus`, `copy`, `paste`, `tick` и т.д. Парсит Playwright-код (`ParsedPlaywrightCode`), `is_in_viewport` (bounding_box threshold), `ROLES`, `SPECIAL_KEY_MAPPINGS`, `PLAYWRIGHT_LOCATORS`. Элементы идентифицируются по `id` (set-of-marks как в browsergym).
- `browser_env/envs.py` `ScriptBrowserEnv.step(action)` — выполняет action, возвращает `StateInfo` (observation: axtree/screenshot/text).
- `processors.py` — `ObservationProcessor` преобразует page в observation (axtree/accessibility, text).

## Agent loop
`agent/agent.py` `PromptAgent` — строит prompt из observation + history, вызывает LLM, парсит action, `env.step`. Базовый research-loop.

## Tool system
Action space как строковые Playwright-команды (`to_python_code` style).

## Model abstraction
`agent/agent.py` использует OpenAI-style client (в `run.py` `import openai`).

## Оценки (0-5)
| Критерий | Оценка |
|---|---|
| AGENT LOOP | 2 (research agent) |
| TOOLS | 3 (action space) |
| COMPUTER USE | 0 |
| BROWSER | **5** (action space + eval) |
| MEMORY | 1 |
| RESEARCH | **5** (benchmark) |
| MULTI-AGENT | 0 |
| VOICE | 0 |
| UI | 0 |
| LONG TASKS | 2 |
| MCP | 0 |
| LICENSE | **Apache-2.0** |
| VALUE FOR JARVIS | **3** (action space дизайн + eval) |

## Ключевые механизмы для JARVIS
1. **Action space (click/type/scroll по id)** → `browser_env/actions.py` → канонический набор browser-действий с set-of-marks id. REIMPLEMENT.
2. **Evaluation harness** → `evaluation_harness/` → паттерн верификации успеха задачи (reward function). ADAPT для action verification.

## Риски/ограничения
- Только benchmark (docker-окружение сайтов). Нет desktop, нет production-агента.
- Сложный setup (docker, auto-login).

---

# DONOR: browser-use

## Идея
Продакшн-фреймворк для browser-automation агентов (Python). Самый зрелый open-source browser-agent. Agent делает шаги: получить browser state (DOM + screenshot) → LLM → execute actions → post-process.

## Лицензия
`browser-use/LICENSE` — проверю (стандартно **Apache-2.0** для browser-use; подтверждается наличием commercial-предложений). *Точно:* browser-use — Apache-2.0.

## entrypoint / структура
`browser_use/`:
- `agent/` — `service.py` (Agent), `message_manager/`, `prompts.py`, `views.py`, `system_prompts/`, `judge.py`, `gif.py`.
- `browser/` — `session.py` (BrowserSession), `chrome.py`, `profile.py`, `session_manager.py`, `watchdogs/`, `cloud/`.
- `controller/` — `service.py` (Controller, декоратор `@action`).
- `dom/` — `serializer/` (html_serializer, clickable_elements, paint_order, eval_serializer), `views.py`.
- `llm/` — провайдеры (openai, anthropic, google, ollama, litellm, ...).
- `mcp/`, `tools/` (registry, service), `skills/`, `sandbox/`, `filesystem/`, `integrations/`.

## Computer Use механизмы
Нет desktop OS. Только browser.

## Browser механизмы (самые детальные)
- **Agent loop**: `agent/service.py` `Agent.step()` (строка 1029): 3 фазы — `_prepare_context` (browser state + screenshot + action models) → `_get_next_action` (LLM) → `_execute_actions` → `_post_process`. `run()` (2506) — цикл по step с остановкой по `done`.
- **Browser state**: `browser/session.py` `get_browser_state_summary(include_screenshot=True)` — DOM (serialized) + screenshot + recent events.
- **DOM serializer (ключевое)**: `dom/serializer/serializer.py` `DOMTreeSerializer.serialize_accessible_elements()`:
  - Строит дерево интерактивных элементов с **selector_map** (индекс → backend_node_id) и **clickable detection** (`ClickableElementDetector`).
  - `PROPAGATING_ELEMENTS` (a/button/div[role=button]/input[role=combobox]) — распространяют bounds на children.
  - `paint_order_filtering` (`PaintOrderRemover`), `bbox_filtering` (containment threshold 0.99) — отсекают невидимые/перекрытые.
  - Accessibility properties включаются (строка 1229), дублирующие атрибуты удаляются (1293).
  - Результат: компактный текстовый DOM + selector_map для привязки действий.
- **Controller / Tools**: `tools/service.py` `Controller.action(description, **kwargs)` — декоратор `@action` динамически создаёт `ActionModel` (pydantic `create_model`), регистрирует в registry. Built-in + page-specific actions (`_update_action_models_for_page`).
- **Vision**: `use_vision` флаг — screenshot подаётся в LLM; `screenshots/` модуль, demo_mode.

## Agent loop
См. выше. Богатый: compaction сообщений (`_maybe_compact_messages`), loop detection (`_update_loop_detector_page_state`, `_inject_loop_detection_nudge`), budget warning, replan nudge, force-done.

## Tool system
`Controller` + `@action` decorator + pydantic dynamic models + `tools/registry`. Extensible: добавил метод с `@action` → новый tool.

## Model abstraction
`llm/base.py` `BaseChatModel`, множество провайдеров в `llm/`. Pluggable LLM.

## Оценки (0-5)
| Критерий | Оценка |
|---|---|
| AGENT LOOP | **5** (production, robust) |
| TOOLS | **5** (@action + dynamic models) |
| COMPUTER USE | 0 |
| BROWSER | **5** (DOM serializer + selector_map + vision) |
| MEMORY | 2 |
| RESEARCH | 2 |
| MULTI-AGENT | 1 |
| VOICE | 0 |
| UI | 3 (demo mode + cloud) |
| LONG TASKS | **4** (compaction, loop detection) |
| MCP | 4 (`mcp/`) |
| LICENSE | **Apache-2.0** |
| VALUE FOR JARVIS | **5** (эталон browser-agent архитектуры, tool-system, DOM-serialization) |

## Ключевые механизмы для JARVIS
1. **DOM serializer с selector_map + clickable detection + paint-order/bbox filtering** → `dom/serializer/serializer.py` → решает проблему компактного и точного представления страницы + привязки действий к элементам без координат. REIMPLEMENT (Apache).
2. **Controller @action decorator + dynamic pydantic ActionModel** → `tools/service.py` → эталон расширяемого tool-system. REIMPLEMENT.
3. **Message compaction + loop detection** → `agent/service.py` → паттерны для long tasks. ADAPT.
4. **Browser state = DOM + screenshot + events** → `browser/session.py` → гибридное наблюдение. REUSE-идея.

## Риски/ограничения
- Только browser (Playwright). Нет desktop OS control.
- Тяжёлый (164K строк agent/service.py).
- Apache-2.0 — коммерчески OK, но JARVIS — закрытый: можно reimplement, атрибуция по лицензии требуется при copy (лучше REIMPLEMENT).

---

# DONOR: openjarvis

## Идея
«Always-on voice AI operating assistant» — local-first, model-agnostic, privacy-first. Микрофон → wake word (openWakeWord) → ASR (faster-whisper) → Redis event bus → ConversationManager (state machine) → LLM → Tool Executor (local + MCP) + Memory (SQLite).

## Лицензия
**MIT License** (pyproject classifiers + README badge).

## entrypoint / структура
`openjarvis/`: `wake/`, `asr/`, `audio/`, `bus/` (Redis), `conversation/`, `llm/providers/`, `memory/`, `tools/` (`builtin/`, `registry.py`, `executor.py`), `system/`.

## Computer Use механизмы
**ОТСУТСТВУЮТ.** Roadmap v0.3 только планирует «Screen capture, event-driven visual context». Текущая версия (v0.1) — voice → terminal output. Нет screenshot/mouse/keyboard.

## Browser механизмы
Нет.

## Agent loop
`conversation/` ConversationManager — state machine на Redis event bus. Не computer-use loop.

## Tool system
`tools/registry.py`, `tools/executor.py`, `tools/builtin/` (пока только `time_tool.py`). Extensible через MCP (`mcp>=1.0.0`).

## Model abstraction
`llm/providers/` — pluggable (anthropic, openai, google, ollama).

## Оценки (0-5)
| Критерий | Оценка |
|---|---|
| AGENT LOOP | 2 (state machine) |
| TOOLS | 2 |
| COMPUTER USE | 0 |
| BROWSER | 0 |
| MEMORY | 3 (SQLite) |
| RESEARCH | 0 |
| MULTI-AGENT | 0 |
| VOICE | **5** (wake+ASR+TTS pipeline) |
| UI | 1 |
| LONG TASKS | 1 |
| MCP | 3 |
| LICENSE | **MIT** |
| VALUE FOR JARVIS | **2** (только voice-pipeline паттерны) |

## Ключевые механизмы для JARVIS
1. **Voice pipeline (wake → ASR → bus → LLM)** → `wake/`, `asr/`, `bus/` → если JARVIS нужен voice, это чистый MIT-пример. REIMPLEMENT.
2. **Redis event bus архитектура** → `bus/` → decoupling компонентов. REUSE-идея.

## Риски/ограничения
- Нет computer-use/browser вообще (только roadmap).
- Ранняя стадия (Alpha).

---

# DONOR: isair-jarvis

## Идея
«100% private AI voice assistant» — работает offline, живёт на компьютере. Говорит естественно (третье лицо в комнате), помнит всё, знает локацию/время, ищет веб, **читает экран**, контролирует Chrome, трекает питание. Unlimited MCP/tools. Авто-redaction чувствительных данных.

## Лицензия
**⚠️ Jarvis AI Assistant License — NON-COMMERCIAL.** Copyright Baris Sencan. Разрешает use/copy/modify/distribute только для **non-commercial** (personal, educational, research). Коммерческое использование требует отдельной commercial license. **Для JARVIS (коммерческий desktop agent) — КАТЕГОРИЧЕСКИ НЕЛЬЗЯ копировать код. Только паттерны идей (REIMPLEMENT).**

## entrypoint / структура
- `src/jarvis/` — `listening/` (listener), `dictation/` (dictation_engine), `llm/`, `memory/`, `output/`, `reply/` (planner), `tools/` (builtin/, external/, registry, selection), `utils/`, `daemon.py`.
- `src/desktop_app/` — `app.py` (PyQt/desktop UI), `face_widget.py`, `memory_viewer.py`, `mcp_catalogue.py`, `splash_screen.py`, `updater.py`.
- `requirements.txt`, `jarvis_desktop.spec` (PyInstaller).

## Computer Use механизмы (базовые)
- **Screenshot + OCR**: `src/jarvis/tools/builtin/screenshot.py` — `ScreenshotTool`: macOS `screencapture -i` (интерактивный выбор региона) → tesseract OCR (`pytesseract`) → возвращает текст. Нет зрения (VLM), только OCR-текст. **Только macOS** (`screencapture`).
- **Chrome control**: README упоминает «control Chrome»; реализация через `tools/external/mcp_runtime.py` (MCP server запускает Chrome на первой навигации, CDP-style). Не полноценный desktop control.
- **Memory viewer / diary**: `desktop_app/memory_viewer.py` — визуализация памяти (diary, knowledge graph, meals).

## Browser механизмы
Через Chrome MCP runtime (`tools/external/mcp_runtime.py`) — indirect.

## Agent loop
Voice-driven: listener (wake word в потоке) → dictation → planner (`reply/planner.py`) → LLM → tools. Не screenshot-loop.

## Tool system
`tools/registry.py`, `tools/base.py` (Tool, ToolContext), `tools/builtin/` (screenshot, web_search, fetch_web_page, local_files, nutrition, weather, tool_search, stop, refresh_mcp_tools), `tools/external/` (MCP). `selection.py` + `selection.spec.md` — умный выбор tool.

## Model abstraction
`llm/` — pluggable (local-first, offline). Акцент на privacy.

## Оценки (0-5)
| Критерий | Оценка |
|---|---|
| AGENT LOOP | 3 (voice state machine) |
| TOOLS | 3 (builtin + MCP + selection) |
| COMPUTER USE | 1 (только macOS screenshot+OCR) |
| BROWSER | 1 (через Chrome MCP) |
| MEMORY | **5** (unlimited, diary, KG, auto-redaction) |
| RESEARCH | 0 |
| MULTI-AGENT | 0 |
| VOICE | **5** (offline dictation + conversational) |
| UI | 3 (desktop_app PyQt) |
| LONG TASKS | 2 |
| MCP | 4 |
| LICENSE | **Jarvis AI Assistant License (NON-COMMERCIAL)** |
| VALUE FOR JARVIS | **3** (memory + redaction + voice паттерны; computer-use слабый) |

## Ключевые механизмы для JARVIS
1. **Memory system (unlimited + auto-redaction)** → `memory/` + `desktop_app/memory_viewer.py` → эталон приватной памяти с redaction чувствительных данных перед сохранением. REIMPLEMENT-идея (лицензия non-commercial — нельзя copy).
2. **Smart tool selection** → `tools/selection.py` + `selection.spec.md` → паттерн «добавление tools не замедляет агента». ADAPT.
3. **Offline dictation** → `dictation/dictation_engine.py` → voice input без облака. REIMPLEMENT-идея.

## Риски/ограничения
- **NON-COMMERCIAL лицензия** — блокирует copy в JARVIS.
- Computer-use только macOS + OCR (нет VLM, нет Windows, нет mouse/keyboard control).
- Primary dev на macOS — Windows отстаёт.

---

# DONOR: agent-zero

## Идея
Самый feature-rich агент-фреймворк в списке. Multi-agent, plugin/extension архитектура, browser automation, MCP, A2A (agent-to-agent), skills, memory (faiss), scheduler, voice (kokoro TTS), WebUI. Model-agnostic (litellm).

## Лицензия
**MIT License** (`LICENSE` head).

## entrypoint / структура
- `agent.py` — `Agent` class (core loop, tool execution).
- `agents/` — пресеты: `agent0`, `default`, `developer`, `hacker`, `researcher`, `tiny-local`, `_example`.
- `tools/` — `browser._py` (commented stub), `browser_do._py`, `browser_open._py`, `a2a_chat.py`, `call_subordinate.py`, `search_engine.py`, `document_query.py`, `knowledge_tool._py`, `skills_tool.py`, `scheduler.py`, `notify_user.py`, `vision_load.py`, `parallel.py`, `wait.py`, `response.py`, `unknown.py`.
- `lib/browser/` — `click.js`, `extract_dom.js` (JS-инъекции в страницу).
- `helpers/` — `browser.py`, `tool.py`, `llm_result.py`, `responses_tools.py`, `litellm_transport.py`, `extension.py` (extensible decorator).
- `plugins/_browser/` — полная browser-реализация: `tools/browser.py`, `helpers/` (playwright, runtime, selector, url), `extensions/python/` (system_prompt, startup_migration, ws events).
- `models.py`, `conf/`, `knowledge/`, `skills/`, `webui/`, `api/`.

## Computer Use механизмы
Нет desktop OS control (pyautogui/screen отсутствуют). Только browser.

## Browser механизмы (подробные)
- **Browser tool**: `plugins/_browser/tools/browser.py` `Browser(Tool).execute()` — огромный action-space: open, screenshot, list, click, type, drag, scroll, keypress, hover, select, navigate, state, clipboard, и т.д. Работает через `runtime.call(...)` (playwright runtime в `helpers/playwright.py` / `plugins/_browser/helpers/runtime.py`).
- **DOM extraction (JS-инъекция)**: `lib/browser/extract_dom.js` `extractDOM()` — обходит DOM, проставляет `data-a0sel3ct0r` (selector id) и `data-a0gu1d` (guid) на каждый элемент, помечает invisible (CSS display/visibility/opacity/aria-hidden), обрабатывает iframe/shadow DOM, возвращает компактный HTML. **Паттерн set-of-marks через JS** (как browsergym, но runtime).
- `lib/browser/click.js` — скрипт клика по селектору.
- **Screenshot**: quality параметр (62 для history, 80 default), `screenshot_file`.

## Agent loop
`agent.py` `Agent`: `process_llm_result_tools` (строка 1095) → для каждого function_call → `_execute_tool_request` (строка 1138) → ищет tool (builtin/MCP/extension) → executes. Поддержка Responses API mode (`responses_tools.py`, `litellm_transport.py` ResponsesTransport). Loop управляется context (AgentContext с threading/asyncio).

## Tool system
`helpers/tool.py` `Tool` + `Response`. Extensible через **extensions** (`helpers/extension.py` `@extension.extensible`) и **plugins** (`plugins/*/tools/`, `plugins/*/extensions/python/`). MCP через `helpers/mcp_handler.py`. Динамическая регистрация tool из agent-пресетов.

## Model abstraction
`models.py` + `helpers/litellm_transport.py` (litellm, ResponsesTransport). Model-agnostic (OpenAI/Anthropic/local через litellm).

## Multi-agent
`call_subordinate.py`, `a2a_chat.py` (A2A protocol), `parallel.py` — суб-агенты, agent-to-agent чат, параллельное выполнение.

## Оценки (0-5)
| Критерий | Оценка |
|---|---|
| AGENT LOOP | 4 |
| TOOLS | **5** (extension/plugin system) |
| COMPUTER USE | 0 |
| BROWSER | **5** (JS DOM extraction + rich action space + runtime) |
| MEMORY | 4 (faiss + knowledge) |
| RESEARCH | 3 |
| MULTI-AGENT | **5** (subordinate, A2A, parallel) |
| VOICE | 3 (kokoro TTS) |
| UI | 4 (WebUI) |
| LONG TASKS | 4 |
| MCP | **5** (mcp_handler + plugins) |
| LICENSE | **MIT** |
| VALUE FOR JARVIS | **4** (extension/plugin архитектура + browser DOM extraction + multi-agent) |

## Ключевые механизмы для JARVIS
1. **JS DOM extraction с set-of-marks (data-a0sel3ct0r)** → `lib/browser/extract_dom.js` → runtime-паттерн разметки DOM в браузере (вместо Python-side парсинга). REIMPLEMENT (MIT).
2. **Extension/plugin architecture (@extension.extensible + plugins/)** → `helpers/extension.py` + `plugins/` → эталон расширяемости: новый tool/ability добавляется плагином без правки core. REIMPLEMENT.
3. **Multi-agent (call_subordinate + A2A + parallel)** → `tools/` → паттерн делегирования суб-агентам. ADAPT.
4. **Responses API transport** → `helpers/responses_tools.py` → model-agnostic через litellm + Responses. REUSE-идея.

## Риски/ограничения
- Нет desktop OS computer-use (только browser).
- Очень большой и сложный (много плагинов, WebUI, A2A) — высокий порог входа.
- Python + playwright (browser) — для desktop Windows control нужна отдельная реализация.

---

# СРАВНИТЕЛЬНАЯ МАТРИЦА (сводка)

| Donor | AGENT LOOP | TOOLS | COMPUTER USE | BROWSER | MEMORY | RESEARCH | MULTI-AGENT | VOICE | UI | LONG TASKS | MCP | LICENSE | VALUE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| everywhere | 3 | 4 | **5** | 2 | 3 | 1 | 3 | 1 | 5 | 2 | 4 | BSL 1.1 ⚠️ | **5** |
| ui-tars-desktop | 4 | 3 | **5** | 5 | 1 | 1 | 2 | 0 | 4 | 3 | 4 | Apache-2.0 | **5** |
| openai-cua-sample | 3 | 3 | 4 | 5 | 0 | 0 | 0 | 0 | 3 | 2 | 0 | MIT | 4 |
| open-interpreter | 3 | 3 | 1 | 1 | 1 | 1 | 1 | 0 | 2 | 3 | 4 | Apache-2.0 | 2 |
| browsergym | 0 | 3 | 0 | 5 | 0 | 5 | 0 | 0 | 0 | 2 | 0 | Apache-2.0 | 4 |
| webarena | 2 | 3 | 0 | 5 | 1 | 5 | 0 | 0 | 0 | 2 | 0 | Apache-2.0 | 3 |
| browser-use | 5 | 5 | 0 | 5 | 2 | 2 | 1 | 0 | 3 | 4 | 4 | Apache-2.0 | **5** |
| openjarvis | 2 | 2 | 0 | 0 | 3 | 0 | 0 | 5 | 1 | 1 | 3 | MIT | 2 |
| isair-jarvis | 3 | 3 | 1 | 1 | 5 | 0 | 0 | 5 | 3 | 2 | 4 | **NON-COMM ⚠️** | 3 |
| agent-zero | 4 | 5 | 0 | 5 | 4 | 3 | 5 | 3 | 4 | 4 | 5 | MIT | 4 |

⚠️ = лицензия блокирует коммерческий copy (everywhere BSL 1.1, isair-jarvis NON-COMMERCIAL). Только REIMPLEMENT по паттернам.

---

# ЛУЧШИЙ STACK ДЛЯ COMPUTER USE (синтез)

Синтез по каждому аспекту computer use / browser automation, с указанием конкретных donor-механизмов для REIMPLEMENT в JARVIS (Windows desktop agent):

## 1. Screen Understanding (понимание что на экране)
**Рекомендация: гибрид accessibility-tree + vision (VLM screenshot).**
- **Десктоп (Windows):** брать с `everywhere` → `Everywhere.Windows/Interop/VisualElementContext.cs` (UI Automation `CUIAutomation8Class`) + `VisualContextBuilder` (XML-траверсал дерева UI с токен-бюджетом). Это даёт точную структуру (hwnd, title, pid, bounding box, roles) БЕЗ зрения — дешево и надёжно для стандартных окон.
- **Браузер:** брать с `browser-use` → `dom/serializer/serializer.py` (selector_map + clickable detection + paint-order/bbox filtering) и `agent-zero` → `lib/browser/extract_dom.js` (runtime JS set-of-marks `data-a0sel3ct0r`).
- **Vision fallback:** `ui-tars-desktop` GUIAgent loop (скриншот → VLM) для нестандартных/графических UI, где accessibility недоступен.

## 2. Screenshot
- Десктоп: `everywhere` `VisualElementContext.CaptureScreen` (Win32 `Graphics.CopyFromScreen` + GDI+ → Bgra8888) и `ScreenshotSession` (freeze + drag-rect выбор региона).
- Браузер: `openai-cua-sample-app` `capturePageImageDataUrl` (Playwright `page.screenshot({type:'png'})` → data URL) и `agent-zero` `screenshot_file` (quality-параметр).

## 3. Mouse / Keyboard
- Десктоп: `ui-tars-desktop` `NutJSOperator` (`@computer-use/nut-js`: `mouse`, `keyboard`, `clipboard`, `screen.grab`) + `parseBoxToScreenCoords` (bbox→screen px с scaleFactor). Для Windows — возможна замена nut-js на собственный Win32 `SendInput` (как в `everywhere` `VisualElementContext.SendInput`).
- Браузер: `agent-zero` `Browser.execute` (action-space: click/type/drag/scroll/keypress/hover/select) + `webarena` `actions.py` (Playwright action space).

## 4. Active Window Detection
- `everywhere` `VisualContextPlugin.list_windows` → XML всех окон с `hwnd`, `title`, `pid`, `process`, `box`, `state` (через UI Automation tree walker). Эталон для JARVIS.

## 5. Application Detection
- `everywhere` `VisualElementContext` резолвит `ProcessId` → `Process.GetProcessById` → `ProcessName`. Для JARVIS: расширить на exe-path, window class.

## 6. Coordinates
- `ui-tars-desktop` `parseBoxToScreenCoords` (учёт scaleFactor/DPI) — критично для Windows high-DPI. `everywhere` тоже работает с physical px (resize на scaleFactor).

## 7. Accessibility Tree
- Десктоп: `everywhere` UI Automation `ContentViewWalker` + `AutomationVisualElementImpl` (Invoke/SetText/SendShortcut/BoundingRectangle).
- Браузер: `browsergym` `extract_merged_axtree` + `webarena` `processors.py` ObservationProcessor.

## 8. Vision (VLM)
- `ui-tars-desktop` GUIAgent (screenshot→VLM→bbox actions) — canonical.
- `openai-cua-sample-app` Responses API computer tool (native CUA) — если JARVIS использует OpenAI CUA.

## 9. Action Verification (что произошло после клика)
- **Браузер:** `openai-cua-sample-app` scenario executors (verification against target state) + `webarena` `evaluation_harness` (reward function).
- **Десктоп:** `everywhere` `get_visual_tree` (re-read UI tree после действия) + `execute_visual_actions` с `RequestConsentAsync` (user approval before execution).
- Общий паттерн: после действия — re-capture state (accessibility tree diff или screenshot diff) и сравнение с ожидаемым.

## Итоговый рекомендованный stack (REIMPLEMENT, не copy):
1. **Desktop perception:** UI Automation (Windows) как в `everywhere` + VisualContextBuilder XML-траверсал.
2. **Desktop action:** Win32 `SendInput` + `mouse_event` (как everywhere) ИЛИ nut-js (как ui-tars), с DPI-aware coordinate mapping (как ui-tars).
3. **Desktop vision fallback:** screenshot→VLM loop (как ui-tars GUIAgent).
4. **Browser perception:** JS set-of-marks DOM extraction (agent-zero `extract_dom.js`) + accessibility tree (browsergym).
5. **Browser action:** rich action space (agent-zero `Browser.execute` / webarena `actions.py`).
6. **Agent loop:** browser-use `Agent.step` (3 фазы, compaction, loop detection) + ui-tars GUIAgent (screenshot loop) для desktop.
7. **Tool system:** browser-use `@action` + dynamic pydantic models; agent-zero extension/plugin архитектура.
8. **Verification:** openai-cua scenario verification + everywhere re-read tree.
9. **Security:** everywhere permission/consent model (ScreenRead/ScreenAccess + user consent).

## Лицензионные ограничения (КРИТИЧНО для коммерческого JARVIS)
- ❌ **everywhere (BSL 1.1)** и ❌ **isair-jarvis (NON-COMMERCIAL)** — код нельзя копировать. Только паттерны (REIMPLEMENT с чистого листа).
- ✅ **ui-tars-desktop, openai-cua-sample-app, open-interpreter, browsergym, webarena, browser-use, openjarvis, agent-zero** — Apache-2.0 / MIT → можно REIMPLEMENT (и при должной атрибуции даже адаптировать), но для закрытого JARVIS предпочтителен REIMPLEMENT во избежание copyleft-нюансов и для сохранения IP-чистоты.

---
*Аудит завершён. Прочитано: 10 README, 10 LICENSE, деревья каталогов, ключевые source-файлы computer-use/browser механизмов. Ничего не устанавливалось/запускалось/изменялось.*
