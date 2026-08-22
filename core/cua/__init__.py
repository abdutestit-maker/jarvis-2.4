"""CUA (Computer-Use Agent) — «глаза и руки» для живого Джарвиса.

Публичный контракт::

    from core.cua import Reflector, build_backend, Point, Region

Задачи модуля:
    * нормализованные координаты 1000×1000 (не пиксели) + region-zoom
      → ``core.cua.geometry``;
    * безопасный backend: dry-run по умолчанию, реальный ввод выключен
      → ``core.cua.backend``;
    * reflector-цикл observe → ground → act → verify → recover
      → ``core.cua.reflector``.

Следует safety-решению проекта: реальная мышь/клавиатура только при
явном ``cua.real_input=True`` (по умолчанию выключено).
"""

from __future__ import annotations

from core.cua.backend import (
    ComputerBackend,
    DryRunBackend,
    ObservedScreen,
    RealInputBackend,
    build_backend,
)
from core.cua.geometry import NORM_MAX, Point, Region, region_centroid, zoom_to_region
from core.cua.reflector import ReflectResult, Reflector

__all__ = [
    "ComputerBackend",
    "DryRunBackend",
    "ObservedScreen",
    "RealInputBackend",
    "build_backend",
    "Point",
    "Region",
    "NORM_MAX",
    "region_centroid",
    "zoom_to_region",
    "ReflectResult",
    "Reflector",
]
