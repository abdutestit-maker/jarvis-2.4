"""Тесты CUA-ядра (Computer-Use Agent) — «глаза и руки».

Цель: нормализованные координаты, безопасный dry-run backend по умолчанию,
reflector-цикл observe→act→verify→recover (на моках — реальный десктоп в
песочнице недоступен).
"""

import sys

import pytest

sys.path.insert(0, ".")

from core.cua import (  # noqa: E402
    DryRunBackend,
    Point,
    ReflectResult,
    Reflector,
    Region,
    build_backend,
    region_centroid,
    zoom_to_region,
)
from core.cua.backend import ObservedScreen  # noqa: E402
from core.cua.geometry import NORM_MAX, clamp  # noqa: E402


# --------------------------------------------------------------------------- #
#  Геометрия
# --------------------------------------------------------------------------- #


def test_point_pixel_conversion():
    p = Point(500, 500)
    assert p.to_pixels(1920, 1080) == (960, 540)
    assert Point.from_pixels(960, 540, 1920, 1080) == p


def test_point_clamps_to_range():
    assert Point(-50, 1500) == Point(0, 1000)
    assert clamp(-5) == 0
    assert clamp(5) == 5.0
    assert clamp(2000) == 1000


def test_region_centroid():
    r = Region(0, 0, 500, 500)
    assert r.centroid == Point(250, 250)


def test_region_limits_at_edge():
    r = Region(900, 900, 500, 500)
    assert r.x + r.w <= NORM_MAX + 1e-6
    assert r.y + r.h <= NORM_MAX + 1e-6


def test_zoom_to_region():
    # Точка (250,250) внутри региона (0,0,500,500) -> центр нового пространства.
    assert zoom_to_region(Point(250, 250), Region(0, 0, 500, 500)) == Point(500, 500)


def test_region_centroid_of_points():
    assert region_centroid([Point(100, 100), Point(300, 300)]) == Point(200, 200)


# --------------------------------------------------------------------------- #
#  Backend
# --------------------------------------------------------------------------- #


def test_default_backend_is_dry_run():
    b = build_backend()  # real_input не передан -> dry-run
    assert isinstance(b, DryRunBackend)
    assert b.is_real is False


def test_real_backend_only_when_flag():
    b = build_backend(real_input=True)
    assert b.is_real is True


def test_dry_run_requires_permission():
    b = build_backend()
    with pytest.raises(PermissionError):
        b.observe()  # permission=False


def test_dry_run_observe_with_permission_ok():
    b = build_backend()
    screen = b.observe(permission=True)
    assert isinstance(screen, ObservedScreen)


def test_dry_run_act_records_no_real_input():
    b = build_backend()
    entry = b.act("click", point=Point(500, 500))
    assert entry["op"] == "act"
    assert b.log  # намерение записано, реального ввода нет


# --------------------------------------------------------------------------- #
#  Reflector
# --------------------------------------------------------------------------- #


class _FakeVerifierBackend(DryRunBackend):
    """Dry-run backend с настраиваемым change-detection."""

    def __init__(self, changes_on_attempt=None):
        super().__init__()
        self._changes_on = set(changes_on_attempt or ())  # набор «удачных» попыток
        self._n = 0

    def observe(self, *, permission=False):
        self._n += 1
        # После «удачного» действия меняем текст, чтобы verify прошёл.
        text = "changed" if (self._n - 1) in self._changes_on else ""
        return ObservedScreen(text=text, active_window="win", width=1, height=1)


def test_reflector_success_on_first_attempt():
    b = _FakeVerifierBackend(changes_on_attempt={1})
    r = Reflector(b, max_attempts=3, stability_delay=0.0)
    res = r.run("do thing", action="click", point=Point(500, 500))
    assert res.ok is True
    assert res.attempts == 1
    assert res.recovered is False


def test_reflector_recovery_after_fail():
    b = _FakeVerifierBackend(changes_on_attempt={3})  # успех на 3-й попытке
    r = Reflector(b, max_attempts=3, stability_delay=0.0)
    res = r.run("do thing", action="click")
    assert res.ok is True
    assert res.attempts == 3
    assert res.recovered is True  # потребовалась recovery


def test_reflector_fails_after_max_attempts():
    b = _FakeVerifierBackend(changes_on_attempt=set())  # никогда не срабатывает
    r = Reflector(b, max_attempts=2, stability_delay=0.0)
    res = r.run("do thing", action="click")
    assert res.ok is False
    assert res.attempts == 2


def test_reflector_honest_verify_text():
    b = _FakeVerifierBackend(changes_on_attempt={1})
    r = Reflector(b, max_attempts=3, stability_delay=0.0)
    res = r.run("do thing", action="click", point=Point(500, 500))
    assert res.verify_text  # что-то «увидели» после действия


def test_reflector_on_step_callback_called():
    steps = []
    b = _FakeVerifierBackend(changes_on_attempt={1})
    r = Reflector(b, max_attempts=3, stability_delay=0.0,
                  on_step=lambda p: steps.append(p))
    r.run("do thing", action="click", point=Point(500, 500))
    assert steps  # шаги передаются наружу (для UI/трейс)


def test_custom_grounder_used():
    seen = {}

    def my_grounder(screen, instruction):
        seen["called"] = True
        return Point(100, 100), "custom"

    b = _FakeVerifierBackend(changes_on_attempt={1})
    r = Reflector(b, max_attempts=2, stability_delay=0.0, grounder=my_grounder)
    res = r.run("найди кнопку", action="click")
    assert seen.get("called") is True
    assert res.ok is True
