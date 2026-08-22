"""CUAEngine — сборка глаза+руки в одно действие: observe → ground → reflect.

``CUAEngine.do(instruction, action, ...)``:
    observe  (снять экран через backend)
      → ground (найти цель по имени среди OCR-слов)
      → act     (клик/ввод/tип и т.п.)
      → verify  (изменился ли экран)
      → recover (повтор до лимита)

Маршрутизация действия: если задан target — ищем его (grounding); если задан
point/region напрямую — действуем по им. Возвращает богатый ``CUAResult`` для
эмиссии в трассу/UI.

Безопасность (как весь CUA): реальный ввод — только через backend,
который пользователь включил явно (dry-run по умолчанию). ``permission``
обязательна для observe; без неё — честная ошибка, не молчание.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from core.cua.backend import ComputerBackend, ObservedScreen
from core.cua.geometry import Point, Region
from core.cua.grounding import GroundResult, Grounder
from core.cua.reflector import ReflectResult, Reflector
from core.utils.logger import get_logger

__all__ = ["CUAEngine", "CUAResult"]

log = get_logger(__name__)


class CUAResult:
    """Итог одного CUA-действия: что хотели, что сделали, что увидели."""

    __slots__ = ("instruction", "action", "ok", "ground", "reflect",
                 "observed", "error")

    def __init__(self, instruction: str = "", action: str = "", *,
                 ok: bool = False, ground: Optional[GroundResult] = None,
                 reflect: Optional[ReflectResult] = None,
                 observed: Optional[ObservedScreen] = None,
                 error: str = "") -> None:
        self.instruction = instruction
        self.action = action
        self.ok = ok
        self.ground = ground
        self.reflect = reflect
        self.observed = observed
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        return {
            "instruction": self.instruction,
            "action": self.action,
            "ok": self.ok,
            "grounded": getattr(self.ground, "found", False),
            "point": getattr(self.ground, "point", None),
            "verify_text": getattr(getattr(self.reflect, "verify_text", None) or self.observed, "text", "")[:200],
            "error": self.error,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"CUAResult(ok={self.ok}, instruction={self.instruction!r}, error={self.error})"


class CUAEngine:
    """Компонуем glance+hand: observe → ground → reflector (verify/recover)."""

    def __init__(self, backend: ComputerBackend, *,
                 grounder: Optional[Grounder] = None,
                 max_attempts: int = 3,
                 on_step: Optional[Callable[[dict[str, Any]], None]] = None,
                 stability_delay: float = 0.4) -> None:
        self._backend = backend
        self._grounder = grounder or Grounder()
        self._reflector = Reflector(
            backend, max_attempts=max_attempts,
            stability_delay=stability_delay,
            on_step=on_step,
        )

    @property
    def real(self) -> bool:
        """True, если backend выполняет реальный ввод."""
        return self._backend.is_real

    # ------------------------------------------------------------------ #
    def act(self, instruction: str, *, action: str = "click",
            target: Optional[str] = None,
            point: Optional[Point] = None,
            region: Optional[Region] = None,
            text: str = "", permission: bool = False) -> CUAResult:
        """Выполнить одно CUA-действие по человеко-описанию (target) или точке."""
        # 1) Observe (глаза) — только с явным разрешением.
        try:
            observed = self._backend.observe(permission=permission)
        except Exception as exc:  # noqa: BLE001
            return CUAResult(instruction, action, ok=False,
                             error=f"observe denied: {exc}")

        # 2) Ground (найти цель).
        ground = None
        final_point, final_region = point, region
        if target:
            ground = self._grounder.ground(observed, target)
            final_point = ground.point
            final_region = ground.region
            if not ground.found:
                return CUAResult(instruction, action, ok=False, ground=ground,
                                 observed=observed,
                                 error=f"цель не найдена: '{target}'")

        # 3) Reflect (действие + verify + recover).
        reflect = self._reflector.run(
            instruction, action=action, text=text,
            point=final_point, region=final_region,
        )

        return CUAResult(instruction, action, ok=reflect.ok, ground=ground,
                         reflect=reflect, observed=observed)
