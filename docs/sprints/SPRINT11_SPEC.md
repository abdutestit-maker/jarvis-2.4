# JARVIS — SPRINT 11
## LIVING CONTEXT + PROACTIVE INTELLIGENCE + WORKFLOW LEARNING

Sprint 10 полностью VERIFIED.

Baseline:

- 243 passed
- 2 skipped
- 0 failed
- Capability Engine работает
- Real Windows Operator работает
- Browser DOM/Playwright работает
- Installer pipeline работает
- AppExplorer/AppKnowledge работает
- Reference/Video foundation работает
- Shadow Engine работает
- Memory/Persona/TTS/STT/System Triggers работают

Не начинать UI redesign.

---

# ГЛАВНАЯ ЦЕЛЬ

JARVIS должен перестать существовать только в момент запроса.

Он должен понимать:

> Что пользователь сейчас делает?  
> Над чем он работает?  
> Чего пытается добиться?  
> Где застрял?  
> Что постоянно повторяет?  
> Что можно сделать за него?  
> Стоит ли сейчас вообще вмешиваться?

Он не должен ждать шаблонной команды.

---

# UX

Пользователь работает.

JARVIS молчит.

Он видит контекст и строит понимание в фоне.

Например пользователь:

- несколько раз открывает одни и те же папки;
- экспортирует одинаковые файлы;
- исправляет одну ошибку;
- переключается между браузером и программой;
- пытается настроить неизвестное приложение.

JARVIS может сам сказать:

> «Сэр, вы уже третий раз делаете одно и то же. Хотите, я возьму это на себя?»

И после разрешения:

> «Понял.»

Дальше создаёт workflow/capability и выполняет.

---

# 1. LIVING CONTEXT ENGINE

Создать:

```text
LivingContextEngine
```

Он поддерживает постоянно обновляемую модель текущей ситуации пользователя.

Источники:

```text
active window
window title
process
UI accessibility context
browser domain/page title
recent commands
recent JARVIS missions
file activity
clipboard metadata when permissioned
idle/AFK
time
application sessions
Shadow patterns
recent failures
recent successful capabilities
```

Не хранить screen pixels постоянно.

Не вести скрытую тотальную запись.

Сохранять только структурированное полезное состояние.

---

# 2. CURRENT CONTEXT MODEL

Пример:

```json
{
  "active_application": "Photoshop",
  "session_duration": 1840,
  "current_project": "catalog",
  "probable_activity": "exporting product images",
  "recent_actions": [
    "open image",
    "resize",
    "export png"
  ],
  "repetition_score": 0.88,
  "friction_score": 0.64,
  "user_busy": true,
  "jarvis_should_interrupt": false
}
```

Это временный working context.

Не путать с persistent memory.

---

# 3. ACTIVITY EPISODES

Разбивать использование ПК на смысловые episodes.

Например:

```text
Gaming session
Coding session
Video editing
Product image preparation
Watching movie
Researching product
Configuring software
Browsing casually
```

Создать:

```text
ActivityEpisode
```

Содержит:

```text
start
end
applications
high-level actions
goal hypothesis
problems
JARVIS interventions
outcome
```

---

# 4. GOAL INFERENCE

Создать:

```text
GoalTracker
```

Он пытается определить текущую цель пользователя.

Не делать вывод из одного клика.

Использовать совокупность:

```text
user language
application context
recent files
recent missions
sequence of actions
memory
```

Confidence обязателен.

Пример:

```json
{
  "goal": "prepare product photos for catalog",
  "confidence": 0.87
}
```

Если confidence низкий — не вмешиваться.

---

# 5. FRICTION DETECTION

JARVIS должен определять, когда пользователь испытывает затруднение.

Сигналы:

```text
same operation repeated
same dialog reopened
same error repeated
undo/redo loops
repeated failed actions
rapid application switching
searching same topic repeatedly
long pause inside task
manual workaround after failed JARVIS action
```

Создать:

```text
FrictionDetector
```

Результат:

