# JARVIS — SPRINT 10  
## REAL-WORLD COMPUTER OPERATOR

Sprint 9 и Voice/TTS Hardening завершены.

Текущая цель: JARVIS должен уметь выполнить реальную неизвестную задачу на Windows от начала до проверенного результата.

Контрольный сценарий:

> «Поставь мне эту программу и настрой так же, как на этом видео.»

Нормальный UX:

> «Сейчас разберусь, сэр.»

После выполнения:

> «Готово. Проверяйте, сэр.»

Не показывать пользователю внутреннюю техническую кухню без запроса.

---

# 1. ОСНОВНОЙ PIPELINE

Использовать существующий Capability Engine:

```text
UNDERSTAND
→ REFERENCE ANALYSIS
→ RESEARCH
→ DESIRED STATE
→ CAPABILITY SEARCH
→ PLAN
→ EXECUTE
→ OBSERVE
→ VERIFY
→ REPAIR
→ LEARN
→ REPORT
```

Не создавать параллельную архитектуру.

---

# 2. WINDOWS AUTOMATION

Наполнить существующий WindowsCapabilityLayer реальными providers.

Приоритет:

```text
1. Native API / COM
2. CLI / PowerShell
3. Config files / registry
4. Windows UI Automation / Accessibility
5. Vision-based interaction
6. Raw coordinates — только последний fallback
```

Создать рабочие primitives:

```text
window.list
window.active
window.focus
window.inspect

ui.tree
ui.find
ui.invoke
ui.set_value
ui.select
ui.toggle
ui.scroll
ui.wait_for

process.list
process.launch
process.stop

registry.read
registry.write

file.read
file.write
file.copy
file.move
```

Использовать Windows UI Automation, accessibility tree или совместимый provider.

Если доступен Microsoft WinApp CLI — поддержать через adapter.

Не делать жёсткую зависимость.

---

# 3. APP DISCOVERY

JARVIS должен уметь впервые открыть неизвестное приложение и исследовать его интерфейс.

Создать:

```text
AppExplorer
```

Он должен:

- найти главное окно;
- прочитать accessibility tree;
- определить menus;
- buttons;
- tabs;
- inputs;
- dropdowns;
- dialogs;
- settings pages;
- current values.

Создавать структурированную карту:

```json
{
  "application": "...",
  "windows": [],
  "menus": [],
  "settings": [],
  "controls": []
}
```

Сохранять как:

```text
AppKnowledge
```

После успешной миссии AppKnowledge сохраняется для будущего использования.

---

# 4. BROWSER AUTOMATION

Добавить реальный BrowserAutomationProvider.

Предпочтительно:

```text
Playwright / DOM-first
```

Capabilities:

```text
browser.open
browser.navigate
browser.read
browser.find
browser.click
browser.type
browser.download
browser.wait
browser.extract
browser.inspect_dom
```

Не использовать screenshot-clicking, если DOM доступен.

Vision — fallback.

---

# 5. SOFTWARE DISCOVERY

Для установки программы JARVIS должен искать источник в порядке:

```text
1. winget / package manager
2. официальный сайт
3. официальный GitHub
4. verified release source
```

Никогда автоматически не скачивать `.exe` с случайного сайта.

Создать:

```text
SoftwareResolver
```

Возвращает:

```json
{
  "name": "...",
  "official_source": "...",
  "package_manager": "...",
  "installer_type": "...",
  "architecture": "...",
  "version": "...",
  "signature_expected": true
}
```

---

# 6. INSTALLER INTELLIGENCE

Поддержать:

```text
winget
MSI
EXE
ZIP/portable
```

Installer Engine должен:

- определить тип;
- проверить архитектуру;
- проверить существующую установку;
- определить installed version;
- скачать;
- проверить источник;
- при возможности проверить digital signature/hash;
- запустить installer;
- обработать elevation/UAC;
- дождаться завершения;
- проверить фактическую установку.

Installer exit code != proof of success.

После установки проверить:

```text
executable exists
version detected
application launches
window appears
```

---

# 7. REFERENCE INTERPRETER

Расширить существующий ReferenceInterpreter.

Поддержать:

```text
video
image
web page
text instructions
existing configured application
```

Главное правило:

не сохранять клики.

