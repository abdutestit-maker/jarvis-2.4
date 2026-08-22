"""Grounding: превратить «вижу картинку/OCR» в «знаю, куда кликнуть».

Детерминированный путь (без VLM и без API-ключа): ищем метку среди
распознанных OCR-слов (`ObservedScreen.words`) и возвращаем нормализованный
регион/точку. Отсюда уже действует `Reflector` (verify/recover).

Порядок (от точного к грубому):
    1. Точное совпадение слова в ``words`` -> его регион -> centroid.
    2. Метка встречается как подстрока любого слова -> регион этого слова.
    3. Метка встречается в сплошном OCR-тексте ``screen.text`` -> центроид
       всего экрана (грубо, но честно: без координат цели).

Если ничего не найдено -> ``None`` + честное описание (Reflector вернёт
«метка не найдена», не станет кликать наугад).
"""

from __future__ import annotations

from typing import Optional

from core.cua.backend import ObservedScreen
from core.cua.geometry import Point, Region, zoom_to_region

__all__ = ["GroundResult", "Grounder", "default_grounder"]


class GroundResult:
    """Итог grounding — куда целиться и как уверенно."""

    __slots__ = ("point", "region", "label", "confidence", "found")

    def __init__(self, point: Optional[Point], region: Optional[Region],
                 label: str, confidence: float, found: bool) -> None:
        self.point = point
        self.region = region
        self.label = label
        self.confidence = confidence
        self.found = found

    def __repr__(self) -> str:  # pragma: no cover
        return (f"GroundResult(found={self.found}, point={self.point}, "
                f"region={self.region}, conf={self.confidence}, label={self.label})")


def _norm(s: str) -> str:
    return " ".join((s or "").casefold().replace("ё", "е").split())


class Grounder:
    """Находит цель по имени среди OCR-слов экрана. (детерминированный, no-key)"""

    def __init__(self, *, zoom_slop: int = 24) -> None:
        # Маленькие цели (w/h < zoom_slop) «приближаем» через zoom_to_region
        # для точнее координат внутри маленького региона.
        self._zoom_slop = max(0, int(zoom_slop))

    def ground(self, screen: ObservedScreen, target: str,
               *, view: Optional[Region] = None) -> GroundResult:
        """Найти цель (кнопку/метку) на экране/в регионе.

        Args:
            screen: снимок экрана (words = OCR-слова с регионами).
            target: что ищем (напр. 'Открыть', 'Submit').
            view: если задан — сузиться до этого региона (words вне view игнорируются).

        Returns:
            GroundResult с точкой/регионом и уверенностью.
        """
        t = _norm(target)
        if not t:
            return GroundResult(None, view, target, 0.0, False)

        candidates = (screen.words or [])
        if view is not None:
            # Сузить поиск до региона (region-zoom): игнорировать слова вне view.
            candidates = [(w, r) for w, r in candidates if r is not None and view.contains(r.centroid)]

        best: Optional[tuple[float, Region]] = None
        for word, reg in candidates:
            w = _norm(word)
            if not w or reg is None:
                continue
            if w == t:
                score = 1.0
            elif t in w or w in t:
                score = 0.8
            else:
                continue
            if best is None or score > best[0]:
                best = (score, reg)

        if best is not None:
            score, reg = best
            # Не выходить за пределы view (если зум-регион).
            if view is not None and not _region_inside(reg, view):
                reg = view
            pt = reg.centroid
            # Приближаем только маленькие цели (иначе zoom_to_region бессмысленен).
            if self._zoom_slop and (reg.w < self._zoom_slop or reg.h < self._zoom_slop):
                pt = zoom_to_region(pt, reg)
            return GroundResult(pt, reg, target, score, True)

        # Грубый fallback: метка есть в тексте, но нет региона слова -> центр экрана.
        if t and _norm(screen.text).count(t):
            return GroundResult(Point(500, 500), view, target, 0.4, True)

        return GroundResult(None, view, target, 0.0, False)


def default_grounder() -> Grounder:
    """Фабрика Grounder по умолчанию (противопоставлена Reflector.default)."""
    return Grounder()


def _region_inside(inner: Region, outer: Region) -> bool:
    return (inner.x >= outer.x and inner.y >= outer.y and
            inner.x + inner.w <= outer.x + outer.w and
            inner.y + inner.h <= outer.y + outer.h)