```json
{
  "type": "repeated_failure",
  "confidence": 0.91,
  "context": "...",
  "possible_help": "..."
}
```

Не использовать псевдопсихологию вроде:

> быстро печатает = злится

Без достаточных данных не определять эмоцию.

---

# 6. WORKFLOW DISCOVERY

Создать:

```text
WorkflowLearner
```

Он выявляет повторяющиеся последовательности действий.

Пример:

```text
open Downloads
→ select newest Excel
→ copy to project
→ rename
→ open
→ export PDF
→ move PDF
```

После нескольких повторений появляется candidate workflow.

Не хардкодить количество повторений.

Оценивать:

```text
frequency
similarity
time_saved
reliability
risk
```

---

# 7. WORKFLOW → CAPABILITY

WorkflowLearner интегрировать с Sprint 9 Capability Engine.

Если последовательность стабильна:

```text
observed workflow
→ generalized workflow
→ CapabilityPlanner
→ sandbox/rehearsal
→ verification
→ learned capability
```

Не хранить тупые coordinate macros.

Хранить semantic actions.

---

# 8. PROACTIVE DECISION ENGINE

Создать:

```text
ProactiveDecisionEngine
```

Это не набор:

```python
if youtube > 2h:
```

Он получает context candidates и принимает решение:

```text
SILENT
PREPARE
SUGGEST
ACT
ASK
WARN
```

---

# 9. SILENT

Большинство времени:

```text
SILENT
```

Это нормальное состояние.

JARVIS не обязан что-то говорить только потому, что заметил паттерн.

---

# 10. PREPARE

Очень важный режим.

Если JARVIS видит вероятную будущую потребность:

```text
PREPARE
```

Он может безопасно:

- исследовать;
- построить план;
- найти документацию;
- подготовить capability;
- sandbox-test;
- добавить Shadow backlog;
- подготовить workflow.

Но не менять пользовательские данные без необходимости.

Это реализует:

> пользователь смотрит фильм, JARVIS тем временем учится.

---

# 11. SUGGEST

Если JARVIS видит очевидную помощь:

> «Сэр, вы уже несколько раз повторили эту последовательность. Хотите, я автоматизирую?»

Коротко.

Без лекций.

Если пользователь:

> «Да.»

JARVIS начинает mission.

---

# 12. ACT

Автоматически действовать можно только когда:

```text
risk LOW
confidence HIGH
user preference allows autonomy
action is reversible
context is clear
```

Пример:

- подготовить копию;
- организовать temporary workspace;
- собрать информацию;
- продолжить ранее одобренную automation.

Не спрашивать разрешение повторно для уже явно разрешённого класса действий.

---

# 13. ASK

Для:

```text
MEDIUM/HIGH ambiguity
missing information
password
2FA
meaningful external side effect
```

задавать один конкретный вопрос.

Не устраивать wizard.

---

# 14. WARN

Использовать только для действительно значимого риска:

- phishing;
- suspicious executable;
- destructive action;
- failing disk indicators if available;
- dangerous configuration.

Не превращать JARVIS в антивирус с постоянными уведомлениями.

---

# 15. ATTENTION BUDGET

Создать:

```text
AttentionManager
```

JARVIS должен понимать:

> Можно ли сейчас вообще отвлекать человека?

Факторы:

```text
fullscreen application
game
movie/video
meeting
recent JARVIS interruption
typing activity
active mission
Do Not Disturb
user preference
urgency
```

---

# 16. INTERRUPTION LEVELS

```text
NONE
PASSIVE
NORMAL
IMPORTANT
URGENT
```

Большинство proactive событий:

```text
PASSIVE
```

Например tray state меняется, но голоса нет.

---

# 17. NO-SPAM POLICY

Добавить глобальные ограничения:

- не повторять одно предложение;
- учитывать отказ;
- учитывать ignore;
- adaptive cooldown;
- не вмешиваться посреди активного общения;
- не повторять dismissed topic.

JARVIS должен научиться:

```text
пользователь не любит такие напоминания
```

и уменьшить их.

---

# 18. PROACTIVE MEMORY

