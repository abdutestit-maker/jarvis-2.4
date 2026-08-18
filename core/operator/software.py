"""Trusted software discovery, installation evidence and reversible checkpoints."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sysconfig
import time
import urllib.parse
import urllib.request
import uuid
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable
from core.security.atomic import atomic_json_write


@dataclass
class SoftwareCandidate:
    name: str
    package_id: str = ""
    official_source: str = ""
    source_kind: str = "verified_release"
    package_manager: str = ""
    installer_type: str = "unknown"
    architecture: str = "unknown"
    version: str = ""
    publisher: str = ""
    signature_expected: bool = True
    trusted: bool = False
    download_url: str = ""
    sha256: str = ""
    expected_executable: str = ""
    silent_args: list[str] = field(default_factory=list)
    launch_args: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SoftwareResolver:
    """Resolves package manager → official site → official GitHub → release."""

    _rank = {
        "package_manager": 0,
        "official_site": 1,
        "official_github": 2,
        "verified_release": 3,
        "third_party": 99,
    }

    def __init__(self, runner: Callable[..., Any] | None = None) -> None:
        self._runner = runner or subprocess.run

    def rank_candidates(self, candidates: Iterable[SoftwareCandidate]) -> list[SoftwareCandidate]:
        trusted = [item for item in candidates if item.trusted and self._source_is_trusted(item)]
        return sorted(trusted, key=lambda item: (
            self._rank.get(item.source_kind, 50),
            item.name.casefold(),
            item.package_id.casefold(),
        ))

    @staticmethod
    def _source_is_trusted(candidate: SoftwareCandidate) -> bool:
        if candidate.package_manager == "winget" and candidate.official_source.startswith("winget://"):
            return bool(candidate.package_id)
        source = candidate.official_source or candidate.download_url
        parsed = urllib.parse.urlparse(source)
        if parsed.scheme != "https" or not parsed.hostname:
            return False
        if candidate.source_kind == "official_github":
            return parsed.hostname.casefold() in {"github.com", "objects.githubusercontent.com"}
        return candidate.source_kind in {"official_site", "verified_release"}

    def resolve(self, name: str, *, package_id: str | None = None,
                candidates: Iterable[SoftwareCandidate] | None = None) -> SoftwareCandidate | None:
        if candidates is not None:
            ranked = self.rank_candidates(candidates)
            return ranked[0] if ranked else None
        return self.resolve_winget(name, package_id=package_id)

    def resolve_winget(self, name: str, *, package_id: str | None = None) -> SoftwareCandidate | None:
        resolved_id = package_id or self._winget_search_id(name)
        if not resolved_id:
            return None
        command = [
            "winget", "show", "--id", resolved_id, "--exact", "--source", "winget",
            "--accept-source-agreements", "--disable-interactivity",
        ]
        done = self._run(command, timeout=90)
        if done["exit_code"] != 0:
            return None
        fields = self._parse_fields(done["stdout"])
        installer_url = fields.get("installer url", "")
        architecture = fields.get("architecture", "") or self._architecture_from_url(installer_url)
        installer_type = fields.get("installer type", fields.get("installer locale", "exe")).casefold()
        if installer_type not in {"msi", "exe", "zip", "portable", "inno", "nullsoft", "burn"}:
            installer_type = "exe"
        if installer_type == "portable":
            installer_type = "zip"
        return SoftwareCandidate(
            name=fields.get("found", name).split("[")[0].strip() or name,
            package_id=resolved_id,
            official_source=f"winget://{resolved_id}",
            source_kind="package_manager",
            package_manager="winget",
            installer_type=installer_type,
            architecture=architecture or "unknown",
            version=fields.get("version", ""),
            publisher=fields.get("publisher", ""),
            signature_expected=True,
            trusted=True,
            download_url=installer_url,
            sha256=fields.get("installer sha256", ""),
        )

    @staticmethod
    def _architecture_from_url(url: str) -> str:
        low = str(url).casefold()
        if re.search(r"(?:^|[._-])arm64(?:[._-]|$)", low):
            return "arm64"
        if re.search(r"(?:^|[._-])(x64|amd64)(?:[._-]|$)", low):
            return "x64"
        if re.search(r"(?:^|[._-])(x86|win32|i386)(?:[._-]|$)", low):
            return "x86"
        return ""

    def _winget_search_id(self, name: str) -> str:
        command = [
            "winget", "search", "--query", name, "--source", "winget",
            "--accept-source-agreements", "--disable-interactivity",
        ]
        done = self._run(command, timeout=90)
        if done["exit_code"] != 0:
            return ""
        for line in done["stdout"].splitlines():
            if not line.strip() or re.match(r"^[\s\-=]+$", line):
                continue
            columns = re.split(r"\s{2,}", line.strip())
            if len(columns) >= 2 and (
                name.casefold() in columns[0].casefold()
                or name.casefold() in columns[1].casefold()
            ):
                return columns[1]
        return ""

    @staticmethod
    def _parse_fields(output: str) -> dict[str, str]:
        aliases = {
            "версия": "version",
            "издатель": "publisher",
            "тип установщика": "installer type",
            "архитектура": "architecture",
            "installer type": "installer type",
            "version": "version",
            "publisher": "publisher",
            "architecture": "architecture",
            "installer url": "installer url",
            "installer sha256": "installer sha256",
            "url-адрес установщика": "installer url",
            "sha256 установщика": "installer sha256",
        }
        fields: dict[str, str] = {}
        for line in output.splitlines():
            match = re.match(r"^\s*([^:]{2,40}):\s*(.+?)\s*$", line)
            if match:
                key = match.group(1).strip().casefold()
                fields[aliases.get(key, key)] = match.group(2).strip()
            else:
                stripped = line.strip()
                low = stripped.casefold()
                for prefix in ("found ", "найдено "):
                    if low.startswith(prefix):
                        fields["found"] = stripped[len(prefix):]
                        break
        return fields

    def _run(self, command: list[str], *, timeout: float) -> dict[str, Any]:
        done = self._runner(
            command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
            shell=False, check=False,
        )
        if isinstance(done, dict):
            return {
                "exit_code": int(done.get("exit_code", done.get("returncode", 1))),
                "stdout": str(done.get("stdout", "")),
                "stderr": str(done.get("stderr", "")),
            }
        return {"exit_code": int(done.returncode), "stdout": done.stdout or "", "stderr": done.stderr or ""}


@dataclass
class InstallationEvidence:
    candidate: dict[str, Any]
    installer_exit: int | None
    installed: bool
    version: str
    executable: str
    signature_status: str
    launched: bool
    process_id: int | None
    window: dict[str, Any] | None
    checks: dict[str, bool]
    verified: bool
    failed_checks: list[str]


class InstallerEngine:
    """Installs known types and proves real installed/launch/window state."""

    def __init__(
        self,
        *,
        runner: Callable[..., Any] | None = None,
        installed_probe: Callable[[SoftwareCandidate], dict[str, Any]] | None = None,
        executable_probe: Callable[[SoftwareCandidate], Path | None] | None = None,
        signature_probe: Callable[[Path], str] | None = None,
        launch_probe: Callable[[Path, SoftwareCandidate], dict[str, Any]] | None = None,
    ) -> None:
        self._runner = runner or subprocess.run
        self._installed_probe = installed_probe or self._probe_installed
        self._executable_probe = executable_probe or self._find_executable
        self._signature_probe = signature_probe or self.authenticode_status
        self._launch_probe = launch_probe or self._launch_and_wait_for_window

    @staticmethod
    def detect_type(source: Path | str) -> str:
        text = str(source)
        if text.casefold().startswith("winget://"):
            return "winget"
        return {".msi": "msi", ".exe": "exe", ".zip": "zip"}.get(
            Path(text).suffix.casefold(), "unknown",
        )

    def install(self, candidate: SoftwareCandidate, *, launch: bool = True,
                portable_directory: Path | str | None = None) -> InstallationEvidence:
        if not candidate.trusted or not SoftwareResolver._source_is_trusted(candidate):
            raise ValueError("software source is not trusted")
        if not self.architecture_supported(candidate.architecture):
            raise ValueError(
                f"installer architecture {candidate.architecture!r} is incompatible "
                f"with host {self._host_architecture()!r}"
            )
        if candidate.package_manager == "winget":
            command = [
                "winget", "install", "--id", candidate.package_id, "--exact", "--source", "winget",
                "--accept-package-agreements", "--accept-source-agreements",
                "--disable-interactivity", "--silent",
            ]
            done = self._run(command, timeout=600)
            return self.verify(candidate, installer_exit=done["exit_code"], launch=launch)

        downloaded = self._download(candidate)
        signature = self._signature_probe(downloaded) if downloaded.suffix.casefold() != ".zip" else "NotApplicable"
        if candidate.signature_expected and signature != "Valid":
            raise ValueError(f"installer signature is not valid: {signature}")
        kind = self.detect_type(downloaded)
        if kind == "msi":
            command = ["msiexec.exe", "/i", str(downloaded), "/qn", "/norestart", *candidate.silent_args]
        elif kind == "exe":
            command = [str(downloaded), *candidate.silent_args]
        elif kind == "zip":
            destination = Path(portable_directory or downloaded.with_suffix(""))
            self._safe_extract(downloaded, destination)
            return self.verify(candidate, installer_exit=0, launch=launch)
        else:
            raise ValueError(f"unsupported installer type: {kind}")
        done = self._run(command, timeout=600)
        return self.verify(candidate, installer_exit=done["exit_code"], launch=launch)

    def verify(self, candidate: SoftwareCandidate, *, installer_exit: int | None,
               launch: bool = True) -> InstallationEvidence:
        installed = self._installed_probe(candidate)
        executable = self._executable_probe(candidate)
        signature = self._signature_probe(executable) if executable and executable.is_file() else "Missing"
        launched = {"launched": False, "pid": None, "window": None}
        if launch and executable and executable.is_file():
            launched = self._launch_probe(executable, candidate)
        checks = {
            "architecture_compatible": self.architecture_supported(candidate.architecture),
            "installed_package": bool(installed.get("installed")),
            "version_detected": bool(installed.get("version")),
            "executable_exists": bool(executable and executable.is_file()),
            "signature": (not candidate.signature_expected) or signature == "Valid",
        }
        if launch:
            checks["application_launched"] = bool(launched.get("launched"))
            checks["window_appeared"] = bool(launched.get("window"))
        failed = [name for name, passed in checks.items() if not passed]
        return InstallationEvidence(
            candidate=candidate.to_dict(),
            installer_exit=installer_exit,
            installed=bool(installed.get("installed")),
            version=str(installed.get("version", "")),
            executable=str(executable or ""),
            signature_status=signature,
            launched=bool(launched.get("launched")),
            process_id=launched.get("pid"),
            window=launched.get("window"),
            checks=checks,
            verified=not failed,
            failed_checks=failed,
        )

    @staticmethod
    def architecture_supported(architecture: str, *, host: str | None = None) -> bool:
        requested = str(architecture or "unknown").casefold().replace("-", "")
        machine = str(host or InstallerEngine._host_architecture()).casefold().replace("-", "")
        if requested in {"", "unknown", "neutral", "any", "all"}:
            return True
        if requested in {"x86", "win32", "i386", "i686"}:
            return machine in {"x86", "i386", "i686", "amd64", "x8664", "arm64", "aarch64"}
        if requested in {"x64", "amd64", "x8664"}:
            return machine in {"amd64", "x8664", "arm64", "aarch64"}
        if requested in {"arm64", "aarch64"}:
            return machine in {"arm64", "aarch64"}
        return False

    @staticmethod
    def _host_architecture() -> str:
        explicit = os.getenv("PROCESSOR_ARCHITEW6432") or os.getenv("PROCESSOR_ARCHITECTURE")
        if explicit:
            return explicit
        detected = platform.machine()
        if detected:
            return detected
        value = sysconfig.get_platform().casefold()
        if "arm64" in value:
            return "arm64"
        if "amd64" in value or "x86_64" in value:
            return "amd64"
        if "win32" in value or value.endswith("x86"):
            return "x86"
        return "unknown"

    def _run(self, command: list[str], *, timeout: float) -> dict[str, Any]:
        done = self._runner(
            command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
            shell=False, check=False,
        )
        if isinstance(done, dict):
            return {"exit_code": int(done.get("exit_code", done.get("returncode", 1))),
                    "stdout": str(done.get("stdout", "")), "stderr": str(done.get("stderr", ""))}
        return {"exit_code": int(done.returncode), "stdout": done.stdout or "", "stderr": done.stderr or ""}

    @staticmethod
    def _download(candidate: SoftwareCandidate) -> Path:
        parsed = urllib.parse.urlparse(candidate.download_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("installer URL must use HTTPS")
        from core.network_guard import assert_safe_url, safe_urlopen
        assert_safe_url(candidate.download_url)
        destination = Path(os.getenv("TEMP", ".")) / "jarvis-installers" / Path(parsed.path).name
        destination.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(candidate.download_url, headers={"User-Agent": "JARVIS/0.1"})
        with safe_urlopen(request, timeout=120) as response, destination.open("wb") as stream:
            remaining = 100 * 1024 * 1024
            while remaining > 0:
                chunk = response.read(min(64 * 1024, remaining + 1))
                if not chunk:
                    break
                if len(chunk) > remaining:
                    raise ValueError("installer exceeds 100 MB limit")
                stream.write(chunk)
                remaining -= len(chunk)
        if candidate.sha256:
            actual = hashlib.sha256(destination.read_bytes()).hexdigest()
            if actual.casefold() != candidate.sha256.casefold():
                destination.unlink(missing_ok=True)
                raise ValueError("installer SHA-256 mismatch")
        return destination

    @staticmethod
    def _safe_extract(archive: Path, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        root = destination.resolve()
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                target = (root / member.filename).resolve()
                if root not in target.parents and target != root:
                    raise ValueError(f"ZIP member escapes destination: {member.filename}")
            bundle.extractall(root)

    @staticmethod
    def authenticode_status(path: Path) -> str:
        if os.name == "nt":
            status = InstallerEngine._win_verify_trust(path)
            if status != "Unavailable":
                return status
        escaped = str(path).replace("'", "''")
        command = [
            "powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
            f"(Get-AuthenticodeSignature -LiteralPath '{escaped}').Status.ToString()",
        ]
        done = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30, check=False, shell=False,
        )
        return (done.stdout or "").strip() or "Unknown"

    @staticmethod
    def _win_verify_trust(path: Path) -> str:
        """Verify an Authenticode signature through the native WinTrust API."""
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [
                    ("Data1", wintypes.DWORD),
                    ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD),
                    ("Data4", ctypes.c_ubyte * 8),
                ]

            class WINTRUST_FILE_INFO(ctypes.Structure):
                _fields_ = [
                    ("cbStruct", wintypes.DWORD),
                    ("pcwszFilePath", wintypes.LPCWSTR),
                    ("hFile", wintypes.HANDLE),
                    ("pgKnownSubject", ctypes.POINTER(GUID)),
                ]

            class WINTRUST_DATA(ctypes.Structure):
                _fields_ = [
                    ("cbStruct", wintypes.DWORD),
                    ("pPolicyCallbackData", wintypes.LPVOID),
                    ("pSIPClientData", wintypes.LPVOID),
                    ("dwUIChoice", wintypes.DWORD),
                    ("fdwRevocationChecks", wintypes.DWORD),
                    ("dwUnionChoice", wintypes.DWORD),
                    ("pFile", ctypes.POINTER(WINTRUST_FILE_INFO)),
                    ("dwStateAction", wintypes.DWORD),
                    ("hWVTStateData", wintypes.HANDLE),
                    ("pwszURLReference", wintypes.LPCWSTR),
                    ("dwProvFlags", wintypes.DWORD),
                    ("dwUIContext", wintypes.DWORD),
                    ("pSignatureSettings", wintypes.LPVOID),
                ]

            action = GUID(
                0x00AAC56B, 0xCD44, 0x11D0,
                (ctypes.c_ubyte * 8)(0x8C, 0xC2, 0x00, 0xC0, 0x4F, 0xC2, 0x95, 0xEE),
            )
            file_info = WINTRUST_FILE_INFO(
                ctypes.sizeof(WINTRUST_FILE_INFO), str(path.resolve()), None, None,
            )
            trust_data = WINTRUST_DATA(
                ctypes.sizeof(WINTRUST_DATA), None, None,
                2,  # WTD_UI_NONE
                0,  # WTD_REVOKE_NONE
                1,  # WTD_CHOICE_FILE
                ctypes.pointer(file_info),
                0, None, None,
                0x00001000,  # WTD_CACHE_ONLY_URL_RETRIEVAL
                0, None,
            )
            verify = ctypes.windll.wintrust.WinVerifyTrust
            verify.argtypes = [wintypes.HWND, ctypes.POINTER(GUID), ctypes.c_void_p]
            verify.restype = ctypes.c_long
            result = int(verify(None, ctypes.byref(action), ctypes.byref(trust_data)))
            return "Valid" if result == 0 else f"Invalid(0x{result & 0xFFFFFFFF:08X})"
        except (AttributeError, OSError, TypeError, ValueError):
            return "Unavailable"

    @staticmethod
    def _probe_installed(candidate: SoftwareCandidate) -> dict[str, Any]:
        if candidate.package_id:
            done = subprocess.run([
                "winget", "list", "--id", candidate.package_id, "--exact", "--source", "winget",
                "--accept-source-agreements", "--disable-interactivity",
            ], capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=90, check=False, shell=False)
            if done.returncode == 0 and candidate.package_id.casefold() in done.stdout.casefold():
                version = ""
                for line in done.stdout.splitlines():
                    if candidate.package_id.casefold() in line.casefold():
                        parts = re.split(r"\s{2,}", line.strip())
                        version = parts[2] if len(parts) > 2 else candidate.version
                        break
                return {"installed": True, "version": version or candidate.version}
        return {"installed": False, "version": ""}

    @staticmethod
    def _find_executable(candidate: SoftwareCandidate) -> Path | None:
        executable_name = candidate.expected_executable or f"{candidate.name}.exe"
        resolved = shutil.which(executable_name)
        if resolved:
            return Path(resolved)
        try:
            import winreg
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                key_path = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{executable_name}"
                try:
                    with winreg.OpenKey(hive, key_path) as key:
                        value = Path(winreg.QueryValueEx(key, "")[0])
                        if value.is_file():
                            return value
                except OSError:
                    continue
        except ImportError:
            pass
        for base in filter(None, (os.getenv("ProgramFiles"), os.getenv("ProgramFiles(x86)"), os.getenv("LOCALAPPDATA"))):
            root = Path(base)
            direct = [
                root / candidate.name / executable_name,
                root / candidate.package_id.split(".")[-1] / executable_name,
            ]
            for path in direct:
                if path.is_file():
                    return path
        return None

    @staticmethod
    def _launch_and_wait_for_window(executable: Path, candidate: SoftwareCandidate) -> dict[str, Any]:
        from core.platform.windows import NativeWindowsProvider
        process = subprocess.Popen([str(executable), *candidate.launch_args], shell=False)
        deadline = time.monotonic() + 20
        window = None
        while time.monotonic() < deadline:
            windows = NativeWindowsProvider.window_list()
            window = next((item for item in windows if item.get("process_id") == process.pid), None)
            if window:
                break
            time.sleep(0.25)
        return {"launched": process.poll() is None or bool(window), "pid": process.pid, "window": window}


@dataclass(frozen=True)
class Checkpoint:
    checkpoint_id: str
    kind: str
    target: str
    existed: bool
    backup: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class CheckpointManager:
    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def backup_file(self, path: Path | str) -> Checkpoint:
        target = Path(path).resolve()
        checkpoint_id = uuid.uuid4().hex
        folder = self.directory / checkpoint_id
        folder.mkdir(parents=True)
        backup = folder / "content.bin"
        existed = target.is_file()
        if existed:
            shutil.copy2(target, backup)
        checkpoint = Checkpoint(checkpoint_id, "file", str(target), existed, str(backup) if existed else "")
        atomic_json_write(folder / "checkpoint.json", asdict(checkpoint))
        return checkpoint

    def backup_registry(self, root: str, path: str, name: str) -> Checkpoint:
        import winreg
        hive = getattr(winreg, root)
        existed, value, kind = False, None, None
        try:
            with winreg.OpenKey(hive, path) as key:
                value, kind = winreg.QueryValueEx(key, name)
                existed = True
        except OSError:
            pass
        return Checkpoint(uuid.uuid4().hex, "registry", f"{root}\\{path}::{name}", existed,
                          metadata={"root": root, "path": path, "name": name,
                                    "value": value, "value_kind": kind})

    def rollback(self, checkpoint: Checkpoint) -> dict[str, Any]:
        if checkpoint.kind == "file":
            target = Path(checkpoint.target)
            if checkpoint.existed:
                shutil.copy2(checkpoint.backup, target)
            elif target.is_file():
                target.unlink()
            return {"restored": target.is_file() == checkpoint.existed, "target": str(target)}
        if checkpoint.kind == "registry":
            import winreg
            data = checkpoint.metadata
            hive = getattr(winreg, data["root"])
            with winreg.CreateKey(hive, data["path"]) as key:
                if checkpoint.existed:
                    winreg.SetValueEx(key, data["name"], 0, data["value_kind"], data["value"])
                else:
                    try:
                        winreg.DeleteValue(key, data["name"])
                    except OSError:
                        pass
            return {"restored": True, "target": checkpoint.target}
        raise ValueError(f"unknown checkpoint kind: {checkpoint.kind}")
