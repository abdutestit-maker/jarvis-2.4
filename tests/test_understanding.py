"""Тесты Understanding Layer — контракт маршрутизации (Фаза 1).

Покрывает баги из живого баг-листа:
    * A2: «открой блокнот» / «слышишь меня, открой браузер» — НЕ рефлекс.
    * A3: составные команды сохраняют все фрагменты.
    * A4: вопросы («помоги решить задачу…») — quick_answer, не шаблон.
    * Миссии: «сделай презентацию…» — mission, глагол «сделай» не должен
      перехватывать маршрут раньше маркера миссии (кириллица + \\b!).
    * Никогда не молчит: пустой ввод и мусор → clarify.
"""

from __future__ import annotations

import pytest

from core.understanding import Route, UnderstandingLayer


@pytest.fixture(scope="module")
def layer() -> UnderstandingLayer:
    return UnderstandingLayer()


# --- action -----------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "Открой блокнот и набери приветствие 'Сэр, системы в норме'",
    "слышишь меня, открой браузер",
    "запусти калькулятор",
    "создай файл plan.txt и переименуй его в done.txt",
    "включи музыку",
])
def test_action(layer, text):
    u = layer.understand(text)
    assert u.route == Route.ACTION, f"{text!r} -> {u.route} ({u.reason})"


# --- quick_answer -----------------------------------------------------------

@pytest.mark.parametrize("text", [
    "помоги решить задачу: как найти площадь круга?",
    "Чем стратегия отличается от тактики?",
    "что такое энтропия",
    "объясни, как работает транзистор",
    "сколько будет 17 * 23?",
])
def test_quick_answer(layer, text):
    u = layer.understand(text)
    assert u.route == Route.QUICK_ANSWER, f"{text!r} -> {u.route} ({u.reason})"
    assert u.intent == "web"


# --- reflex -----------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "привет",
    "как дела",
    "который час",
    "спасибо",
    "слышишь меня",
])
def test_reflex(layer, text):
    u = layer.understand(text)
    assert u.route == Route.REFLEX, f"{text!r} -> {u.route} ({u.reason})"


# --- mission ----------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "сделай презентацию про марс на 5 слайдов",
    "подготовь отчёт по продажам за квартал",
    "напиши доклад про фотосинтез",
])
def test_mission(layer, text):
    u = layer.understand(text)
    assert u.route == Route.MISSION, f"{text!r} -> {u.route} ({u.reason})"


# --- clarify ----------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "",
    "   ",
    "хм",
])
def test_clarify(layer, text):
    u = layer.understand(text)
    assert u.route == Route.CLARIFY, f"{text!r} -> {u.route} ({u.reason})"


def test_vague_action_low_confidence(layer):
    """«сделай как лучше»: глагол есть, объекта нет — маршрут есть, но
    уверенность ниже порога 0.7 → в Фазе 2 такое уйдёт Tier-1 классификатору."""
    u = layer.understand("сделай как лучше")
    assert u.route == Route.ACTION
    assert u.confidence < 0.7


# --- контрактные свойства ---------------------------------------------------

def test_compound_preserved(layer):
    """A3: составная команда не теряет вторую половину."""
    u = layer.understand("открой блокнот и включи музыку")
    assert u.route == Route.ACTION
    assert len(u.compound) == 2


def test_address_prefix_stripped_but_not_reflex(layer):
    """A2: обращение + команда — это команда, а не проверка связи."""
    u = layer.understand("слышишь меня, открой браузер")
    assert u.route == Route.ACTION
    assert u.intent in {"browser", "app"}


def test_privacy_flag(layer):
    u = layer.understand("запомни мой пароль от почты")
    assert u.privacy is True


def test_never_silent(layer):
    """На любой ввод — валидный маршрут с обоснованием."""
    for text in ["", "?", "а", "ы", "привет", "сделай всё"]:
        u = layer.understand(text)
        assert isinstance(u.route, Route)
        assert 0.0 <= u.confidence <= 1.0
        assert u.source in {"regex", "llm", "fallback"}