Сохранять:

```text
suggestion
accepted?
ignored?
rejected?
outcome
useful?
```

Использовать это для будущей политики.

---

# 19. USER AUTONOMY PROFILE

Создать настройки:

```text
observer
assistant
partner
autonomous
```

### observer

JARVIS почти никогда сам не действует.

### assistant

Предлагает, но ждёт подтверждения.

### partner

LOW-risk reversible задачи может выполнять сам.

### autonomous

Максимальная автономность в рамках Risk Gate.

Default:

```text
assistant
```

Не менять default без пользователя.

---

# 20. USER-SPECIFIC LEARNING

JARVIS должен постепенно понимать:

```text
какие предложения пользователь принимает
какие игнорирует
какие задачи делегирует
какие предпочитает делать сам
```

Это влияет на ProactiveDecisionEngine.

---

# 21. NOVICE COMPUTER MODE

Очень важная часть проекта.

Создать:

```text
ComputerAssistanceProfile
```

Пользователь может быть:

```text
beginner
normal
advanced
developer
```

Это НЕ интеллект пользователя.

Это уровень компьютерной помощи.

---

# 22. BEGINNER BEHAVIOR

Если пользователь не умеет пользоваться ПК:

не говорить:

> «Откройте regedit и измените DWORD».

JARVIS:

> «Я сам настрою. Когда понадобится ваше действие — скажу.»

Если нужен ввод:

> «Windows просит пароль. Введите его здесь, дальше я продолжу.»

---

# 23. ADVANCED / DEVELOPER

Продвинутому пользователю JARVIS может:

- показывать commands;
- давать technical trace;
- объяснять provider;
- позволять быстрее подтверждать действия.

---

# 24. CONTEXTUAL HELP

Если beginner застрял в интерфейсе:

JARVIS может использовать Sprint 10 AppExplorer.

Например:

> «Где здесь сохранить?»

JARVIS:

- inspect current app;
- находит Save;
- при возможности выполняет;
- либо кратко указывает элемент.

Не выдавать абстрактную инструкцию, если может сделать сам.

---

# 25. LONG-RUNNING MISSIONS

Использовать существующий persistent Mission Runtime.

JARVIS может заниматься задачей, пока пользователь делает другое.

Пример:

```text
research software
download
process files
prepare capability
```

Mission должна:

- pause;
- resume;
- survive UI close;
- survive temporary provider errors.

---

# 26. BACKGROUND RESOURCE MANAGER

Создать:

```text
BackgroundBudgetManager
```

Shadow/Proactive learning не должен мешать пользователю.

Учитывать:

```text
CPU
RAM
foreground latency
gaming/fullscreen
active TTS
active user mission
battery if laptop
```

При высокой нагрузке:

```text
pause shadow work
```

---

# 27. SHADOW BACKLOG PRIORITY

Shadow backlog должен ранжироваться:

```text
user pain
frequency
expected time saved
probability of reuse
risk
cost of learning
```

Не генерировать бесполезные способности.

---

# 28. SELF-IMPROVEMENT QUALITY LOOP

После использования learned capability:

```text
execute
→ verify
→ measure
→ record
```

Если capability:

- часто repair;
- медленная;
- ломается;
- требует fallback;

добавить optimization task в Shadow backlog.

---

# 29. SESSION SUMMARY

Не показывать автоматически.

Но internally по завершению activity episode формировать компактный summary:

```text
goal
important events
unfinished work
learned workflows
problems
```

Использовать как память следующей сессии.

---

# 30. RETURN CONTEXT

После возвращения пользователя JARVIS может восстановить контекст.

Например:

> «Продолжим каталог? Вчера остановились на экспорте изображений.»

Только если confidence высокий и это уместно.

Не говорить это при каждом запуске.

---

# 31. USER CAN ASK

Поддержать естественные вопросы:

```text
что я сейчас делал?
на чем мы остановились?
что ты заметил?
чему ты научился?
что ты делал пока меня не было?
```

Отвечать из structured context/action traces.

Не выдумывать.