Из reference извлекать:

```text
DESIRED STATE
```

Пример:

Видео показывает OBS.

Результат:

```json
{
  "application": "OBS",
  "desired_state": {
    "encoder": "H264",
    "bitrate": 8000,
    "resolution": "1920x1080",
    "fps": 60
  }
}
```

---

# 8. VIDEO UNDERSTANDING FOUNDATION

Создать VideoReferenceProvider.

Для первого этапа:

- принимать локальный video file или URL;
- извлекать metadata;
- извлекать keyframes;
- извлекать subtitle/transcript, если доступно;
- анализировать relevant frames;
- связывать spoken instructions с visible settings.

Не анализировать каждый frame.

Использовать adaptive sampling / scene changes.

Output:

```json
{
  "steps": [],
  "observed_settings": {},
  "uncertain_items": [],
  "desired_state": {}
}
```

Если какой-то параметр не удалось определить — не выдумывать.

---

# 9. CURRENT STATE → DESIRED STATE

Перед изменением программы:

```text
inspect current state
```

После этого построить diff:

```text
CURRENT
vs
DESIRED
```

Менять только отличающиеся параметры.

---

# 10. EXECUTION WITHOUT DISTURBING USER

Классифицировать действия:

```text
BACKGROUND_SAFE
FOREGROUND_REQUIRED
USER_REQUIRED
```

BACKGROUND_SAFE:

- research;
- download;
- CLI;
- API;
- filesystem;
- silent install;
- config parsing.

FOREGROUND_REQUIRED:

- GUI settings;
- visible installer;
- UI inspection requiring window focus.

USER_REQUIRED:

- password;
- 2FA;
- CAPTCHA;
- license purchase;
- UAC interaction if automation unavailable.

Не захватывать foreground без необходимости.

---

# 11. FOREGROUND SESSION

Если GUI действительно нужен:

создать:

```text
ForegroundSession
```

Он должен:

- запомнить активное пользовательское окно;
- открыть/фокусировать нужное приложение;
- выполнить UI steps;
- минимизировать время foreground;
- вернуть пользователя в прежнее приложение.

---

# 12. USER INTERRUPTION

Во время mission поддержать:

```text
стоп
пауза
продолжай
отмени
что ты делаешь?
не меняй это
пропусти
```

Не терять mission context.

---

# 13. VERIFICATION

После настройки обязательно повторно читать реальное состояние.

Использовать:

```text
accessibility tree
DOM
config
registry
process state
file state
screen state
application UI values
```

Только если desired state достигнут:

```text
COMPLETED
```

---

# 14. REPAIR

Если часть desired state не совпала:

не начинать всё сначала.

Пример:

```text
7/8 settings correct
audio bitrate wrong
```

Repair должен менять только audio bitrate.

После repair снова verify.

---

# 15. APP LEARNING

После успешной неизвестной программы сохранить:

```text
AppKnowledge
CapabilityEpisode
successful selectors
settings locations
best execution method
fallback method
verification rules
```

Пример:

```text
OBS:
Output Settings → Streaming → Encoder
```

Но хранить semantic selectors, не координаты.

---

# 16. SELECTOR RESILIENCE

UI selector должен использовать:

```text
automation id
control type
accessible name
label
hierarchy
semantic role
```

Coordinates использовать только fallback.

Если UI обновился:

повторно inspect tree и найти control по смыслу.

---

# 17. RESEARCH → EXECUTION

Structured research должен реально подключаться к Capability Engine.

Если capability missing:

```text
research
→ discover execution method
→ acquire primitives
→ execute
```

Не заканчивать research длинным текстовым ответом, если пользователь попросил действие.

---

# 18. SAFETY

Использовать существующий Risk × Confidence.

Дополнить для:

```text
software installation = MEDIUM
registry changes = MEDIUM/HIGH
security software = HIGH
account/payment = HIGH
system destructive = CRITICAL
```

HIGH/CRITICAL требуют подтверждения.

LOW/MEDIUM действуют по существующей policy.

---

# 19. CHECKPOINTS

Перед изменением:

- config backup;
- registry previous value;
- file backup;
- app setting snapshot;
- previous version when practical.

При unrecoverable failure:

```text
rollback
```

---

