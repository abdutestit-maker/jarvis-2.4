# Browser Automation — инструмент JARVIS (SPRINT P2-B)

Реальный инструмент управления браузером в стиле **Browser Use**:
модель получает пронумерованный список интерактивных элементов страницы
и выбирает действие по **номеру**, а не по пиксельным координатам. Это
надёжнее, чем screenshot-driven clicking.

Модуль: `core/actions/browser_automation.py`
Регистрация: `browser_automation` в `DEFAULT_REGISTRY` (`core/actions/`).

## Движок

Используется **Playwright** (sync API). Ни Playwright, ни Selenium ранее в
проекте не было — добавлена единственная зависимость `playwright>=1.45`
(см. `requirements.txt` / `pyproject.toml`). После установки пакета:
`python -m playwright install chromium`.

Архитектура:
- `BrowserAutomationEngine` — низкоуровневое ядро (открытие/закрытие/
  перечисление/клик/ввод/чтение). Тестируется напрямую.
- `BrowserAutomationTool(Tool)` — обёртка для реестра `core.actions`,
  единый инструмент с под-действием `action`.

## API движка

| Метод | Назначение |
|-------|-----------|
| `open(url, timeout=30000)` | Открыть URL в новом контексте. Сбрасывает предыдущую сессию. |
| `list_elements()` | Пронумерованный список интерактивных элементов (индекс с 0). |
| `click(index, confirm=False, timeout=15000)` | Клик по элементу по номеру. |
| `type_text(index, text, timeout=15000)` | Ввод текста в поле по номеру (заменяет значение, `fill`). |
| `read(index=None, max_length=8000)` | Чтение текста страницы или конкретного элемента. |
| `close()` | Идемпотентное закрытие всех ресурсов. |

Интерактивные элементы (один селектор для листинга и для действия, поэтому
нумерация совпадает — документный порядок):
`a, button, input:not([type=hidden]), textarea, select, [role=button],
[role=link], [contenteditable=true]`.

`close()` закрывает page → context → browser → playwright и сбрасывает
внутренние хэндлы. Безопасно вызывать повторно; после `close()` повторный
`open()` всегда работает (нет висящих процессов).

## Нумерация элементов

Номер (`index`) действителен до существенного изменения страницы
(навигация/перерисовка DOM). После таких изменений клиент обязан заново
вызвать `list_elements()`. Номер вычисляется заново при каждом действии
через `locator(selector).nth(index)` — никакие хэндлы не хранятся между
вызовами, поэтому устаревшие ссылки DOM не возможны.

## Контракт безопасности: `requires_confirmation`

Инструмент **НЕ решает сам**, выполнять опасное действие или нет. Он
**сигнализирует** наружу (вызывающий код — `agent.py`, P2-сессия — позже
подключит confirmation-flow).

Элемент помечается `requires_confirmation = True`, если:
- `tag == "button"` или `tag == "input"`, и `type` в
  `{submit, image}`;
- в `text`/`id`/`name`/`aria-label`/`title`/`value` встречается одно из
  ключевых слов: `submit, send, pay, payment, checkout, buy, order,
  purchase, confirm, place order, donate, login, signin, subscribe,
  complete purchase, make payment, transfer, check out`.

Флаг присутствует:
1. в каждом элементе из `list_elements()` (превью для модели);
2. в результате `click()`.

Поведение `click(index, confirm=False)`:
1. Элемент повторно классифицируется по актуальному DOM.
2. Если `requires_confirmation` и `confirm != True` → возвращается
   `{"ok": True, "requires_confirmation": True, "action_taken": False,
   "reason": "..."}` и **реальный клик НЕ происходит**.
3. Если `confirm=True` → клик выполняется,
   `action_taken: True`.

Обычная ссылка/кнопка кликается без запроса подтверждения.

## Безопасность в тестах и эксплуатации

- Никаких реальных платёжных форм, логинов в реальные аккаунты, отправки
  реальных писем/сообщений. Тесты используют только локальную HTML-страницу
  в `tmp_path` (через `file://`).
- `user-data-dir` браузера (куки/сессии) не коммитится — добавлена строка
  `browser-user-data/` в `.gitignore`.
- По умолчанию используется эфемерный контекст (`launch` + `new_context`),
  который ничего не пишет на диск; постоянный профиль (`user_data_dir`)
  опционален и изолируется `.gitignore`.

## Тесты

`tests/test_browser_automation.py` — только этот файл прогоняется при
приёмке (`pytest tests/test_browser_automation.py -v`). Покрывает:

1. `open` + `list_elements`: элементы найдены, пронумерованы с 0, поля
   присутствуют; `submit`/`pay` уже помечены `requires_confirmation`.
2. Обычный клик: выполняется, `requires_confirmation=False`.
3. Клик по submit/pay **без** `confirm`: `requires_confirmation=True`,
   реального клика НЕТ; **с** `confirm=True` — выполняется.
4. Ввод текста: значение поля реально изменилось (проверка чтением `value`).
5. Некорректный номер: аккуратная ошибка `ok=False`, без краша.
6. `close` + reopen: ресурс освобождён, повторное открытие работает.
7. Регистрация Tool в реестре `core.actions`.

Тестовая HTML предотвращает реальную отправку формы (`onsubmit="return false"`)
и помечает клики в `#out` для детекции фактического срабатывания.