---

# 32. PRIVACY

LivingContext не должен превращаться в spyware.

Default:

- не сохранять screenshot stream;
- не сохранять keystrokes;
- не сохранять passwords;
- не сохранять private fields;
- не отправлять context в cloud без policy;
- хранить только необходимое structured context.

Sensitive app/window filtering должен существовать.

---

# 33. PROACTIVE SAFETY

Proactive action проходит тот же:

```text
Risk Gate
Capability verification
Checkpoint
Rollback
```

что обычная пользовательская mission.

Proactive mode НЕ имеет дополнительных прав.

---

# 34. NEVER FAKE PROACTIVITY

JARVIS не должен генерировать случайную реплику:

> «Я заметил...»

если соответствующего наблюдения не было.

Каждая proactive реплика должна иметь structured evidence.

---

# 35. LIVE TEST — REPEATED WORKFLOW

Создать безопасную локальную последовательность:

```text
files arrive
→ user manually organizes
→ repeats
```

Проверить:

1. LivingContext видит действия.
2. WorkflowLearner обнаруживает pattern.
3. ProactiveDecisionEngine предлагает automation.
4. Пользователь mock-accept.
5. Capability создаётся.
6. Следующая последовательность выполняется автоматически.
7. Desired state verify.

---

# 36. LIVE TEST — USER BUSY

Открыть fullscreen/video-like fixture.

Создать proactive candidate.

Ожидание:

```text
AttentionManager → do not interrupt
```

После выхода:

предложение может появиться, если ещё актуально.

---

# 37. LIVE TEST — BEGINNER

Симулировать:

> «Я скачал программу, не понимаю, как её установить.»

JARVIS должен использовать Sprint 10 capabilities.

Не выдавать длинную инструкцию.

Он должен выполнить безопасные части сам.

---

# 38. LIVE TEST — SHADOW PREPARE

Создать незакрытую безопасную проблему.

Пользователь становится busy.

Shadow Engine должен:

```text
research
prepare
sandbox
```

без foreground interruption.

После окончания:

capability готова.

---

# 39. TESTS

Добавить минимум:

- LivingContext update;
- episode segmentation;
- goal inference confidence;
- friction detection;
- workflow discovery;
- workflow generalization;
- proactive SILENT;
- PREPARE;
- SUGGEST;
- ACT policy;
- AttentionManager;
- fullscreen suppression;
- ignore learning;
- autonomy profile;
- beginner behavior;
- background budget;
- Shadow backlog priority;
- proactive Risk Gate;
- evidence-required proactive output;
- session summary;
- return context;
- Sprint 10 regression;
- Capability Engine regression;
- Voice regression.

---

# 40. BASELINE / REGRESSION

Зафиксировать baseline:

```text
243 passed
2 skipped
0 failed
```

Затем:

- targeted tests;
- full pytest;
- compileall;
- git diff --check;
- frontend build только если frontend пришлось менять;
- реальный safe smoke.

Не скрывать failures.

---

# FINAL REPORT

Показать кратко:

1. Changed files.
2. Living Context architecture.
3. Goal/Friction inference.
4. Workflow learning.
5. Proactive Decision Engine.
6. Attention Manager.
7. Autonomy profiles.
8. Beginner assistance.
9. Shadow integration.
10. Real safe proactive demo.
11. Tests before/after.
12. Known limitations.
13. Rollback.

---

# CRITICAL

Не начинать Sprint 12.

Не делать UI redesign.

Не добавлять LLM-модели.

Не строить proactivity на наборе жёстких if-rules.

Не записывать raw keystrokes.

Не хранить continuous screenshots.

Не обходить Risk Gate.

Не выполнять HIGH/CRITICAL proactive actions.

Не спамить пользователя.

Главная проверка:

> Может ли JARVIS теперь самостоятельно понять, что пользователь делает, заметить полезную возможность помочь, выбрать правильный момент, подготовить или выполнить помощь и научиться на результате — не превращаясь в раздражающий набор уведомлений?

Если нет — Sprint 11 не завершён.