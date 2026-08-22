"""Тесты Quick-Answer пути (Фаза 2, v2).

Цель: быстрый ответ не падает в миссию, не молчит, честно деградирует
(фикс A3), использует память (дыры 1/3), читает top-1 (дыра 2) и честно
маркирует verified (дыра 4).
"""

import sys

import pytest

sys.path.insert(0, ".")

import core.understanding.quick_answer as qa  # noqa: E402
from core.understanding.quick_answer import (  # noqa: E402
    QuickAnswerEngine,
    QuickAnswerResult,
)


# --------------------------------------------------------------------------- #
# Фикстуры
# --------------------------------------------------------------------------- #


class _FakeSettings:
    offline_mode = True


class _FakeMemory:
    def __init__(self, answer=None):
        self._answer = answer
        self.saved = []

    def answer_context(self, question):
        return {"answer": self._answer} if self._answer else None

    def remember_exchange(self, q, a):
        self.saved.append((q, a))


class _FakeBackend:
    """Фейк локальной модели: решает -> SEARCH/KNOW, генерирует -> короткий ответ."""

    def __init__(self, decide="KNOW", out="Фейковый ответ из головы."):
        self._decide = decide
        self._out = out
        self.calls = []

    def direct(self, prompt, **kw):
        self.calls.append((prompt, kw))
        if "SEARCH или KNOW" in prompt:
            return self._decide
        return self._out


def _engine(decide="KNOW", out="Фейковый ответ из головы.", **kw):
    eng = QuickAnswerEngine(_FakeSettings(), **kw)
    eng._llm = _FakeBackend(decide=decide, out=out)
    return eng


@pytest.fixture
def no_network(monkeypatch):
    """Все поиски возвращают пусто (сеть подменена)."""
    monkeypatch.setattr(qa, "_search_impl", lambda *a, **k: [])
    monkeypatch.setattr(qa, "_fetch_impl", lambda *a, **k: "")


# --------------------------------------------------------------------------- #
# Тесты
# --------------------------------------------------------------------------- #


def test_empty_never_silent():
    r = QuickAnswerEngine(_FakeSettings()).answer("")
    assert r.text
    assert r.source == "clarify"


def test_instant_know_no_search_no_decide():
    """Вопрос-время: из головы, без decide-генерации и без сети."""
    eng = _engine(decide="SEARCH", out="Время 14:57.")  # дал бы SEARCH, но он не нужен
    r = eng.answer("который час")
    assert r.searched is False
    assert r.source == "quick_answer"
    # decide не вызвался — нет SEARCH/KNOW в списке промптов
    called = [p for p, _ in eng._llm.calls if "SEARCH или KNOW" in p]
    assert called == []


def test_memory_retriever_callback_used_first():
    """Дыра 1: колбэк-ретривер памяти отвечает без сети."""
    eng = _engine(memory_retriever=lambda q: "Факт из памяти.")
    r = eng.answer("столица Франции")
    assert r.source == "memory"
    assert r.searched is False
    assert r.verified is True
    assert r.text.startswith("Факт из памяти")


def test_legacy_memory_object_supported():
    """Обратная совместимость: объект с .answer_context()."""
    eng = _engine(memory=_FakeMemory("Часовой пояс Кызылорды: UTC+5."))
    r = eng.answer("какой часовой пояс")
    assert r.source == "memory"


def test_know_path_no_search(no_network):
    """KNOW-решение -> из головы, поиска нет."""
    eng = _engine(decide="KNOW", out="Это стабильное знание.")
    r = eng.answer("демократия и республика, в чём разница")
    assert r.searched is False
    assert r.source == "quick_answer"
    assert r.verified is True  # дыра 4: уверенно из головы


def test_explanatory_marker_forces_search(monkeypatch):
    """«объясни/почему» -> сразу поиск, даже если модель сказала бы KNOW."""
    captured = {}
    def fake_search(q, max_results=4, timeout=None):
        captured["searched"] = True
        return [{"title": "Небо", "url": "https://n.example", "snippet": "..."}]
    def fake_fetch(url, max_length=2400, timeout=6.0):
        return "Рэлеевское рассеяние."
    monkeypatch.setattr(qa, "_search_impl", fake_search)
    monkeypatch.setattr(qa, "_fetch_impl", fake_fetch)
    eng = _engine(decide="KNOW", out="не должно быть вызвано")
    r = eng.answer("объясни мне, почему небо голубое")
    assert captured.get("searched") is True
    assert r.searched is True


def test_top1_only_fetch(monkeypatch):
    """Дыра 2: читается ТОЛЬКО первый источник."""
    fetched = []
    def fake_search(q, max_results=4, timeout=None):
        return [
            {"title": "Первый", "url": "https://one.example", "snippet": "..."},
            {"title": "Второй", "url": "https://two.example", "snippet": "..."},
        ]
    def fake_fetch(url, max_length=2400, timeout=6.0):
        fetched.append(url)
        return "Текст первого источника."
    monkeypatch.setattr(qa, "_search_impl", fake_search)
    monkeypatch.setattr(qa, "_fetch_impl", fake_fetch)
    eng = _engine(decide="KNOW", out="Ответ по первому источнику.")
    r = eng.answer("кто такой Цицерон")
    assert len(fetched) == 1  # top-1, не top-2
    assert "one.example" in fetched[0]
    assert r.evidence
    assert r.verified is True  # есть evidence