# 20. DOWNLOAD SAFETY

Перед выполнением скачанного installer:

проверять минимум:

- источник;
- HTTPS;
- filename;
- architecture;
- signature/hash, если доступно;
- executable metadata.

Сомнительный источник автоматически не запускать.

---

# 21. PASSWORDS / SECRETS

JARVIS не должен:

- читать browser password store;
- вытаскивать сохранённые passwords;
- писать secrets в logs;
- сохранять пользовательский пароль в CapabilityEpisode.

Если нужен пароль:

> «Сэр, здесь нужен ваш пароль. Введите его — дальше я сам.»

---

# 22. OBSERVABILITY

Для разработчика сохранять Action Trace:

```text
Research
Plan
Execution
Observation
Verification
Repair
Learning
```

Для пользователя по умолчанию это скрыто.

По запросу:

> «Что ты сделал?»

показать понятный список действий.

Не раскрывать hidden reasoning.

---

# 23. LIVE SAFE TEST APPLICATION

Выбрать безопасное бесплатное Windows-приложение для end-to-end теста.

Требования:

- официальный источник;
- не системное;
- легко удалить;
- несколько настроек;
- без аккаунта;
- без оплаты.

Не использовать production-critical software.

Прогнать настоящий сценарий:

```text
install
→ launch
→ inspect UI
→ change settings
→ verify
→ learn
```

---

# 24. SECOND RUN

После первого успешного запуска:

удалить/сбросить test state и повторить похожую задачу.

Проверить:

```text
AppKnowledge reused
CapabilityEpisode reused
fewer discovery steps
fewer LLM calls
lower latency
```

---

# 25. REFERENCE TEST

Создать безопасный reference fixture:

например короткая инструкция или тестовое видео с несколькими настройками.

Проверить:

```text
reference
→ desired state
→ application configuration
→ verification
```

---

# 26. TESTS

Добавить tests минимум для:

- UI tree parsing;
- semantic control lookup;
- selector fallback;
- AppExplorer;
- AppKnowledge persistence;
- Browser DOM provider;
- SoftwareResolver trusted source ranking;
- installer detection;
- installer verification;
- ReferenceInterpreter;
- desired state extraction;
- foreground session restoration;
- targeted repair;
- checkpoint/rollback;
- password/secret filtering;
- unknown app learning;
- second-run reuse;
- capability integration;
- Sprint 9 regressions;
- Voice Hardening regressions.

---

# 27. FULL REGRESSION

Перед:

```text
record full pytest baseline
```

После:

- full pytest;
- compileall;
- frontend build if modified;
- cargo check if Tauri modified;
- git diff --check.

Не скрывать failures.

---

# 28. FINAL DEMO

Главная демонстрация должна выглядеть так:

```text
USER:
Установи тестовую программу и настрой её как в этой инструкции/reference.

JARVIS:
Сейчас разберусь, сэр.
```

Внутри:

```text
discover
research
download
verify installer
install
launch
inspect
desired state
configure
observe
verify
learn
```

Финал:

```text
JARVIS:
Готово. Проверяйте, сэр.
```

---

# 29. FINAL REPORT

Показать:

1. real architecture;
2. changed files;
3. Windows provider;
4. Browser provider;
5. SoftwareResolver;
6. Installer Engine;
7. AppExplorer;
8. AppKnowledge example;
9. Reference Interpreter;
10. VideoReferenceProvider;
11. live installation demo;
12. verification result;
13. second-run improvement;
14. risk/checkpoint behavior;
15. tests before/after;
16. limitations;
17. rollback instructions.

---

# CRITICAL RULES

Не начинать Sprint 11.

Не делать UI redesign.

Не добавлять новые LLM-модели.

Не объявлять GUI automation рабочей без реального safe live test.

Не использовать raw coordinates как основной механизм.

Не считать installer exit code успехом.

Не считать tool success выполненной миссией.

Не сохранять passwords/secrets.

Не симулировать результаты.

Главный критерий Sprint 10:

> Может ли JARVIS получить неизвестную реальную Windows-задачу, самостоятельно исследовать программу, установить её, понять интерфейс, изменить нужное состояние, проверить результат и сохранить приобретённое знание?

Если нет — Sprint 10 не завершён.