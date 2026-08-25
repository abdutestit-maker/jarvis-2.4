"""Canonical lazy world state with OS observers, provenance and TTL cache."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import platform
import re
import socket
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from .models import FactType, WorldFact
from .store import ExecutiveStore


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | str | None) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class DomainObservation:
    """One bounded acquisition from a concrete local source."""

    domain: str
    data: dict[str, Any] = field(default_factory=dict)
    source: str = "local_os"
    observed_at: datetime = field(default_factory=_utcnow)
    ttl_seconds: float = 15.0
    confidence: float = 1.0
    evidence: tuple[str, ...] = ()
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class WorldQuery:
    text: str
    domains: tuple[str, ...] = ()
    current: bool = True
    confidence: float = 0.0
    options: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class WorldQueryResult:
    query: WorldQuery
    observations: list[WorldFact] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.observations) and all(not fact.error for fact in self.observations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query.text,
            "domains": list(self.query.domains),
            "current": self.query.current,
            "confidence": self.query.confidence,
            "observations": [fact.to_dict() for fact in self.observations],
        }

    def render(self) -> str:
        if not self.query.current:
            return "Запрос относится к прошлому состоянию; текущий снимок системы этого не доказывает."
        if not self.observations:
            return "Для этого запроса не определена локальная область наблюдения."
        failures = [fact for fact in self.observations if fact.error]
        if failures:
            details = "; ".join(f"{fact.domain}: {fact.error}" for fact in failures)
            return f"Текущее состояние получить не удалось: {details}."
        return " ".join(part for part in (_render_fact(fact) for fact in self.observations) if part)


class WorldQueryRouter:
    """Lightweight concept router for read-only current-state questions."""

    _HISTORY = re.compile(
        r"(?i)(?:\bвчера\b|\bраньше\b|\bистори\w*|\bкогда\b|\bнедавно\b|"
        r"\bзапускал[аи]?\b|\bоткрывал[аи]?\b|\bused\s+to\b|\byesterday\b)"
    )
    _CURRENT = re.compile(r"(?i)(?:\bсейчас\b|\bтекущ\w*|\bв\s+данный\s+момент\b|\bnow\b|\bcurrently\b)")
    _PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
        ("screen", re.compile(r"(?i)(?:что|покажи|видно).{0,30}(?:на\s+экране|дисплее)|скриншот|screen")),
        ("filesystem", re.compile(r"(?i)(?:файл|pdf|docx|xlsx|загрузк|downloads|documents|desktop).{0,50}(?:найд|последн|свеж|недав)|(?:найд|последн).{0,50}(?:файл|pdf|docx|xlsx)")),
        ("storage", re.compile(r"(?i)(?:диск|\bтом(?:а|ов|ы)\b|накопител|хранилищ|storage|drive|volume|свободн.{0,20}мест|мест.{0,20}(?:свобод|остал)|занят.{0,20}(?:диск|мест))")),
        ("browser", re.compile(r"(?i)(?:браузер|chrome|edge|firefox|opera|vivaldi|browser).{0,40}(?:запущ|открыт|работа|сейчас)|(?:запущ|открыт).{0,40}(?:браузер|chrome|edge|firefox|opera|vivaldi)")),
        ("desktop", re.compile(r"(?i)(?:что|какие).{0,30}(?:открыт|активн)(?:.{0,20}(?:программ|окн))?|(?:программ|окн).{0,30}(?:открыт|активн|видим)|(?:видим|активн).{0,20}(?:окн|программ)|active\s+window|visible\s+windows")),
        ("processes", re.compile(r"(?i)(?:процесс|задач|process|что\s+запущено|программ).{0,30}(?:запущ|работа|ресурс)|(?:запущен|работает).{0,30}(?:процесс|программ)")),
        ("applications", re.compile(r"(?i)(?:установлен|инсталлирован).{0,30}(?:программ|приложен)|installed\s+apps")),
        (
            "machine",
            re.compile(
                r"(?i)(?:cpu|процессор|оператив|\bram\b|"
                r"памят.{0,20}(?:комп|систем|занят|свобод|использ)|"
                r"(?:комп|систем).{0,20}памят|батаре|заряд|uptime|аптайм|"
                r"комп.{0,20}тормоз|систем.{0,20}(?:нагруз|ресурс)|"
                r"ресурс.{0,20}(?:комп|систем))"
            ),
        ),
        ("audio", re.compile(r"(?i)(?:громкост|mute|звук|аудио|музык).{0,30}(?:сейчас|игра|уров|включ|выключ|state|status)")),
    )

    def route(self, text: str) -> WorldQuery:
        raw = " ".join((text or "").casefold().replace("ё", "е").split())
        domains = [domain for domain, pattern in self._PATTERNS if pattern.search(raw)]
        if "screen" in domains:
            domains = [domain for domain in domains if domain != "desktop"]
        historical = bool(self._HISTORY.search(raw) and not self._CURRENT.search(raw))
        # A past file date is still answerable from current filesystem metadata;
        # a past application state needs episodic memory instead of a process snapshot.
        if historical and "filesystem" not in domains:
            return WorldQuery(raw, current=False, confidence=0.95)
        if "тормоз" in raw or "slow" in raw:
            domains = ["machine", "processes"]
        options: dict[str, Any] = {}
        if "filesystem" in domains:
            if "pdf" in raw:
                options["extension"] = ".pdf"
            if "загруз" in raw or "download" in raw:
                options["roots"] = ("downloads",)
            options["sort"] = "modified_desc"
            options["limit"] = 1 if ("последн" in raw or "latest" in raw) else 10
            if "вчера" in raw or "yesterday" in raw:
                local_now = datetime.now().astimezone()
                start_local = (local_now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                options["modified_after"] = start_local.astimezone(timezone.utc).isoformat()
                options["modified_before"] = (start_local + timedelta(days=1)).astimezone(timezone.utc).isoformat()
        return WorldQuery(
            raw,
            tuple(dict.fromkeys(domains)),
            current=True,
            confidence=0.92 if domains else 0.0,
            options=options,
        )


class LocalWorldObserver:
    """Bounded, on-demand OS acquisition. Construction performs no probes."""

    _TTLS = {
        "screen": 2.0, "desktop": 3.0, "processes": 5.0,
        "browser": 5.0, "audio": 5.0, "machine": 10.0,
        "storage": 15.0, "filesystem": 10.0, "applications": 300.0,
    }

    def __init__(self, *, roots: Optional[Mapping[str, Path | str]] = None) -> None:
        defaults = {
            "documents": Path.home() / "Documents",
            "downloads": Path.home() / "Downloads",
            "desktop": Path.home() / "Desktop",
        }
        self.roots = {
            name: Path(value).expanduser().resolve()
            for name, value in {**defaults, **dict(roots or {})}.items()
        }

    def observe(self, domain: str, **options: Any) -> DomainObservation:
        name = str(domain or "").casefold()
        method = getattr(self, f"_observe_{name}", None)
        if not callable(method):
            return DomainObservation(name, error=f"unsupported observation domain: {name}")
        try:
            data, source, evidence = method(**options)
            return DomainObservation(
                domain=name, data=data, source=source,
                ttl_seconds=self._TTLS.get(name, 15.0), evidence=tuple(evidence),
            )
        except Exception as exc:
            return DomainObservation(
                domain=name, data={}, source="local_os",
                ttl_seconds=self._TTLS.get(name, 15.0), confidence=0.0,
                error=f"{type(exc).__name__}: {exc}",
            )

    @staticmethod
    def _observe_machine(**_: Any) -> tuple[dict[str, Any], str, list[str]]:
        import psutil

        memory = psutil.virtual_memory()
        cpu_freq = psutil.cpu_freq()
        adapters = []
        for name, addresses in psutil.net_if_addrs().items():
            adapters.append({"name": name, "addresses": [str(item.address) for item in addresses if str(item.address)][:4]})
        battery = psutil.sensors_battery()
        payload = {
            "os": {"system": platform.system(), "release": platform.release(), "version": platform.version()},
            "hostname": socket.gethostname(),
            "uptime_seconds": max(0.0, time.time() - psutil.boot_time()),
            "cpu": {
                "used_percent": float(psutil.cpu_percent(interval=0.05)),
                "logical_count": int(psutil.cpu_count(logical=True) or 0),
                "physical_count": int(psutil.cpu_count(logical=False) or 0),
                "frequency_mhz": float(cpu_freq.current) if cpu_freq else None,
            },
            "memory": {
                "total_bytes": int(memory.total), "available_bytes": int(memory.available),
                "used_bytes": int(memory.used), "used_percent": float(memory.percent),
            },
            "battery": None if battery is None else {
                "percent": float(battery.percent), "plugged": bool(battery.power_plugged),
                "seconds_left": int(battery.secsleft),
            },
            "network_adapters": adapters[:16],
        }
        return payload, "psutil", ["psutil.cpu_percent", "psutil.virtual_memory", "psutil.boot_time"]

    @staticmethod
    def _drive_type(path: str) -> int | None:
        if os.name != "nt":
            return None
        try:
            return int(ctypes.windll.kernel32.GetDriveTypeW(str(path)))
        except Exception:
            return None

    def _observe_storage(self, **_: Any) -> tuple[dict[str, Any], str, list[str]]:
        import psutil

        volumes: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        seen: set[str] = set()
        for partition in psutil.disk_partitions(all=False):
            mountpoint = str(partition.mountpoint)
            if not mountpoint or mountpoint.casefold() in seen:
                continue
            seen.add(mountpoint.casefold())
            try:
                usage = psutil.disk_usage(mountpoint)
                volumes.append({
                    "device": str(partition.device), "mountpoint": mountpoint,
                    "fstype": str(partition.fstype), "total_bytes": int(usage.total),
                    "used_bytes": int(usage.used), "free_bytes": int(usage.free),
                    "used_percent": float(usage.percent), "removable": self._drive_type(mountpoint) == 2,
                })
            except (OSError, PermissionError) as exc:
                errors.append({"mountpoint": mountpoint, "error": f"{type(exc).__name__}: {exc}"})
        if not volumes:
            raise RuntimeError(f"no accessible logical volumes; errors={errors[:3]}")
        return {"volumes": volumes, "errors": errors}, "psutil.disk_partitions", ["psutil.disk_partitions", "psutil.disk_usage"]

    @staticmethod
    def _observe_processes(
        *, limit: int = 128, include_executable: bool = False, **_: Any,
    ) -> tuple[dict[str, Any], str, list[str]]:
        import psutil

        items: list[dict[str, Any]] = []
        denied = 0
        attributes = ["pid", "name", "status", "cpu_percent", "memory_percent"]
        if include_executable:
            attributes.append("exe")
        for process in psutil.process_iter(attributes):
            try:
                info = process.info
                items.append({
                    "pid": int(info.get("pid") or process.pid), "name": str(info.get("name") or ""),
                    "status": str(info.get("status") or "unknown"),
                    "cpu_percent": float(info.get("cpu_percent") or 0.0),
                    "memory_percent": round(float(info.get("memory_percent") or 0.0), 3),
                })
                if include_executable:
                    items[-1]["executable"] = str(info.get("exe") or "")
            except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                denied += 1
        items.sort(key=lambda item: (item["cpu_percent"], item["memory_percent"]), reverse=True)
        bounded = items[: max(1, min(int(limit), 4096))]
        return {
            "total_count": len(items), "processes": bounded,
            "truncated": len(bounded) < len(items), "access_denied": denied,
        }, "psutil.process_iter", ["psutil.process_iter"]

    @staticmethod
    def _observe_desktop(*, limit: int = 64, **_: Any) -> tuple[dict[str, Any], str, list[str]]:
        import psutil
        from core.platform.windows import NativeWindowsProvider

        provider = NativeWindowsProvider()
        windows_result = provider.invoke("window.list")
        active_result = provider.invoke("window.active")
        if not windows_result.ok or not active_result.ok:
            raise RuntimeError(windows_result.error or active_result.error or "window observation unavailable")
        pids = {int(item.get("process_id") or 0) for item in list(windows_result.value or []) if int(item.get("process_id") or 0)}
        process_names: dict[int, str] = {}
        for pid in pids:
            try:
                process_names[pid] = str(psutil.Process(pid).name())
            except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                process_names[pid] = ""
        windows = []
        for item in list(windows_result.value or [])[: max(1, min(int(limit), 256))]:
            pid = int(item.get("process_id") or 0)
            windows.append({
                "handle": int(item.get("handle") or 0), "title": str(item.get("title") or ""),
                "process_id": pid, "process_name": process_names.get(pid, ""),
            })
        active_raw = dict(active_result.value or {})
        active_pid = int(active_raw.get("process_id") or 0)
        active = {
            "handle": int(active_raw.get("handle") or 0), "title": str(active_raw.get("title") or ""),
            "process_id": active_pid, "process_name": process_names.get(active_pid, ""),
        }
        return {
            "active_window": active, "windows": windows,
            "truncated": len(windows) < len(windows_result.value or []),
        }, "native_windows", ["EnumWindows", "GetForegroundWindow", "psutil.Process"]

    def _observe_browser(self, **options: Any) -> tuple[dict[str, Any], str, list[str]]:
        browser_names = {"chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "vivaldi.exe", "browser.exe"}
        process_data, _, _ = self._observe_processes(limit=4096)
        processes = [item for item in process_data["processes"] if item["name"].casefold() in browser_names]
        windows: list[dict[str, Any]] = []
        active: dict[str, Any] = {}
        try:
            desktop, _, _ = self._observe_desktop(limit=int(options.get("limit", 64)))
            windows = [item for item in desktop["windows"] if item["process_name"].casefold() in browser_names]
            if desktop["active_window"].get("process_name", "").casefold() in browser_names:
                active = desktop["active_window"]
        except Exception:
            pass
        return {
            "running": bool(processes), "processes": processes[:32],
            "windows": windows[:32], "active_window": active,
        }, "native_windows+psutil", ["psutil.process_iter", "EnumWindows"]

    def _observe_filesystem(
        self, *, roots: Sequence[str] = ("documents", "downloads", "desktop"),
        extension: str = "", sort: str = "modified_desc", limit: int = 25,
        max_files: int = 2000, max_depth: int = 5, timeout_seconds: float = 0.5,
        modified_after: str = "", modified_before: str = "",
        cancel_event: threading.Event | None = None, **_: Any,
    ) -> tuple[dict[str, Any], str, list[str]]:
        selected = [self.roots[name] for name in roots if name in self.roots]
        if not selected:
            raise ValueError("no allowed filesystem roots selected")
        suffix = extension.casefold().strip()
        if suffix and not suffix.startswith("."):
            suffix = f".{suffix}"
        deadline = time.monotonic() + max(0.05, min(float(timeout_seconds), 3.0))
        after = _as_utc(modified_after)
        before = _as_utc(modified_before)
        queue: deque[tuple[Path, int]] = deque((root, 0) for root in selected if root.exists())
        files: list[dict[str, Any]] = []
        scanned_files = 0
        scanned_dirs = 0
        stopped_reason = "complete"
        while queue:
            if cancel_event is not None and cancel_event.is_set():
                stopped_reason = "cancelled"
                break
            if time.monotonic() >= deadline:
                stopped_reason = "timeout"
                break
            directory, depth = queue.popleft()
            scanned_dirs += 1
            try:
                with os.scandir(directory) as entries:
                    for entry in entries:
                        if cancel_event is not None and cancel_event.is_set():
                            stopped_reason = "cancelled"
                            break
                        try:
                            if entry.is_dir(follow_symlinks=False) and depth < max(0, int(max_depth)):
                                queue.append((Path(entry.path), depth + 1))
                            elif entry.is_file(follow_symlinks=False):
                                scanned_files += 1
                                if scanned_files > max(1, int(max_files)):
                                    stopped_reason = "file_limit"
                                    queue.clear()
                                    break
                                path = Path(entry.path)
                                if suffix and path.suffix.casefold() != suffix:
                                    continue
                                stat = entry.stat(follow_symlinks=False)
                                modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                                if after is not None and modified < after:
                                    continue
                                if before is not None and modified >= before:
                                    continue
                                files.append({
                                    "path": str(path), "name": path.name, "size_bytes": int(stat.st_size),
                                    "modified_at": modified.isoformat(),
                                    "root": next((name for name, root in self.roots.items() if path == root or root in path.parents), ""),
                                })
                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError):
                continue
        if sort == "modified_desc":
            files.sort(key=lambda item: item["modified_at"], reverse=True)
        else:
            files.sort(key=lambda item: item["path"].casefold())
        bounded = files[: max(1, min(int(limit), 100))]
        return {
            "files": bounded, "scanned_files": min(scanned_files, max(1, int(max_files))),
            "scanned_directories": scanned_dirs,
            "truncated": len(files) > len(bounded) or stopped_reason != "complete",
            "stopped_reason": stopped_reason, "roots": [str(root) for root in selected],
        }, "os.scandir", ["allowed user roots", "bounded os.scandir"]

    def _observe_screen(self, *, ocr: bool = False, **_: Any) -> tuple[dict[str, Any], str, list[str]]:
        import mss

        with mss.mss() as capture:
            frame = capture.grab(capture.monitors[0])
            digest = hashlib.sha256(bytes(frame.rgb)).hexdigest()
            monitor_count = max(0, len(capture.monitors) - 1)
        active: dict[str, Any] = {}
        try:
            desktop, _, _ = self._observe_desktop(limit=1)
            active = desktop["active_window"]
        except Exception:
            pass
        text = ""
        if ocr:
            try:
                import pytesseract
                text = str(pytesseract.image_to_string(frame)).strip()[:2000]
            except Exception:
                text = ""
        return {
            "physical": True, "width": int(frame.width), "height": int(frame.height),
            "monitor_count": monitor_count, "image_sha256": digest,
            "active_window": active, "ocr_text": text,
        }, "mss", ["physical desktop capture", "SHA-256 frame digest"]

    @staticmethod
    def _observe_audio(**_: Any) -> tuple[dict[str, Any], str, list[str]]:
        from core.verifier import _active_audio_sessions

        sessions = _active_audio_sessions()
        payload: dict[str, Any] = {"playback_active": bool(sessions), "active_sessions": sessions[:16]}
        try:
            from core.actions.system import _get_volume_interface
            volume = _get_volume_interface()
            if volume is not None:
                payload["volume_percent"] = round(float(volume.GetMasterVolumeLevelScalar()) * 100, 1)
                payload["muted"] = bool(volume.GetMute())
        except Exception:
            pass
        return payload, "windows_core_audio", ["Windows audio sessions", "IAudioEndpointVolume"]

    @staticmethod
    def _observe_applications(*, limit: int = 256, **_: Any) -> tuple[dict[str, Any], str, list[str]]:
        if os.name != "nt":
            raise RuntimeError("installed application registry is Windows-only")
        import winreg

        locations = (
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        )
        applications: dict[str, dict[str, Any]] = {}
        for hive, key_path in locations:
            try:
                with winreg.OpenKey(hive, key_path) as parent:
                    for index in range(winreg.QueryInfoKey(parent)[0]):
                        try:
                            child_name = winreg.EnumKey(parent, index)
                            with winreg.OpenKey(parent, child_name) as child:
                                name = str(winreg.QueryValueEx(child, "DisplayName")[0]).strip()
                                if not name:
                                    continue
                                def read(field_name: str) -> str:
                                    try:
                                        return str(winreg.QueryValueEx(child, field_name)[0])
                                    except OSError:
                                        return ""
                                applications[name.casefold()] = {
                                    "name": name, "version": read("DisplayVersion"),
                                    "publisher": read("Publisher"),
                                }
                        except OSError:
                            continue
            except OSError:
                continue
        ordered = sorted(applications.values(), key=lambda item: item["name"].casefold())
        bounded = ordered[: max(1, min(int(limit), 512))]
        return {
            "applications": bounded, "total_count": len(ordered),
            "truncated": len(bounded) < len(ordered),
        }, "windows_registry", ["Windows uninstall registry"]


class UnifiedWorldState:
    """Single owner for current facts; volatile OS state remains memory-only."""

    def __init__(
        self, store: ExecutiveStore | str | Path | None = None, *, observer: Any | None = None,
        router: WorldQueryRouter | None = None, clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store if isinstance(store, ExecutiveStore) else ExecutiveStore(store or "data/executive")
        self.observer = observer or LocalWorldObserver()
        self.router = router or WorldQueryRouter()
        self._clock = clock or _utcnow
        self._lock = threading.RLock()
        raw = self.store.read("world", [])
        self._facts = {
            str(item["key"]): WorldFact.from_dict(item)
            for item in raw if isinstance(item, dict) and item.get("key")
        }

    def _save(self) -> None:
        self.store.write("world", [fact.to_dict() for fact in self._facts.values() if not fact.ephemeral])

    def observe(
        self, key: str, value: Any, *, source: str, confidence: float = 0.7,
        valid_until: Optional[str] = None, volatility: str = "normal",
        domain: str = "general", fact_type: FactType | str = FactType.INFERRED,
        ttl_seconds: float | None = None, evidence: Sequence[str] = (),
        error: str | None = None, ephemeral: bool = False,
        observed_at: datetime | str | None = None,
    ) -> WorldFact:
        key = " ".join((key or "").split()).strip()
        if not key:
            raise ValueError("world fact key is required")
        moment = _as_utc(observed_at) or self._clock()
        ttl = float(ttl_seconds) if ttl_seconds is not None else None
        deadline = valid_until or ((moment + timedelta(seconds=max(0.0, ttl))).isoformat() if ttl is not None else None)
        kind = fact_type.value if isinstance(fact_type, FactType) else str(fact_type)
        with self._lock:
            previous = self._facts.get(key)
            fact = WorldFact(
                key=key, value=value, source=source, observed_at=moment.isoformat(),
                valid_until=deadline, confidence=max(0.0, min(1.0, confidence)),
                volatility=volatility, supersedes=previous.observed_at if previous else None,
                domain=domain, fact_type=kind, ttl_seconds=ttl,
                evidence=[str(item) for item in evidence], error=error, ephemeral=bool(ephemeral),
            )
            self._facts[key] = fact
            if not fact.ephemeral:
                self._save()
            return fact

    update = observe

    def observe_domain(self, domain: str, *, force: bool = False, **options: Any) -> WorldFact:
        domain = str(domain or "").casefold()
        cache_key = self._cache_key(domain, options)
        if not force:
            cached = self.get(cache_key)
            if cached is not None:
                return cached
        try:
            sample = self.observer.observe(domain, **options)
        except Exception as exc:
            sample = DomainObservation(
                domain=domain, data={}, confidence=0.0,
                error=f"{type(exc).__name__}: {exc}",
            )
        return self.observe(
            cache_key, sample.data if sample.ok else None, source=sample.source,
            confidence=sample.confidence, volatility="volatile", domain=domain,
            fact_type=FactType.OBSERVED, ttl_seconds=sample.ttl_seconds,
            evidence=sample.evidence, error=sample.error, ephemeral=True,
            observed_at=sample.observed_at,
        )

    def query(self, text: str, *, force: bool = False) -> WorldQueryResult:
        route = self.router.route(text)
        if not route.current or not route.domains:
            return WorldQueryResult(route)
        return WorldQueryResult(route, [
            self.observe_domain(domain, force=force, **dict(route.options))
            for domain in route.domains
        ])

    def context_for(self, query: str) -> dict[str, Any]:
        """Return only query-relevant, locally reduced facts for model context."""
        route = self.router.route(query)
        if not route.current or not route.domains:
            return {}
        allowed = set(route.domains)
        context: dict[str, Any] = {}
        for key, fact in self.current().items():
            if fact.domain not in allowed or fact.error:
                continue
            context[key] = {
                "domain": fact.domain, "fact_type": fact.fact_type, "source": fact.source,
                "observed_at": fact.observed_at, "freshness": fact.freshness(self._clock()),
                "value": _compact_value(fact.domain, fact.value),
            }
        return context

    def get(self, key: str, *, include_expired: bool = False) -> Optional[WorldFact]:
        fact = self._facts.get(key)
        if fact is None or (not include_expired and self._expired(fact)):
            return None
        return fact

    def current(self) -> dict[str, WorldFact]:
        return {key: fact for key, fact in self._facts.items() if not self._expired(fact)}

    def snapshot(self) -> dict[str, Any]:
        return {key: fact.value for key, fact in self.current().items()}

    def diff_since(self, since: str | datetime) -> list[dict[str, Any]]:
        moment = _as_utc(since)
        if moment is None:
            return []
        return [
            fact.to_dict() for fact in self._facts.values()
            if (_as_utc(fact.observed_at) or moment) > moment and not self._expired(fact)
        ]

    def expire(self, *, now: Optional[datetime] = None) -> int:
        current = now or self._clock()
        expired = [key for key, fact in self._facts.items() if self._expired(fact, now=current)]
        for key in expired:
            self._facts.pop(key, None)
        if expired:
            self._save()
        return len(expired)

    def _expired(self, fact: WorldFact, *, now: datetime | None = None) -> bool:
        deadline = _as_utc(fact.valid_until)
        return bool(deadline and deadline <= (now or self._clock()))

    @staticmethod
    def _cache_key(domain: str, options: Mapping[str, Any]) -> str:
        relevant = {key: value for key, value in options.items() if key not in {"cancel_event", "force"}}
        if not relevant:
            return f"world.{domain}"
        serialized = json.dumps(relevant, ensure_ascii=False, sort_keys=True, default=str)
        suffix = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:12]
        return f"world.{domain}.{suffix}"


def _human_bytes(value: Any) -> str:
    amount = float(value or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(amount) < 1024.0 or unit == "TB":
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024.0
    return f"{int(value or 0)} B"


def _render_fact(fact: WorldFact) -> str:
    value = fact.value if isinstance(fact.value, Mapping) else {}
    if fact.domain == "storage":
        return "Диски: " + "; ".join(
            f"{item.get('mountpoint')}: {_human_bytes(item.get('free_bytes'))} свободно из {_human_bytes(item.get('total_bytes'))}"
            for item in value.get("volumes", [])
        ) + "."
    if fact.domain == "machine":
        cpu, memory = value.get("cpu", {}), value.get("memory", {})
        return (
            f"CPU сейчас: {cpu.get('used_percent', 0):g}%. "
            f"RAM: {memory.get('used_percent', 0):g}% занято, {_human_bytes(memory.get('available_bytes'))} доступно."
        )
    if fact.domain == "processes":
        items = value.get("processes", [])[:10]
        names = ", ".join(str(item.get("name") or item.get("pid")) for item in items)
        return f"Запущено процессов: {value.get('total_count', len(items))}. Верх списка по нагрузке: {names}."
    if fact.domain == "desktop":
        active, windows = value.get("active_window", {}), value.get("windows", [])
        names = ", ".join(str(item.get("title") or item.get("process_name")) for item in windows[:10])
        return f"Активное окно: {active.get('title') or 'не определено'}. Видимые окна: {names or 'не обнаружены'}."
    if fact.domain == "filesystem":
        files = value.get("files", [])
        return "Найдены файлы: " + (", ".join(str(item.get("path")) for item in files) if files else "совпадений нет") + "."
    if fact.domain == "browser":
        windows = value.get("windows", [])
        titles = ", ".join(str(item.get("title")) for item in windows[:10])
        return f"Браузер {'запущен' if value.get('running') else 'не запущен'}." + (f" Видимые страницы: {titles}." if titles else "")
    if fact.domain == "screen":
        active, text = value.get("active_window", {}), str(value.get("ocr_text") or "").strip()
        return f"Экран наблюдён физически. Активное окно: {active.get('title') or 'не определено'}." + (f" Текст: {text}" if text else "")
    if fact.domain == "audio":
        return f"Воспроизведение {'активно' if value.get('playback_active') else 'не наблюдается'}."
    if fact.domain == "applications":
        return "Установленные приложения: " + ", ".join(str(item.get("name")) for item in value.get("applications", [])[:20]) + "."
    return f"{fact.domain}: {value}."


def _compact_value(domain: str, value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value
    compact = dict(value)
    if domain == "processes":
        compact["processes"] = [
            {key: item.get(key) for key in ("pid", "name", "status", "cpu_percent", "memory_percent")}
            for item in list(compact.get("processes", []))[:10]
        ]
    elif domain in {"desktop", "browser"}:
        compact["windows"] = list(compact.get("windows", []))[:10]
        compact["processes"] = [
            {key: item.get(key) for key in ("pid", "name")}
            for item in list(compact.get("processes", []))[:10]
        ]
    elif domain == "filesystem":
        compact["files"] = list(compact.get("files", []))[:10]
    elif domain == "applications":
        compact["applications"] = list(compact.get("applications", []))[:20]
    return compact


WorldState = UnifiedWorldState
