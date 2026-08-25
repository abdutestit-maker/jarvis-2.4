"""Build a self-contained Windows installer for the production JARVIS runtime.

The conversational brain is remote DeepSeek through DeepInfra.  The bundle
contains the native GUI/backend and local Piper/Whisper assets, but no GGUF or
llama-server executable.
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
    required = [
        app_bundle / "jarvis-frontend.exe",
        app_bundle / "resources" / "jarvis-runtime" / "runtime" / "jarvis-backend.exe",
        app_bundle / "resources" / "jarvis-runtime" / "runtime" / "piper" / "piper.exe",
        app_bundle / "resources" / "jarvis-runtime" / "data" / "models" / "piper",
        app_bundle / "resources" / "jarvis-runtime" / "data" / "models" / "stt",
        app_bundle / "resources" / "jarvis-runtime" / "data" / "brain" / "provider-secrets.dpapi",
    ]
    missing = [str(path) for path in required if not path.exists()]
    model_dir = app_bundle / "resources" / "jarvis-runtime" / "data" / "models"
    voice_dir = model_dir / "piper"
    if not list(voice_dir.glob("*.onnx")):
        missing.append(f"{voice_dir}/*.onnx")
    if missing:
        raise FileNotFoundError("Installer payload is incomplete: " + ", ".join(missing))
    stale_local_assets = list(model_dir.glob("*.gguf")) + list(
        (app_bundle / "resources" / "jarvis-runtime" / "runtime").glob("llama-server*")
    )
    if stale_local_assets:
        raise ValueError(
            "DeepSeek production payload contains local LLM assets: "
            + ", ".join(str(item) for item in stale_local_assets)
        )
    config_path = app_bundle / "resources" / "jarvis-runtime" / "config" / "settings.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not config.get("deepseek_brain_mode") or config.get("offline_mode"):
        raise ValueError("Installer config is not DeepSeek production mode")
    credential = config.get("credential_store", {})
    if credential.get("backend") != "dpapi" or credential.get("required_in_production") is not True:
        raise ValueError("Installer config does not require the packaged DPAPI credential")
    credential_path = app_bundle / "resources" / "jarvis-runtime" / credential.get(
        "path", "data/brain/provider-secrets.dpapi"
    )
    if not credential_path.is_file() or credential_path.stat().st_size < 64:
        raise ValueError("Installer payload has no verified packaged DeepInfra credential")


def _sync_runtime_resource(app_bundle: Path) -> None:
    """Keep the release payload aligned with the staged local runtime.

    ``tauri build --no-bundle`` builds the frontend executable but does not
    refresh bundled resources.  Always copy the staged production runtime so
    an old local-model payload cannot survive in ``target/release``.
    """
    source = ROOT / "jarvis" / "src-tauri" / "resources" / "jarvis-runtime"
    target = app_bundle / "resources" / "jarvis-runtime"
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)


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
    $programs = [Environment]::GetFolderPath("Programs")
    $shell = New-Object -ComObject WScript.Shell
    if ($desktop) {
        $shortcut = $shell.CreateShortcut((Join-Path $desktop "J.A.R.V.I.S..lnk"))
        $shortcut.TargetPath = $exe
        $shortcut.WorkingDirectory = $app
        $shortcut.IconLocation = "$exe,0"
        $shortcut.Save()
    }
    if ($programs) {
        $menu = Join-Path $programs "J.A.R.V.I.S."
        New-Item -ItemType Directory -Path $menu -Force | Out-Null
        $shortcut = $shell.CreateShortcut((Join-Path $menu "J.A.R.V.I.S..lnk"))
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
    _sync_runtime_resource(app_bundle)
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
        # Copy mode keeps the runtime deterministic and avoids wasting time on
        # already-compressed voice/model assets.
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
        "brain": "deepinfra/deepseek-ai/DeepSeek-V4-Flash-0731",
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
