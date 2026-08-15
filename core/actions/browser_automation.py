"""Browser automation — инструмент Джарвиса в стиле Browser Use.

Реализует управление браузером как РЕАЛЬНЫЙ инструмент (не dry-run):

- открыть URL;
- получить пронумерованный список интерактивных элементов страницы
  (ссылки, кнопки, поля ввода) — как у Browser Use, по номеру, а не по
  пиксельным координатам;
- кликнуть по элементу по номеру;
- ввести текст в поле по номеру;
- прочитать текстовое содержимое страницы/элемента;
- корректно закрыть/освободить ресурсы браузера.

БЕЗОПАСНОСТЬ (по таксономии P1 §2.2):
Инструмент УМЕЕТ различать "просто клик по ссылке" и "клик по кнопке
типа submit/pay/send". Для опасных элементов он выставляет флаг
``requires_confirmation`` и НЕ выполняет действие без явного флага
``confirm=True`` на вызове. Сам инструмент не решает, продолжать или нет —
он только СИГНАЛИЗИРУЕТ наружу, чтобы вызывающий код (agent.py, P2-сессия)
мог подключить confirmation-flow позже.

Браузерный движок — Playwright (единственная зависимость для браузерной
автоматизации; ни Playwright, ни Selenium ранее в проекте не было).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from core.actions.base import ActionResult, Tool, ToolContext
from core.actions.registry import DEFAULT_REGISTRY
from core.utils.logger import get_logger

__all__ = [
    "BrowserAutomationError",
    "BrowserAutomationEngine",
    "BrowserAutomationTool",
]

log = get_logger(__name__)


class BrowserAutomationError(Exception):
    """Ошибка движка browser-automation (ожидаемая, не фатальная)."""


# Селектор интерактивных элементов (Browser Use style). Тот же селектор
# используется и для JS-перечисления, и для Playwright locator.nth(idx),
# поэтому нумерация в листинге и при действии совпадает (документный порядок).
_INTERACTIVE_SELECTOR = (
    "a, button, input:not([type=hidden]), textarea, select, "
    "[role='button'], [role='link'], [contenteditable='true']"
)

# Аргументы запуска chromium (headless/CI должны работать без sandbox).
_LAUNCH_ARGS = ["--no-sandbox", "--disable-dev-shm-usage"]

# Ключевые слова, по которым элемент считается HIGH-risk (требует
# подтверждения). Проверяются в text/id/name/aria-label/title/value.
_RISKY_WORDS = [
    "submit", "send", "pay", "payment", "checkout", "buy", "order",
    "purchase", "confirm", "place order", "donate", "login", "signin",
    "sign in", "subscribe", "complete purchase", "make payment",
    "transfer", "check out",
]


# JS, выполняемый в контексте страницы: обходит интерактивные элементы
# в документном порядке и возвращает метаданные + requires_confirmation.
_ELEMENTS_JS = """(selector) => {
  const els = Array.from(document.querySelectorAll(selector));
  const RISKY = %s;
  const norm = (s) => (s || '').toLowerCase();
  function classify(el) {
    const tag = el.tagName.toLowerCase();
    const type = norm(el.getAttribute('type') || el.type);
    const txt = norm(el.innerText || el.value || '');
    const id = norm(el.id);
    const name = norm(el.getAttribute('name'));
    const aria = norm(el.getAttribute('aria-label'));
    const title = norm(el.getAttribute('title'));
    const val = norm(el.getAttribute('value'));
    let risky = false;
    if ((tag === 'button' || tag === 'input') &&
        (type === 'submit' || type === 'image')) risky = true;
    const hay = [txt, id, name, aria, title, val].join('  ');
    if (RISKY.some((w) => hay.indexOf(w) !== -1)) risky = true;
    return risky;
  }
  function isVisible(el) {
    try {
      return !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
    } catch (e) { return true; }
  }
  return els.map((el, i) => {
    const tag = el.tagName.toLowerCase();
    const isField = (tag === 'input' || tag === 'textarea');
    let text = isField ? (el.value || '') : (el.innerText || '');
    if (text.length > 200) text = text.slice(0, 200);
    return {
      index: i,
      tag: tag,
      id: el.id || null,
      name: el.getAttribute('name') || null,
      type: el.getAttribute('type') || (isField ? (el.type || null) : null),
      text: text.trim(),
      value: isField ? (el.value || '') : null,
      href: (tag === 'a') ? (el.getAttribute('href') || null) : null,
      role: el.getAttribute('role') || null,
      aria_label: el.getAttribute('aria-label') || null,
      placeholder: el.getAttribute('placeholder') || null,
      disabled: el.disabled === true,
      visible: isVisible(el),
      requires_confirmation: classify(el),
    };
  });
}""" % (str(_RISKY_WORDS),)


class BrowserAutomationEngine:
    """Низкоуровневый движок управления браузером (Playwright, sync API).

    Состояние: браузер + контекст + страница. ``close()`` идемпотентна и
    гарантированно освобождает все ресурсы (страница → контекст → браузер →
    playwright), поэтому повторное ``open()`` после ``close()`` всегда работает
    и не оставляет висящих процессов.

    Нумерация элементов действительна до существенного изменения страницы
    (навигация/перерисовка DOM). После таких изменений клиент обязан заново
    вызвать ``list_elements()``.
    """

    def __init__(self, user_data_dir: Optional[str] = None, headless: bool = True) -> None:
        self._selector = _INTERACTIVE_SELECTOR
        self._user_data_dir = user_data_dir
        self._headless = headless
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None

    # --- жизненный цикл --------------------------------------------------- #
    def open(self, url: str, timeout: int = 30000) -> Dict[str, Any]:
        """Открывает URL в новом контексте. Сбрасывает предыдущую сессию."""
        self.close()
        try:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            if self._user_data_dir:
                # Постоянный контекст: куки/сессии сохраняются в user_data_dir
                # (он в .gitignore, см. требования безопасности спринта).
                self._context = self._pw.chromium.launch_persistent_context(
                    self._user_data_dir, headless=self._headless, args=_LAUNCH_ARGS
                )
                self._page = (
                    self._context.pages[0]
                    if self._context.pages
                    else self._context.new_page()
                )
            else:
                # Эфемерный контекст — ничего не пишется на диск.
                self._browser = self._pw.chromium.launch(headless=self._headless, args=_LAUNCH_ARGS)
                self._context = self._browser.new_context()
                self._page = self._context.new_page()
            self._page.goto(url, wait_until="load", timeout=timeout)
        except Exception as exc:  # любая ошибка запуска — чистый сброс
            self.close()
            raise BrowserAutomationError(
                f"Не удалось открыть {url}: {type(exc).__name__}: {exc}"
            )
        return {"ok": True, "url": self._page.url, "title": self._page.title()}

    def _require_page(self) -> None:
        if self._page is None:
            raise BrowserAutomationError("Браузер не открыт (вызовите open() первым)")

    def close(self) -> Dict[str, Any]:
        """Идемпотентное закрытие всех ресурсов. Безопасно вызывать повторно."""
        warning: Optional[str] = None
        try:
            if self._page is not None:
                self._page.close()
        except Exception as exc:  # pragma: no cover - защита от утечек
            warning = warning or str(exc)
        try:
            if self._context is not None:
                self._context.close()
        except Exception as exc:  # pragma: no cover
            warning = warning or str(exc)
        try:
            if self._browser is not None:
                self._browser.close()
        except Exception as exc:  # pragma: no cover
            warning = warning or str(exc)
        try:
            if self._pw is not None:
                self._pw.stop()
        except Exception as exc:  # pragma: no cover
            warning = warning or str(exc)
        self._page = None
        self._context = None
        self._browser = None
        self._pw = None
        return {"ok": True, "closed": True, "warning": warning}

    def __enter__(self) -> "BrowserAutomationEngine":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # --- интроспекция ---------------------------------------------------- #
    def list_elements(self) -> List[Dict[str, Any]]:
        """Возвращает пронумерованный список интерактивных элементов.

        Каждый элемент: index, tag, id, name, type, text, value, href, role,
        aria_label, placeholder, disabled, visible, requires_confirmation.
        """
        self._require_page()
        try:
            data = self._page.evaluate(_ELEMENTS_JS, self._selector)
        except Exception as exc:
            raise BrowserAutomationError(f"Ошибка перечисления элементов: {exc}")
        return list(data)

    def _locator(self, index: int):
        self._require_page()
        return self._page.locator(self._selector).nth(index)

    def _classify_index(self, index: int, els: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(index, int) or isinstance(index, bool):
            raise BrowserAutomationError(f"Номер элемента должен быть int, получено: {index!r}")
        if index < 0 or index >= len(els):
            return {"ok": False, "error": f"Элемент с номером {index} не существует", "index": index}
        return {"ok": True, "element": els[index]}

    # --- действия -------------------------------------------------------- #
    def click(self, index: int, confirm: bool = False, timeout: int = 15000) -> Dict[str, Any]:
        """Клик по элементу по номеру.

        Если элемент помечен как requires_confirmation и confirm != True —
        возвращает requires_confirmation=True, action_taken=False и НЕ кликает.
        Иначе выполняет реальный клик.
        """
        els = self.list_elements()
        check = self._classify_index(index, els)
        if not check["ok"]:
            return check
        element = check["element"]
        requires = bool(element["requires_confirmation"])
        if requires and not confirm:
            return {
                "ok": True,
                "requires_confirmation": True,
                "action_taken": False,
                "index": index,
                "element": element,
                "reason": "Действие требует подтверждения (submit/pay/send). Передайте confirm=True.",
            }
        try:
            # no_wait_after: не ждём навигации — страница может измениться,
            # но при подтверждённом клике мы не блокируемся на ожидании загрузки.
            self._locator(index).click(timeout=timeout, no_wait_after=True)
        except Exception as exc:
            raise BrowserAutomationError(
                f"Ошибка клика по элементу #{index}: {type(exc).__name__}: {exc}"
            )
        return {"ok": True, "requires_confirmation": requires, "action_taken": True, "index": index}

    def type_text(self, index: int, text: str, timeout: int = 15000) -> Dict[str, Any]:
        """Ввод текста в поле по номеру (заменяет значение)."""
        els = self.list_elements()
        check = self._classify_index(index, els)
        if not check["ok"]:
            return check
        element = check["element"]
        if element["disabled"]:
            return {"ok": False, "error": f"Элемент #{index} отключён (disabled)", "index": index}
        try:
            self._locator(index).fill(text, timeout=timeout)
        except Exception as exc:
            raise BrowserAutomationError(
                f"Ошибка ввода в элемент #{index}: {type(exc).__name__}: {exc}"
            )
        return {"ok": True, "index": index, "text": text}

    def read(self, index: Optional[int] = None, max_length: int = 8000) -> Dict[str, Any]:
        """Чтение текста страницы (index=None) или конкретного элемента.

        Для input/textarea дополнительно возвращает реальное value поля.
        """
        self._require_page()
        if index is None:
            try:
                text = self._page.inner_text("body")
            except Exception as exc:
                raise BrowserAutomationError(f"Ошибка чтения страницы: {exc}")
            if max_length and len(text) > max_length:
                text = text[:max_length] + "…[обрезано]"
            return {"ok": True, "text": text}

        els = self.list_elements()
        check = self._classify_index(index, els)
        if not check["ok"]:
            return check
        element = check["element"]
        tag = element["tag"]
        try:
            if tag in ("input", "textarea"):
                value = self._locator(index).input_value()
                return {"ok": True, "index": index, "text": value, "value": value}
            text = self._locator(index).inner_text()
        except Exception as exc:
            raise BrowserAutomationError(
                f"Ошибка чтения элемента #{index}: {type(exc).__name__}: {exc}"
            )
        return {"ok": True, "index": index, "text": text, "value": None}


# --------------------------------------------------------------------------- #
# Tool-обёртка для реестра core.actions
# --------------------------------------------------------------------------- #
class BrowserAutomationTool(Tool):
    """Инструмент: управление браузером (Browser Use style).

    Единый инструмент с под-действием ``action``:
      open  — {url}
      list  — (без аргументов)
      click — {index, confirm?}
      type  — {index, text}
      read  — {index?}
      close — (без аргументов)

    Состояние браузера хранится в экземпляре инструмента (stateful session).
    """

    def __init__(self) -> None:
        self._engine: Optional[BrowserAutomationEngine] = None
        self._user_data_dir: Optional[str] = None

    def _get_engine(self) -> BrowserAutomationEngine:
        if self._engine is None:
            self._engine = BrowserAutomationEngine(
                user_data_dir=self._user_data_dir, headless=True
            )
        return self._engine

    @property
    def name(self) -> str:
        return "browser_automation"

    @property
    def description(self) -> str:
        return (
            "Управление браузером (Browser Use style): открывает URL, возвращает "
            "пронумерованный список интерактивных элементов страницы (ссылки, "
            "кнопки, поля), кликает/вводит по номеру элемента, читает текст. "
            "Опасные элементы (submit/pay/send) помечаются requires_confirmation "
            "и не срабатывают без confirm=true. Действия: open(url), list(), "
            "click(index, confirm?), type(index, text), read(index?), close()."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["open", "list", "click", "type", "read", "close"],
                    "description": "Под-действие инструмента.",
                },
                "url": {"type": "string", "description": "URL для open."},
                "index": {
                    "type": "integer",
                    "description": "Номер интерактивного элемента (из list).",
                },
                "text": {"type": "string", "description": "Текст для type."},
                "confirm": {
                    "type": "boolean",
                    "default": False,
                    "description": "Подтверждение опасного действия (submit/pay/send).",
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        }

    def run(self, args: Dict[str, Any], context: ToolContext) -> ActionResult:
        action = args.get("action")
        engine = self._get_engine()
        try:
            if action == "open":
                if not args.get("url"):
                    return ActionResult(tool=self.name, args=args, ok=False, error="open требует url")
                result = engine.open(args["url"])
            elif action == "list":
                result = engine.list_elements()
            elif action == "click":
                result = engine.click(int(args["index"]), confirm=bool(args.get("confirm", False)))
            elif action == "type":
                if "text" not in args:
                    return ActionResult(tool=self.name, args=args, ok=False, error="type требует text")
                result = engine.type_text(int(args["index"]), args["text"])
            elif action == "read":
                idx = args.get("index")
                result = engine.read(None if idx is None else int(idx))
            elif action == "close":
                result = engine.close()
            else:
                return ActionResult(
                    tool=self.name, args=args, ok=False, error=f"Неизвестное действие: {action}"
                )
        except BrowserAutomationError as exc:
            return ActionResult(tool=self.name, args=args, ok=False, error=str(exc))
        except Exception as exc:
            return ActionResult(
                tool=self.name, args=args, ok=False, error=f"{type(exc).__name__}: {exc}"
            )
        # Маппинг результата движка -> ActionResult
        ok = bool(result.get("ok", True)) if isinstance(result, dict) else True
        return ActionResult(
            tool=self.name,
            args=args,
            ok=ok,
            output=result,
            error=result.get("error") if isinstance(result, dict) else None,
        )


# Авто-регистрация в реестре инструментов Джарвиса.
DEFAULT_REGISTRY.register(BrowserAutomationTool())
