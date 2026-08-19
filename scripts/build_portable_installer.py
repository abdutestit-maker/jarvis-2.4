"""Build a self-contained Windows installer for the local JARVIS runtime.

The stock Tauri NSIS bundler cannot memory-map a multi-gigabyte GGUF on some
Windows hosts.  This builder keeps the same Tauri application and resource
layout, but packages it with the official 7-Zip SFX module.  The archive is
stored (the GGUF is already compressed), so the installer is deterministic and
does not spend hours trying to compress model weights.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APP_BUNDLE = ROOT / "jarvis" / "src-tauri" / "target" / "release"
DEFAULT_OUTPUT = (
    ROOT
    / "jarvis"
    / "src-tauri"
    / "target"
    / "release"
    / "bundle"
    / "nsis"
    / "J.A.R.V.I.S._4.0.0_x64-setup.exe"
)


def _find_7z(explicit: str | None) -> Path:
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    candidates.extend(
        [
            Path(r"C:\Program Files\7-Zip\7z.exe"),
            Path(r"C:\Program Files (x86)\7-Zip\7z.exe"),
        ]
    )
    from_path = shutil.which("7z") or shutil.which("7zz")
    if from_path:
        candidates.append(Path(from_path))
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError("7z.exe is required to build the portable installer")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify_payload(app_bundle: Path) -> None:
    # Legacy marker kept for compatibility checks; v4 payloads use the
    # Ministral GGUF discovered below instead of qwen3-4b-instruct-q5_k_m.gguf.
    required = [
        app_bundle / "jarvis-frontend.exe",
        app_bundle / "resources" / "jarvis-runtime" / "runtime" / "jarvis-backend.exe",
        app_bundle / "resources" / "jarvis-runtime" / "runtime" / "piper" / "piper.exe",
        app_bundle / "resources" / "jarvis-runtime" / "data" / "models",
    ]
    missing = [str(path) for path in required if not path.exists()]
    model_dir = app_bundle / "resources" / "jarvis-runtime" / "data" / "models"
    if not list(model_dir.glob("*.gguf")):
        missing.append(f"{model_dir}/*.gguf")
    voice_dir = model_dir / "piper"
    if not list(voice_dir.glob("*.onnx")):
        missing.append(f"{voice_dir}/*.onnx")
    if missing:
        raise FileNotFoundError("Installer payload is incomplete: " + ", ".join(missing))


def _write_install_files(app_bundle: Path) -> tuple[Path, Path]:
    """Create hidden post-extraction launchers next to the Tauri executable."""
    ps1 = app_bundle / "install.ps1"
    cmd = app_bundle / "install.cmd"
    ps1.write_text(
        r'''$ErrorActionPreference = "Stop"
$app = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $app "jarvis-frontend.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    throw "JARVIS executable is missing: $exe"
}

# A normal shortcut is enough; the backend itself is started by Tauri with
# CREATE_NO_WINDOW, so no terminal window is shown when JARVIS runs.
try {
    $desktop = [Environment]::GetFolderPath("Desktop")
    if ($desktop) {
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut((Join-Path $desktop "J.A.R.V.I.S..lnk"))
        $shortcut.TargetPath = $exe
        $shortcut.WorkingDirectory = $app
        $shortcut.IconLocation = "$exe,0"
        $shortcut.Save()
    }
} catch {
    # A locked or redirected desktop must not prevent the application launch.
}

Start-Process -FilePath $exe -WorkingDirectory $app
''',
        encoding="utf-8",
    )
    cmd.write_text(
        '@echo off\r\npowershell.exe -NoProfile -WindowStyle Hidden '
        '-ExecutionPolicy Bypass -File "%~dp0install.ps1"\r\n',
        encoding="ascii",
    )
    return ps1, cmd


def build(app_bundle: Path, output: Path, seven_zip: Path) -> dict[str, object]:
    app_bundle = app_bundle.resolve()
    output = output.resolve()
    _verify_payload(app_bundle)
    output.parent.mkdir(parents=True, exist_ok=True)

    sfx = seven_zip.with_name("7z.sfx")
    if not sfx.exists():
        raise FileNotFoundError(f"7z.sfx is required next to {seven_zip}")

    ps1, cmd = _write_install_files(app_bundle)
    archive_fd, archive_name = tempfile.mkstemp(prefix="jarvis-payload-", suffix=".7z")
    os.close(archive_fd)
    archive = Path(archive_name)
    archive.unlink(missing_ok=True)
    config_fd, config_name = tempfile.mkstemp(prefix="jarvis-sfx-", suffix=".txt")
    os.close(config_fd)
    config = Path(config_name)
    try:
        # The model is already quantized; Copy mode avoids wasteful recompression
        # and lets 7-Zip handle files larger than the 32-bit NSIS mmap limit.
        command = [
            str(seven_zip),
            "a",
            "-t7z",
            "-mx=0",
            "-m0=Copy",
            "-ms=off",
            "-mmt=on",
            str(archive),
            "jarvis-frontend.exe",
            "install.cmd",
            "install.ps1",
            "resources",
        ]
        subprocess.run(command, cwd=app_bundle, check=True)
        config.write_text(
            ';!@Install@!UTF-8!\n'
            'Title="J.A.R.V.I.S. 4.0.0"\n'
            'InstallPath="%LOCALAPPDATA%\\JARVIS"\n'
            'RunProgram="powershell.exe -NoProfile -WindowStyle Hidden '
            '-ExecutionPolicy Bypass -File install.ps1"\n'
            ';!@InstallEnd@!\n',
            encoding="utf-8",
        )
        with output.open("wb") as target:
            for part in (sfx, config, archive):
                with part.open("rb") as source:
                    shutil.copyfileobj(source, target, length=8 * 1024 * 1024)
    finally:
        ps1.unlink(missing_ok=True)
        cmd.unlink(missing_ok=True)
        archive.unlink(missing_ok=True)
        config.unlink(missing_ok=True)

    result = {
        "installer": str(output),
        "size_bytes": output.stat().st_size,
        "sha256": _sha256(output),
        "payload_root": str(app_bundle),
        "installer_type": "7zip_sfx",
        "install_path": r"%LOCALAPPDATA%\JARVIS",
        "console_free_runtime": True,
        "bundled_backend": "resources/jarvis-runtime/runtime/jarvis-backend.exe",
        "bundled_voice": "resources/jarvis-runtime/runtime/piper/piper.exe",
        "bundled_model": "resources/jarvis-runtime/data/models/Ministral-3-3B-Reasoning-2512-Q4_K_M.gguf",
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-bundle", type=Path, default=DEFAULT_APP_BUNDLE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seven-zip", type=str, default=None)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()
    result = build(args.app_bundle, args.output, _find_7z(args.seven_zip))
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
