"""Нормализованная система координат computer-use (CUA).

Паттерн взят у донора OpenComputer (MIT): агент оперирует НЕ пикселями,
а нормализованными координатами в квадрате 1000×1000 плюс region-zoom для
маленьких целей. Это делает действия независимыми от разрешения экрана и
позволяет модели/логике ссылаться на точку, а не угадывать пиксели.

Соглашения:
    * нормализованные координаты — ``float`` в [0, 1000] по каждой оси;
    * ``Point`` — (x, y) в [0, 1000];
    * ``Region`` — (x, y, w, h) в [0, 1000];
    * ``zoom`` — выделить/«приблизить» регион: пересчитать координаты так,
      будто этот регион — весь экран (для повторного grounding мелкой цели).
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Point", "Region", "NORM_MAX", "clamp", "zoom_to_region", "region_centroid"]


NORM_MAX = 1000.0


def clamp(v: float, lo: float = 0.0, hi: float = NORM_MAX) -> float:
    """Ограничить значение в [lo, hi]."""
    return max(lo, min(hi, float(v)))


@dataclass(frozen=True)
class Point:
    """Нормализованная точка (0..1000)."""

    x: float
    y: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", round(clamp(self.x), 3))
        object.__setattr__(self, "y", round(clamp(self.y), 3))

    def to_pixels(self, width: int, height: int) -> tuple[int, int]:
        """Сконвертировать в пиксели реального экрана."""
        return int(round(self.x / NORM_MAX * max(1, width))), int(
            round(self.y / NORM_MAX * max(1, height))
        )

    @classmethod
    def from_pixels(cls, px: float, py: float, width: int, height: int) -> "Point":
        """Конвертировать пиксели в нормализованную точку."""
        return cls(px / max(1, width) * NORM_MAX, py / max(1, height) * NORM_MAX)


@dataclass(frozen=True)
class Region:
    """Нормализованный прямоугольник (x, y, w, h в 0..1000)."""

    x: float
    y: float
    w: float
    h: float

    def __post_init__(self) -> None:
        x = clamp(self.x)
        y = clamp(self.y)
        w = clamp(self.w)
        h = clamp(self.h)
        # Не даём выйти за край экрана.
        if x + w > NORM_MAX:
            w = NORM_MAX - x
        if y + h > NORM_MAX:
            h = NORM_MAX - y
        object.__setattr__(self, "x", round(x, 3))
        object.__setattr__(self, "y", round(y, 3))
        object.__setattr__(self, "w", round(max(0.0, w), 3))
        object.__setattr__(self, "h", round(max(0.0, h), 3))

    @property
    def centroid(self) -> Point:
        return Point(self.x + self.w / 2.0, self.y + self.h / 2.0)

    def contains(self, p: Point) -> bool:
        return self.x <= p.x <= self.x + self.w and self.y <= p.y <= self.y + self.h


def region_centroid(points: list[Point]) -> Point:
    """Центроид списка точек (для «кликнуть по центру скопления»)."""
    if not points:
        return Point(NORM_MAX / 2.0, NORM_MAX / 2.0)
    return Point(sum(p.x for p in points) / len(points),
                 sum(p.y for p in points) / len(points))


def zoom_to_region(point: Point, region: Region) -> Point:
    """Пересчитать точку так, будто ``region`` — весь экран (region-zoom).

    Полезно: маленькая цель -> сначала «приблизить» регион до 1000×1000,
    затем grounding внутри него точнее. Возвращает нормализованную точку
    в новом «увеличенном» пространстве.
    """
    if region.w <= 0 or region.h <= 0:
        return point
    nx = (clamp(point.x) - region.x) / region.w * NORM_MAX
    ny = (clamp(point.y) - region.y) / region.h * NORM_MAX
    return Point(nx, ny)
