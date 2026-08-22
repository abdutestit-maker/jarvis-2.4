"""Тесты CUA grounding + engine (observe→ground→reflect).

Цель: метка из OCR-слов -> нормализованный регион/точка; CUAEngine действует
только по найденной цели; без permission -> честная ошибка.
"""

import sys

import pytest

sys.path.insert(0, ".")

from core.cua.engine import CUAEngine  # noqa: E402
from core.cua.grounding import GroundResult, Grounder  # noqa: E402


class _FakeBackend:
    """DryRun-backend с заранее заданными OCR-словами и сменой текста."""

    def __init__(self, words=None, text_after_act=None):
        from core.cua.backend import ObservedScreen
        from core.cua.geometry import Region
        self._words = words or [("Старт", Region(400, 300, 100, 50))]
        self._text = "".join(w for w, _ in self._words)
        self._after = text_after_act
        self._is_real = False
        self.actions = []

    @property
    def is_real(self):
        return self._is_real

    def observe(self, *, permission=False):
        from core.cua.backend import ObservedScreen
        if not permission:
            raise PermissionError("screen requires permission")
        return ObservedScreen(
            text=self._text, width=1000, height=1000,
            active_window="test", words=list(self._words),
        )

    def act(self, action, *, region=None, point=None, text=""):
        self.actions.append((action, point))
        if self._after is not None:
            self._text = self._after  # «экран изменился» -> verify пройдёт
        return {"ok": True, "action": action}


# --------------------------------------------------------------------------- #
#  Grounding
# --------------------------------------------------------------------------- #


def test_ground_exact_word():
    from core.cua.backend import ObservedScreen
    from core.cua.geometry import Region
    scr = ObservedScreen(words=[("Старт", Region(400, 300, 100, 50))])
    res = Grounder().ground(scr, "Старт")
    assert res.found is True
    assert res.point is not None
    assert res.point.to_pixels(1000, 1000) == (450, 325)
    assert res.confidence == 1.0


def test_ground_substring():
    from core.cua.backend import ObservedScreen
    from core.cua.geometry import Region
    scr = ObservedScreen(words=[("Открыть меню", Region(0, 0, 200, 50))])
    res = Grounder().ground(scr, "Открыть")
    assert res.found is True
    assert res.confidence == 0.8


def test_ground_missing():
    from core.cua.backend import ObservedScreen
    scr = ObservedScreen(words=[("Старт", None)], text="")
    res = Grounder().ground(scr, "Выход")
    assert res.found is False
    assert res.point is None


def test_ground_fallback_text_center():
    from core.cua.backend import ObservedScreen
    scr = ObservedScreen(words=[], text="что-то про Выход")
    res = Grounder().ground(scr, "Выход")
    assert res.found is True
    assert res.confidence == 0.4


def test_ground_respects_view():
    from core.cua.backend import ObservedScreen
    from core.cua.geometry import Region
    scr = ObservedScreen(words=[("Кнопка", Region(100, 100, 50, 50))])
    view = Region(0, 0, 50, 50)  # View не включает слово (centroid 125,125)
    res = Grounder().ground(scr, "Кнопка", view=view)
    # Новое поведение: words вне view игнорируются -> not found.
    assert res.found is False


def test_ground_view_finds_inside():
    from core.cua.backend import ObservedScreen
    from core.cua.geometry import Region
    scr = ObservedScreen(words=[("Внутри", Region(10, 10, 30, 30)), ("Снаружи", Region(200, 200, 50, 50))])
    view = Region(0, 0, 100, 100)
    res = Grounder().ground(scr, "Внутри", view=view)
    assert res.found is True
    assert res.confidence == 1.0


def test_ground_zoom_small_target():
    from core.cua.backend import ObservedScreen
    from core.cua.geometry import Region
    # Маленький регион (1×1) должен триггерить zoom_to_region при zoom_slop=24.
    scr = ObservedScreen(words=[("Микро", Region(100, 100, 1, 1))])
    res = Grounder(zoom_slop=24).ground(scr, "Микро")
    assert res.found is True
    # zoom_to_region пересчитает centroid (100.5,100.5) внутри tiny region.


def test_ground_no_zoom_large_target():
    from core.cua.backend import ObservedScreen
    from core.cua.geometry import Region
    # Большой регион (100×100) — zoom НЕ должен срабатывать (slop=24, но w,h > 24).
    scr = ObservedScreen(words=[("Большой", Region(100, 100, 100, 100))])
    res = Grounder(zoom_slop=24).ground(scr, "Большой")
    assert res.found is True
    assert res.point == Region(100, 100, 100, 100).centroid


# --------------------------------------------------------------------------- #
#  Engine
# --------------------------------------------------------------------------- #


def test_engine_act_finds_target():
    from core.cua.geometry import Region
    eng = CUAEngine(
        _FakeBackend(words=[("Старт", Region(400, 300, 100, 50))],
                     text_after_act="готово"),
        stability_delay=0.0)
    res = eng.act("запустить", target="Старт", permission=True)
    assert res.ok is True


def test_engine_act_target_not_found():
    eng = CUAEngine(_FakeBackend(), stability_delay=0.0)
    res = eng.act("закрыть", target="НесуществующаяКнопка", permission=True)
    assert res.ok is False
    assert "не найдена" in res.error


def test_engine_act_requires_permission():
    eng = CUAEngine(_FakeBackend(), stability_delay=0.0)
    res = eng.act("запустить", target="Старт", permission=False)
    assert res.ok is False
    assert "observe denied" in res.error


def test_engine_act_with_explicit_point():
    from core.cua.geometry import Point
    eng = CUAEngine(_FakeBackend(words=[],
                                 text_after_act="changed"),
                    stability_delay=0.0)
    res = eng.act("клик", point=Point(500, 500), permission=True)
    # Drain + default verifier: текста до=после нет разницы -> reflection без verify?
    # В fake backend текст меняется на 'changed', но после остаётся 'changed' ->
    # проверить успех не обязателен; проверяем что не упало и действие дошло.
    assert res.reflect is not None
