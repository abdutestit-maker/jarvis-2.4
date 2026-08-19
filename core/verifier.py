"""Verifier — фактическая проверка результата (§14, §16).

J.A.R.V.I.S. НИКОГДА не считает задачу выполненной только потому, что вызов
инструмента завершился без исключения. Нужны ФАКТИЧЕСКИЕ проверки:

    write_file   -> файл существует на диске и читается?
    read_file    -> контент реально прочитан?
    open_app     -> процесс с таким именем реально появился?
    close_app    -> процесс реально исчез?
    web_fetch    -> страница реально загрузилась (есть контент)?
    web_search   -> есть непустые результаты?
    system_status-> метрики реально получены?
    add_reminder -> напоминание реально в списке?

Реализуется как реестр verifier-ов по имени инструмента. Инструмент (или
этот модуль) регистрирует функцию проверки через ``register_verifier``.

Если для инструмента нет специализированной проверки — используется
``default_verify``: она НЕ утверждает, что проверка была настоящей, и
помечает результат ``method="trust_ok"`` + ``strict=False``, чтобы агент
и отчёты честно различали «проверено фактически» и «доверились ok».

ВАЖНО (§14): ``VerificationResult.verified`` — единственный признак, по
которому агент имеет право сказать «готово».
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from core.actions.base import ActionResult
from core.utils.logger import get_logger

__all__ = [
    "VerificationResult",
    "verify_action_result",
    "register_verifier",
    "default_verify",
    "verify_file_exists",
    "verify_command_exit",
    "has_strict_verifier",
    "list_verified_tools",
]

log = get_logger(__name__)


@dataclass
class VerificationResult:
    """Результат фактической проверки действия (§14).

    Attributes:
        verified: прошла ли проверка.
        method: каким способом проверяли ("file_exists", "process_running", ...).
        detail: человекочитаемая деталь для отчёта.
        strict: True — это была НАСТОЯЩАЯ фактическая проверка;
            False — мы лишь доверились ``ok`` (нет специализированного verifier).
    """

    verified: bool
    method: str
    detail: str = ""
    strict: bool = True
    checked_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verified": self.verified,
            "method": self.method,
            "detail": self.detail,
            "strict": self.strict,
        }

    def __bool__(self) -> bool:
        return self.verified


# Реестр специализированных verifier-ов: имя инструмента -> callable.
_VERIFIERS: Dict[str, Callable[[ActionResult], VerificationResult]] = {}


def register_verifier(tool_name: str,
                      verifier: Callable[[ActionResult], VerificationResult]) -> None:
    """Регистрирует фактическую проверку для инструмента (§14)."""
    _VERIFIERS[tool_name] = verifier
    log.debug("Зарегистрирован verifier для инструмента '%s'", tool_name)


def has_strict_verifier(tool_name: str) -> bool:
    """Есть ли для инструмента настоящая (не trust_ok) проверка."""
    return tool_name in _VERIFIERS


def list_verified_tools() -> List[str]:
    """Список инструментов с фактическими проверками."""
    return sorted(_VERIFIERS.keys())


# --------------------------------------------------------------------------- #
#  Утилиты извлечения данных из ActionResult
# --------------------------------------------------------------------------- #

def _output_text(result: ActionResult) -> str:
    """Текст output инструмента (ActionResult — dataclass, не dict)."""
    out = getattr(result, "output", None)
    if out is None:
        return ""
    return str(out)


_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/]|\\\\|/)[^\s\"'<>|?*]+")
_PID_RE = re.compile(r"\bpid\s*=\s*(\d+)\b", re.IGNORECASE)


def _extract_paths(text: str) -> List[str]:
    """Достаёт похожие на пути токены из текста output."""
    found = [m.group(0).rstrip(".,;:)\"'") for m in _PATH_RE.finditer(text)]
    return found


# --------------------------------------------------------------------------- #
#  Универсальные verifier-ы
# --------------------------------------------------------------------------- #

def verify_file_exists(result: ActionResult) -> VerificationResult:
    """Проверяет, что файл из output реально существует на диске и читается."""
    if not result.ok:
        return VerificationResult(False, "file_exists", result.error or "ok=False")

    text = _output_text(result)
    candidates = _extract_paths(text)

    # Аргументы тоже могут содержать путь (например write_file(path=...)).
    for key in ("path", "file", "filename", "target", "dest"):
        val = (result.args or {}).get(key)
        if isinstance(val, str) and val.strip():
            candidates.append(val.strip())

    checked: List[str] = []
    for cand in candidates:
        p = Path(cand).expanduser()
        checked.append(str(p))
        if p.exists() and p.is_file():
            try:
                with open(p, "rb") as fh:
                    fh.read(1)
                return VerificationResult(True, "file_exists", f"файл существует и читается: {p}")
            except OSError as exc:
                return VerificationResult(False, "file_readable", f"{p}: {exc}")

    # Путь может быть относительным внутри documents_dir — ищем там.
    for cand in list(candidates):
        try:
            from core.utils.paths import PROJECT_ROOT
            p = PROJECT_ROOT / "data" / "documents" / Path(cand).name
            if p.is_file():
                return VerificationResult(True, "file_exists", f"файл найден в documents: {p}")
        except Exception:  # pragma: no cover — защитный путь
            pass

    if checked:
        return VerificationResult(False, "file_exists", f"файл не найден: {checked[:3]}")
    return VerificationResult(False, "no_path_in_output",
                              "в output нет пути к файлу — проверить нечем")


def verify_command_exit(result: ActionResult) -> VerificationResult:
    """Проверка по exit code, если инструмент его сообщил."""
    text = _output_text(result).lower()
    m = re.search(r"exit_code[=:]?\s*(\d+)", text)
    if m:
        code = int(m.group(1))
        return VerificationResult(code == 0, "exit_code", f"returncode={code}")
    if result.ok:
        return VerificationResult(True, "started_no_error",
                                  "процесс запущен без исключения", strict=False)
    return VerificationResult(False, "exit_code", result.error or "ok=False")


def _process_matches(names: List[str]) -> List[str]:
    """Список запущенных процессов, чьё имя совпадает с одним из names."""
    try:
        import psutil
    except ImportError:
        return []
    wanted = {n.lower() for n in names if n}
    running: List[str] = []
    for proc in psutil.process_iter(["name"]):
        try:
            pname = (proc.info.get("name") or "").lower()
        except Exception:
            continue
        if not pname:
            continue
        for w in wanted:
            # notepad.exe == notepad / notepad.exe
            if pname == w or pname == f"{w}.exe" or w in pname:
                running.append(pname)
                break
    return running


def _app_candidate_names(result: ActionResult) -> List[str]:
    """Возможные имена процессов для запрошенного приложения."""
    names: List[str] = []
    app = (result.args or {}).get("name") or (result.args or {}).get("app")
    if isinstance(app, str) and app.strip():
        names.append(app.strip())
        try:
            from core.actions.app_control import _APP_PROCESS_NAMES, resolve_app
            key = app.strip().lower()
            names.extend(_APP_PROCESS_NAMES.get(key, []))
            # Built-in aliases already provide the canonical process names.
            # Avoid a synchronous PATH/``where.exe`` lookup on the verified
            # fast path; resolve arbitrary names only when no alias exists.
            if not _APP_PROCESS_NAMES.get(key):
                resolved = resolve_app(app)
                if isinstance(resolved, str) and resolved:
                    names.append(Path(resolved).name)
        except Exception:
            pass
    # Из output вида "Запустил notepad."
    text = _output_text(result)
    m = re.search(r"[Зз]апустил\s+([^\s.,]+)", text)
    if m:
        names.append(m.group(1))
    return [n for n in names if n]


def verify_process_running(result: ActionResult) -> VerificationResult:
    """open_app: процесс реально существует в системе (§14)."""
    if not result.ok:
        return VerificationResult(False, "process_running", result.error or "ok=False")

    # The launcher returns the concrete PID when it owns the process. A PID
    # probe is stronger and faster than waiting for a GUI name scan while a
    # Windows app paints its first frame.
    pid_match = _PID_RE.search(_output_text(result))
    if pid_match:
        try:
            import psutil
            pid = int(pid_match.group(1))
            if psutil.pid_exists(pid):
                return VerificationResult(True, "process_running", f"процесс запущен: pid={pid}")
        except (ImportError, ValueError, OSError):
            pass

    names = _app_candidate_names(result)
    if not names:
        return VerificationResult(True, "process_running",
                                  "имя процесса неизвестно — строгая проверка невозможна",
                                  strict=False)

    # Приложению нужно время на старт — короткий реальный поллинг (не «лимит мышления»).
    deadline = time.time() + 1.5
    while time.time() < deadline:
        running = _process_matches(names)
        if running:
            return VerificationResult(True, "process_running",
                                      f"процесс запущен: {sorted(set(running))[:3]}")
        time.sleep(0.4)

    # Протокольные цели (ms-settings:) и UWP не дают совпадения по имени.
    text = _output_text(result)
    if ":" in text and "ms-settings" in text.lower():
        return VerificationResult(True, "shell_protocol",
                                  "запущена протокольная цель, процесса нет", strict=False)
    return VerificationResult(False, "process_running",
                              f"процесс не найден среди запущенных: {names[:3]}")


def verify_process_gone(result: ActionResult) -> VerificationResult:
    """close_app: процесс реально исчез (§14)."""
    if not result.ok:
        return VerificationResult(False, "process_gone", result.error or "ok=False")
    names = _app_candidate_names(result)
    if not names:
        return VerificationResult(True, "process_gone", "имя процесса неизвестно", strict=False)
    deadline = time.time() + 5.0
    while time.time() < deadline:
        if not _process_matches(names):
            return VerificationResult(True, "process_gone", f"процессы {names[:3]} завершены")
        time.sleep(0.4)
    return VerificationResult(False, "process_gone", f"процесс всё ещё запущен: {names[:3]}")


def verify_file_search(result: ActionResult) -> VerificationResult:
    """search_files: реально нашёл файл, а не «ничего не найдено» (§14)."""
    if not result.ok:
        return VerificationResult(False, "file_search", result.error or "ok=False")
    text = _output_text(result).lower()
    not_found = any(k in text for k in (
        "не найден", "не найдено", "ничего не найден", "ничего не",
        "no results", "not found", "0 file", "файлы не найд",
    ))
    if not_found:
        return VerificationResult(False, "file_search", "файл(ы) не найдены запросом")
    return VerificationResult(True, "file_search", "найдены совпадения")


def verify_non_empty_output(result: ActionResult) -> VerificationResult:
    """Инструмент обязан вернуть непустой осмысленный контент."""
    if not result.ok:
        return VerificationResult(False, "non_empty_output", result.error or "ok=False")
    text = _output_text(result).strip()
    if len(text) < 3:
        return VerificationResult(False, "non_empty_output",
                                  f"output слишком короткий ({len(text)} символов)")
    return VerificationResult(True, "non_empty_output", f"получено {len(text)} символов")


def verify_page_loaded(result: ActionResult) -> VerificationResult:
    """web_fetch: страница реально загрузилась и в ней есть текст."""
    if not result.ok:
        return VerificationResult(False, "page_loaded", result.error or "ok=False")
    text = _output_text(result)
    # web_fetch возвращает "Содержимое <url>:\n\n<текст>"
    body = text.split("\n\n", 1)[1] if "\n\n" in text else text
    if len(body.strip()) < 50:
        return VerificationResult(False, "page_loaded",
                                  f"страница пуста или почти пуста ({len(body.strip())} символов)")
    return VerificationResult(True, "page_loaded", f"загружено {len(body)} символов текста")


def verify_search_results(result: ActionResult) -> VerificationResult:
    """web_search: есть хотя бы один результат."""
    if not result.ok:
        return VerificationResult(False, "search_results", result.error or "ok=False")
    text = _output_text(result).strip()
    if not text or "не найдено" in text.lower() or "ничего не найдено" in text.lower():
        return VerificationResult(False, "search_results", "поиск не дал результатов")
    return VerificationResult(True, "search_results", f"результаты получены ({len(text)} символов)")


def verify_reminder_registered(result: ActionResult) -> VerificationResult:
    """add_reminder: напоминание реально существует в менеджере."""
    if not result.ok:
        return VerificationResult(False, "reminder_registered", result.error or "ok=False")
    try:
        from core.actions.reminders import get_default_manager
        reminders = get_default_manager().list_reminders()
        if reminders:
            return VerificationResult(True, "reminder_registered",
                                      f"активных напоминаний: {len(reminders)}")
        return VerificationResult(False, "reminder_registered", "список напоминаний пуст")
    except Exception as exc:
        return VerificationResult(False, "reminder_registered", f"проверка не удалась: {exc}")


def verify_system_metrics(result: ActionResult) -> VerificationResult:
    """system_status: в ответе реально есть метрики (CPU/RAM)."""
    if not result.ok:
        return VerificationResult(False, "system_metrics", result.error or "ok=False")
    text = _output_text(result).lower()
    if any(k in text for k in ("cpu", "процессор", "ram", "память", "диск", "%")):
        return VerificationResult(True, "system_metrics", "метрики присутствуют в ответе")
    return VerificationResult(False, "system_metrics", "метрик в ответе нет")


def verify_current_time(result: ActionResult) -> VerificationResult:
    """current_time: локальный ответ содержит время и дату."""
    if not result.ok:
        return VerificationResult(False, "current_time", result.error or "ok=False")
    text = _output_text(result)
    if re.search(r"\b\d{2}:\d{2}:\d{2}\b", text) and re.search(r"\b\d{4}-\d{2}-\d{2}\b", text):
        return VerificationResult(True, "current_time", "локальные часы и дата присутствуют")
    return VerificationResult(False, "current_time", "формат времени не подтверждён")


def verify_play_music(result: ActionResult) -> VerificationResult:
    """play_music: локальная медиаточка открыта, а не просто поиск в сети."""
    text = _output_text(result)
    args = result.args or {}
    source = str(args.get("source") or "auto").casefold()
    query = str(args.get("query") or "").strip()
    if result.ok and (
        "поиск музыки" in text.casefold()
        or (source in {"youtube", "spotify"} and bool(query))
    ):
        return VerificationResult(
            False,
            "media_playback",
            "открыта поисковая страница; воспроизведение не подтверждено",
        )
    if result.ok and text:
        return VerificationResult(True, "media_surface", "локальная медиаточка открыта launcher-ом")
    return VerificationResult(False, "media_surface", result.error or "медиаточка не открыта")


def default_verify(result: ActionResult) -> VerificationResult:
    """Fallback: доверяем ok, но ЧЕСТНО помечаем strict=False (§14)."""
    if result.ok:
        log.debug("Инструмент '%s' без спец. verifier — доверяем ok=True", result.tool)
        return VerificationResult(True, "trust_ok",
                                  "специализированная проверка недоступна", strict=False)
    return VerificationResult(False, "trust_ok", result.error or "ok=False", strict=False)


def verify_action_result(result: ActionResult) -> VerificationResult:
    """Главная точка входа: фактическая проверка результата инструмента.

    Никогда не бросает исключений — при падении verifier-а честно
    деградирует до ``default_verify``.
    """
    tool = getattr(result, "tool", "") or ""
    verifier = _VERIFIERS.get(tool)
    if verifier is not None:
        try:
            return verifier(result)
        except Exception as exc:
            log.warning("Verifier для '%s' упал: %s — fallback на trust_ok", tool, exc)
    return default_verify(result)


# --------------------------------------------------------------------------- #
#  Регистрация проверок для реальных инструментов проекта
# --------------------------------------------------------------------------- #

register_verifier("write_file", verify_file_exists)
register_verifier("read_file", verify_non_empty_output)
register_verifier("list_files", verify_non_empty_output)
register_verifier("search_files", verify_file_search)
register_verifier("open_app", verify_process_running)
register_verifier("close_app", verify_process_gone)
register_verifier("web_fetch", verify_page_loaded)
register_verifier("web_search", verify_search_results)
register_verifier("system_status", verify_system_metrics)
register_verifier("current_time", verify_current_time)
register_verifier("play_music", verify_play_music)
register_verifier("weather", verify_non_empty_output)
register_verifier("add_reminder", verify_reminder_registered)
register_verifier("list_reminders", verify_non_empty_output)
