"""Абстракция «компьютера» (CUA backend) — глаза и руки.

Дизайн следует существующему решению проекта: реальный ввод (мышь/
клавиатура) по умолчанию НЕ выполняется. Вместо этого:

    * ``ComputerBackend`` — абстрактный контракт (общие глаза/руки);
    * ``DryRunBackend`` — безопасный режим по умолчанию: «снимает» и
      «кликает» на мок-поверхности, ВСЁ регистрируется в журнал, реального
      ввода нет (как существующий ``DryRunInputController``);
    * ``RealInputBackend`` — настоящий ввод через pyautogui/pygetwindow,
      живёт в ОТДЕЛЬНОМ модуле и активен ТОЛЬКО при ``cua.real_input=True``
      (выключен по умолчанию — возобновление автономного safety-решения).

Все backend-и возвращают нормализованные ``Point``/текст экрана, не пиксели.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from core.cua.geometry import Point, Region, NORM_MAX

__all__ = [
    "ComputerBackend",
    "DryRunBackend",
    "RealInputBackend",
    "build_backend",
    "ObservedScreen",
]


@dataclass
class ObservedScreen:
    """Снимок «экрана» с точки зрения CUA (глаза)."""

    text: str = ""                      # OCR-текст (или пусто при dry-run/ошибке)
    width: int = 1                      # логическое разрешение
    height: int = 1
    active_window: str = ""
    regions: list[Region] = field(default_factory=list)  # обнаруженные UI-регионы
    raw: Any = None                     # сырой кадр (не сериализуется)
    error: str = ""                     # текст ошибки observe() (если была)
    words: list[tuple[str, Region]] = field(default_factory=list)  # OCR: (метка, регион)


class ComputerBackend(ABC):
    """Два обязательных глаза: снять экран, выполнить действие."""

    @abstractmethod
    def observe(self, *, permission: bool = False) -> ObservedScreen:
        """Снять текущий экран и вернуть OCR-текст + регионы."""

    @abstractmethod
    def act(self, action: str, *, region: Optional[Region] = None,
            point: Optional[Point] = None, text: str = "") -> Any:
        """Выполнить действие (click/type/scroll/hotkey...)."""

    @property
    def is_real(self) -> bool:
        """True, если backend выполняет реальный ввод."""
        return False


class DryRunBackend(ComputerBackend):
    """Безопасный режим по умолчанию: записывает намерения, не выполняет.

    Имитирует поведение: observe возвращает ``ObservedScreen`` с пустым
    текстом (нет OCR), дей-ствий физически нет — только журнал.
    """

    def __init__(self) -> None:
        self.log: list[dict[str, Any]] = []

    def observe(self, *, permission: bool = False) -> ObservedScreen:
        if not permission:
            raise PermissionError("Screen capture requires explicit permission")
        self.log.append({"op": "observe", "permission": permission})
        return ObservedScreen(text="", width=1, height=1,
                              active_window="(dry-run)", regions=[])

    def act(self, action: str, *, region: Optional[Region] = None,
            point: Optional[Point] = None, text: str = "") -> Any:
        entry = {"op": "act", "action": action, "region": region and region.centroid,
                 "point": point, "text": text[:80]}
        self.log.append(entry)
        return entry

    @property
    def is_real(self) -> bool:
        return False


class RealInputBackend(ComputerBackend):
    """Настоящий ввод (pyautogui/pygetwindow). Только по явному включению.

    Этот класс НЕ импортирует тяжёлые зависимости на уровне модуля — они
    подтягиваются лениво в ``observe``/``act``, чтобы проект не падал там,
    где pyautogui не установлен или флаг выключен.
    """

    def __init__(self) -> None:
        self._enabled = False  # активируется из build_backend()

    def observe(self, *, permission: bool = False) -> ObservedScreen:
        if not permission:
            raise PermissionError("Screen capture requires explicit permission")
        try:
            import mss  # type: ignore
            from core.vision.screen import ScreenCapture
        except Exception as exc:  # noqa: BLE001
            return ObservedScreen(text="", active_window="(no mss)",
                                  error=str(exc)[:120])
        cap = ScreenCapture(ocr_enabled=True)
        result = cap.capture(permission=True)
        w, h = _screen_size()
        return ObservedScreen(text=result.text, width=w, height=h,
                              active_window=result.active_window)

    def act(self, action: str, *, region: Optional[Region] = None,
            point: Optional[Point] = None, text: str = "") -> Any:
        if not self._enabled:
            raise RuntimeError("Real input disabled (cua.real_input=False)")
        try:
            import pyautogui  # type: ignore
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)[:120]}
        w, h = _screen_size()
        px = py = None
        if point is not None:
            px, py = point.to_pixels(w, h)
        elif region is not None:
            px, py = region.centroid.to_pixels(w, h)
        if action in {"click", "left_click"}:
            pyautogui.click(px, py)
            return {"ok": True, "action": "click", "px": px, "py": py}
        if action == "move":
            pyautogui.moveTo(px, py, duration=0.15)
            observed = pyautogui.position()
            return {
                "ok": int(observed.x) == int(px) and int(observed.y) == int(py),
                "action": "move", "px": px, "py": py,
                "observed_x": int(observed.x), "observed_y": int(observed.y),
            }
        if action in {"double_click"}:
            pyautogui.doubleClick(px, py)
            return {"ok": True, "action": "double_click", "px": px, "py": py}
        if action == "right_click":
            pyautogui.rightClick(px, py)
            return {"ok": True, "action": "right_click", "px": px, "py": py}
        if action == "type":
            pyautogui.write(text, interval=0.01)
            return {"ok": True, "action": "type"}
        if action == "press":
            pyautogui.press(str(text or ""))
            return {"ok": True, "action": "press", "key": str(text or "")}
        if action == "scroll":
            pyautogui.scroll(int(text or "1"))
            return {"ok": True, "action": "scroll"}
        if action == "hotkey":
            parts = [s.strip() for s in (text or "").split("+") if s.strip()]
            if parts:
                pyautogui.hotkey(*parts)
                return {"ok": True, "action": "hotkey", "keys": parts}
        return {"ok": False, "action": action, "error": "unsupported"}

    @property
    def is_real(self) -> bool:
        return self._enabled


def _screen_size() -> tuple[int, int]:
    try:
        import pyautogui  # type: ignore
        return int(pyautogui.size().width), int(pyautogui.size().height)
    except Exception:  # noqa: BLE001
        return 1920, 1080


def build_backend(*, real_input: bool = False) -> ComputerBackend:
    """Построить backend: безопасный dry-run по умолчанию, реальный — по флагу."""
    if real_input:
        b = RealInputBackend()
        b._enabled = True
        return b
    return DryRunBackend()
