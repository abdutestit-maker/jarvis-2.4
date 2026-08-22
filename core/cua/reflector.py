"""Reflector: цикл «глаза и руки» для живого computer-use.

Паттерн взят у доноров (MIT): OpenComputer (loop observe→decide→act→verify),
Navigator (change-detection + recovery).

Reflector — это ядро «Джарвис живёт в компьютере»:
    observe (снять экран/OCR)
      → ground (найти цель в координатах 1000×1000)
      → act (клик/ввод)
      → verify (изменился ли экран/достигнуто ли)
      → recover (если нет — вернуть цель и повторить, до лимита)

Он НЕ решает "что делать" (это модель/план выше). Он отвечает за надёжное
исполнение одного шага: "сделай это действие и проверь, что вышло".

Безопасность: лимит шагов (как max_action_iterations), реальный ввод только
через `real_input`-backend (выключен по умолчанию), verify честный.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from core.cua.backend import ComputerBackend, ObservedScreen
from core.cua.geometry import Point, Region
from core.utils.logger import get_logger

__all__ = ["Reflector", "ReflectResult", "Groounder"]

log = get_logger(__name__)


#: Функция grounding: по задаче/запросам и снимку вернуть цель (регион или точку).
#: Принимает (screenshot, instruction) -> (Point | Region | None, описание).
Groounder = Callable[[ObservedScreen, str], tuple[Optional[Point], str]]


def _default_grounder(screen: ObservedScreen, instruction: str) -> tuple[Optional[Point], str]:
    """Дефолтный «грозндер» по тексту: ищет подстроку в OCR.

    Это детерминированный fallback без VLM: если в OCR-тексте есть искомая
    метка, возвращаем центр экрана как точку (грубо). Реальная локализация
    подключается позже (UI-TARS/OCR-регионы).
    """
    labels = [w for w in instruction.split() if len(w) > 2]
    if any(lb.casefold() in screen.text.casefold() for lb in labels):
        return None, "метка найдена в OCR (без координат)"
    return None, "метка не найдена в OCR"


@dataclass
class ReflectResult:
    """Итог одного шага reflector-цикла."""

    ok: bool                              # успешно ли выполнен шаг (verify прошёл)
    action: str = ""
    verify_text: str = ""
    attempts: int = 0
    recovered: bool = False               # потребовалась ли recovery-попытка
    evidence: list[str] = field(default_factory=list)
    error: str = ""


class Reflector:
    """Выполняет шаг «действие + verify(+recover)» через backend."""

    def __init__(self, backend: ComputerBackend, *,
                 max_attempts: int = 3,
                 stability_delay: float = 0.4,
                 grounder: Optional[Groounder] = None,
                 verifier: Optional[Callable[[ObservedScreen, str], bool]] = None,
                 on_step: Optional[Callable[[dict[str, Any]], None]] = None) -> None:
        self._backend = backend
        self._max_attempts = max(1, int(max_attempts))
        self._stability_delay = max(0.0, float(stability_delay))
        self._grounder = grounder or _default_grounder
        # Default verifier: считаем успехом, если после действия изменился
        # активный заголовок/текст (change-detection упрощённо).
        self._verifier = verifier or self._default_verify
        self._on_step = on_step

    # ------------------------------------------------------------------ #
    def run(self, instruction: str, *, action: str = "click",
            text: str = "", region: Optional[Region] = None,
            point: Optional[Point] = None) -> ReflectResult:
        """Выполнить шаг с verify/recover. Никогда не бросает (кроме perms)."""
        started = time.perf_counter()
        attempts = 0
        recovered = False
        verify_text = ""
        evidence: list[str] = []
        last_error = ""

        before = self._observe(evidence)
        while attempts < self._max_attempts:
            attempts += 1
            # Ground: если нет явной точки/региона, ищем через grounder.
            cur_point, desc = point, ""
            if region is not None:
                cur_point = region.centroid
            elif cur_point is None:
                cur_point, desc = self._grounder(before, instruction)

            self._emit({
                "attempt": attempts, "instruction": instruction,
                "action": action, "target": cur_point and cur_point.x, 
                "target_desc": desc,
            })
            try:
                self._backend.act(action, point=cur_point, region=region, text=text)
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)[:200]
                log.warning("Reflector: act упал (%s); попытка recovery", exc)
                recovered = True
                time.sleep(self._stability_delay)
                continue

            # Verify после действия.
            time.sleep(self._stability_delay)
            after = self._observe(evidence)
            verify_text = after.text[:300]
            if self._verifier(before, after):
                return ReflectResult(
                    ok=True, action=action, verify_text=verify_text,
                    attempts=attempts, recovered=recovered,
                    evidence=evidence, error=last_error,
                )
            # Изменений нет -> recovery: повтор (пауза, новый снимок).
            recovered = True
            log.info("Reflector: verify не прошёл (attempt %d/%d)",
                     attempts, self._max_attempts)
        # Исчерпали попытки.
        return ReflectResult(
            ok=False, action=action, verify_text=verify_text,
            attempts=attempts, recovered=recovered, evidence=evidence,
            error=last_error or "verify failed after max attempts",
        )

    # ------------------------------------------------------------------ #
    def _observe(self, evidence: list[str]) -> ObservedScreen:
        try:
            screen = self._backend.observe(permission=True)
        except Exception as exc:  # noqa: BLE001
            log.warning("Reflector: observe упал: %s", exc)
            return ObservedScreen(text="", active_window="", error=str(exc))
        if screen.text:
            evidence.append(screen.text[:200])
        return screen

    @staticmethod
    def _default_verify(before: ObservedScreen, after: ObservedScreen) -> bool:
        # Упрощённый change-detection: изменился ли OCR-текст или окно.
        if before.active_window and after.active_window \
                and before.active_window != after.active_window:
            return True
        return bool(after.text) and before.text != after.text

    def _emit(self, payload: dict[str, Any]) -> None:
        if self._on_step is not None:
            try:
                self._on_step(payload)
            except Exception:  # noqa: BLE001
                pass
