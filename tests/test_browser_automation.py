"""Тесты инструмента browser_automation (SPRINT P2-B).

Проверяют ВСЕ обязательные сценарии на локальной HTML-странице,
сгенерированной в pytest tmp_path (фикстура не коммитится):

1. open + list: элементы найдены, пронумерованы с 0, поля присутствуют.
2. обычный клик (не submit): выполняется БЕЗ requires_confirmation.
3. клик по submit/pay-like БЕЗ confirm: requires_confirmation=True,
   реального клика НЕ происходит; С confirm=True — выполняется.
4. ввод текста: значение поля реально изменилось (проверка чтением).
5. некорректный номер: аккуратная ошибка, без краша.
6. close + reopen: ресурс освобождён, повторное открытие работает.
7. регистрация Tool в реестре core.actions.

Браузерные бинарники (chromium) должны быть установлены:
    python -m playwright install chromium
Если их нет — тесты упадут ЯВНО (без тихого skip), это блокер среды.
"""

from __future__ import annotations

import os
import sys

import pytest

# Гарантируем воспроизводимость: корень проекта в sys.path.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core.actions.browser_automation import (  # noqa: E402
    BrowserAutomationEngine,
    BrowserAutomationError,
    BrowserAutomationTool,
)
from core.actions.base import ToolContext  # noqa: E402
from core.actions.registry import DEFAULT_REGISTRY  # noqa: E402

# Безопасная тестовая страница: форма НЕ отправляется (onsubmit false),
# клики помечаются в #out, чтобы детектить реальное срабатывание.
_HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>JARVIS Browser Test</title></head>
<body>
  <h1>Test Page</h1>
  <a id="link1" href="#next">Regular link</a>
  <button id="btn1" type="button"
          onclick="document.getElementById('out').textContent='plain clicked'">
    Regular button
  </button>
  <form id="frm" onsubmit="return false">
    <label>Name: <input id="name" type="text" placeholder="Your name" /></label>
    <button id="submit" type="submit"
            onclick="document.getElementById('out').textContent='submit clicked'">
      Submit
    </button>
  </form>
  <button id="pay" type="button"
          onclick="document.getElementById('out').textContent='pay clicked'">
    Pay now
  </button>
  <a id="paylink" href="#" onclick="return false">Pay invoice</a>
  <div id="out"></div>
</body>
</html>"""


@pytest.fixture
def page_url(tmp_path):
    """Локальная тестовая HTML, открытая через file:// (без коммита фикстуры)."""
    p = tmp_path / "test_page.html"
    p.write_text(_HTML, encoding="utf-8")
    return p.as_uri()


# --------------------------------------------------------------------------- #
def test_open_and_list_elements(page_url):
    with BrowserAutomationEngine(headless=True) as eng:
        eng.open(page_url)
        els = eng.list_elements()
        assert isinstance(els, list)
        assert len(els) >= 5, f"ожидалось >=5 элементов, найдено {len(els)}"
        # нумерация последовательная с 0
        assert [e["index"] for e in els] == list(range(len(els)))
        # обязательные поля присутствуют
        for e in els:
            for k in ("index", "tag", "text", "requires_confirmation", "visible"):
                assert k in e
        # submit и pay помечены как risky уже в листинге
        sub = next(e for e in els if e["id"] == "submit")
        pay = next(e for e in els if e["id"] == "pay")
        assert sub["requires_confirmation"] is True
        assert pay["requires_confirmation"] is True


def test_normal_click_no_confirmation(page_url):
    with BrowserAutomationEngine(headless=True) as eng:
        eng.open(page_url)
        els = eng.list_elements()
        btn = next(e for e in els if e["id"] == "btn1")
        res = eng.click(btn["index"])
        assert res["ok"] is True
        assert res["action_taken"] is True
        assert res["requires_confirmation"] is False
        # реальный клик изменил DOM
        assert "plain clicked" in eng.read()["text"]


def test_submit_click_requires_confirmation(page_url):
    with BrowserAutomationEngine(headless=True) as eng:
        eng.open(page_url)
        els = eng.list_elements()
        sub = next(e for e in els if e["id"] == "submit")
        assert sub["requires_confirmation"] is True

        # БЕЗ confirm — сигнал о необходимости подтверждения, клика НЕТ
        res = eng.click(sub["index"])
        assert res["ok"] is True
        assert res["requires_confirmation"] is True
        assert res["action_taken"] is False
        assert "submit clicked" not in eng.read()["text"]

        # С confirm=True — реальный клик выполняется
        res2 = eng.click(sub["index"], confirm=True)
        assert res2["action_taken"] is True
        assert "submit clicked" in eng.read()["text"]


def test_type_text_changes_value(page_url):
    with BrowserAutomationEngine(headless=True) as eng:
        eng.open(page_url)
        els = eng.list_elements()
        fld = next(e for e in els if e["id"] == "name")
        res = eng.type_text(fld["index"], "Alice")
        assert res["ok"] is True
        # чтение значения поля (value, а не textContent body)
        val = eng.read(fld["index"])
        assert val["ok"] is True
        assert val["value"] == "Alice"
        # значение реально изменилось — повторное чтение подтверждает
        assert eng.read(fld["index"])["value"] == "Alice"


def test_invalid_index_graceful(page_url):
    with BrowserAutomationEngine(headless=True) as eng:
        eng.open(page_url)
        els = eng.list_elements()
        bad = len(els) + 100
        res = eng.click(bad)
        assert res["ok"] is False
        assert "не существует" in res["error"]
        # и при вводе — тоже аккуратная ошибка, без краша
        res2 = eng.type_text(bad, "x")
        assert res2["ok"] is False


def test_close_then_reopen(page_url):
    eng = BrowserAutomationEngine(headless=True)
    try:
        eng.open(page_url)
        assert len(eng.list_elements()) >= 5
        # закрытие освобождает ресурс (внутренние хэндлы сброшены)
        assert eng.close()["ok"] is True
        assert eng._page is None
        # повторное закрытие идемпотентно не падает
        eng.close()
        # повторное открытие работает — ресурсы не утекли
        eng.open(page_url)
        assert len(eng.list_elements()) >= 5
    finally:
        eng.close()


def test_engine_requires_open_before_action():
    eng = BrowserAutomationEngine(headless=True)
    try:
        # действие до open — аккуратная ошибка, не краш
        with pytest.raises(BrowserAutomationError):
            eng.list_elements()
    finally:
        eng.close()


def test_tool_registered_and_end_to_end(page_url):
    # инструмент зарегистрирован в реестре core.actions
    assert "browser_automation" in DEFAULT_REGISTRY
    tool = DEFAULT_REGISTRY.get("browser_automation")
    assert isinstance(tool, BrowserAutomationTool)

    ctx = ToolContext()
    r1 = tool.run({"action": "open", "url": page_url}, ctx)
    assert r1.ok is True
    r2 = tool.run({"action": "list"}, ctx)
    assert r2.ok is True
    assert isinstance(r2.output, list) and len(r2.output) >= 5
    # submit-клик через Tool без confirm — requires_confirmation, без клика
    els = r2.output
    sub = next(e for e in els if e["id"] == "submit")
    r3 = tool.run({"action": "click", "index": sub["index"]}, ctx)
    assert r3.ok is True
    assert r3.output["requires_confirmation"] is True
    assert r3.output["action_taken"] is False
    r4 = tool.run({"action": "close"}, ctx)
    assert r4.ok is True