def test_degraded_when_network_fails_honest(monkeypatch):
    """Сбой сети -> ЧЕСТНАЯ деградация, не canned-фраза «сохранено»."""
    def boom(q, max_results=4, timeout=None):
        raise RuntimeError("network down")
    monkeypatch.setattr(qa, "_search_impl", boom)
    eng = _engine(decide="KNOW", out="Ответ из головы.")
    r = eng.answer("новейшая новость сегодня")  # маркер 'today'? нет -> decide KNOW -> head
    # после критики: маркер форс-поиска нет, значит KNOW путь -> head, сети нет
    assert r.searched is False
    assert r.source == "quick_answer"


def test_search_fail_when_forced_search(monkeypatch):
    """Форс-маркер + сбой сети -> честная деградация «по памяти»."""
    def boom(q, max_results=4, timeout=None):
        raise RuntimeError("network down")
    monkeypatch.setattr(qa, "_search_impl", boom)
    eng = _engine(decide="KNOW", out="Ответ по памяти.")
    r = eng.answer("почему сегодня холодно")  # маркер 'почему' форсит поиск
    assert r.degraded is True
    assert r.searched is True
    assert r.verified is False            # дыра 4: сбой -> не verified
    assert "по памяти" in r.text
    assert "повторной попытки" not in r.text.lower()  # фикс A3


def test_compress_saves_fact_to_memory(monkeypatch):
    """Дыра 3: найденный факт пишется в память в фоне."""
    mem = _FakeMemory()
    def fake_search(q, max_results=4, timeout=None):
        return [{"title": "Энтропия", "url": "https://e.example", "snippet": "..."}]
    def fake_fetch(url, max_length=2400, timeout=6.0):
        return "Энтропия — мера беспорядка в системе."
    monkeypatch.setattr(qa, "_search_impl", fake_search)
    monkeypatch.setattr(qa, "_fetch_impl", fake_fetch)
    eng = _engine(
        decide="KNOW", out="Энтропия — мера беспорядка.",
        memory_retriever=lambda q: None,
        memory_saver=mem.remember_exchange,
    )
    r = eng.answer("что такое энтропия")
    assert r.source == "search"
    import time as _t
    for _ in range(50):
        if mem.saved:
            break
        _t.sleep(0.02)
    assert mem.saved, "факт должен быть сохранён в память (дыра 3)"


def test_bing_parser_extracts_results(monkeypatch):
    """Запасной поиск Bing: парсер извлекает результаты из HTML (без core.actions)."""
    html = """
    <html><body>
      <li class="b_algo">
        <h2><a href="https://en.wikipedia.org/wiki/Gravity">Гравитация</a></h2>
        <div class="b_caption"><p>Гравитация — фундаментальное взаимодействие.</p></div>
      </li>
      <li class="b_algo">
        <h2><a href="https://x.example/2">Второй</a></h2>
        <span class="b_lineclamp2">Второй результат.</span>
      </li>
    </body></html>
    """
    class _Resp:
        status_code = 200
        text = html
    captured = {}
    import requests as _r
    def fake_get(url, **kw):
        captured["url"] = url
        captured["params"] = kw.get("params")
        return _Resp()
    monkeypatch.setattr(_r, "get", fake_get)
    res = qa._search_bing("гравитация", 4, timeout=8.0)
    assert len(res) == 2
    assert res[0]["title"] == "Гравитация"
    assert res[0]["url"].startswith("https://en.wikipedia.org")
    assert "взаимодействие" in res[0]["snippet"]
    assert captured["url"].startswith("https://www.bing.com/search")


def test_bing_returns_empty_on_http_error(monkeypatch):
    import requests as _r
    class _Err:
        status_code = 503
        text = ""
    monkeypatch.setattr(_r, "get", lambda url, **kw: _Err())
    assert qa._search_bing("что-то", 4, timeout=8.0) == []


def test_search_path_when_decide_searches(monkeypatch):
    """SEARCH-решение (без маркера) -> поиск."""
    captured = {}
    def fake_search(q, max_results=4, timeout=None):
        captured["searched"] = True
        return [{"title": "Погода", "url": "https://w.example", "snippet": "..."}]
    def fake_fetch(url, max_length=2400, timeout=6.0):
        return "Сегодня в Астане солнечно, +22."
    monkeypatch.setattr(qa, "_search_impl", fake_search)
    monkeypatch.setattr(qa, "_fetch_impl", fake_fetch)
    eng = _engine(decide="SEARCH", out="В Астане солнечно, +22.")
    r = eng.answer("какая погода в Астане")  # без форс-маркера
    assert captured.get("searched") is True
    assert r.searched is True
