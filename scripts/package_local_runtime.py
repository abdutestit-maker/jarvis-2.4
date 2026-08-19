#!/usr/bin/env python
"""Stage a portable local model/runtime for the Tauri installer.

The staged directory is intentionally ignored by Git: it contains the local
GGUF and Vulkan DLLs.  The resulting installer can therefore ship a model
without embedding a user's API keys or depending on a cloud provider.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _candidate_backend_pythons(explicit: str | None = None) -> list[Path]:
    """Return Python runtimes in the same order as the desktop launcher."""
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    env_value = os.environ.get("JARVIS_PYTHON", "").strip()
    if env_value:
        candidates.append(Path(env_value).expanduser())
    candidates.extend([
        ROOT / "runtime" / "python.exe",
        ROOT / ".venv" / "Scripts" / "python.exe",
        Path.home() / "AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe",
        Path.home() / "venv/Scripts/python.exe",
        Path(sys.executable),
    ])
    result: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        key = str(resolved).casefold()
        if key not in seen and resolved.is_file():
            seen.add(key)
            result.append(resolved)
    return result


def _select_backend_python(explicit: str | None = None) -> Path:
    """Find a Python that has the frozen-backend build dependency installed."""
    for candidate in _candidate_backend_pythons(explicit):
        probe = subprocess.run(
            [str(candidate), "-c", "import pydantic, websockets, PyInstaller"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if probe.returncode == 0:
            return candidate
    raise RuntimeError(
        "Не найден Python с pydantic, websockets и PyInstaller. "
        "Укажите --backend-python на окружение сборки."
    )


def _build_backend_executable(*, output: Path, python: Path, dry_run: bool = False) -> Path:
    """Build a windowless, self-contained WS backend for the installer."""
    if dry_run:
        return output / "runtime" / "jarvis-backend.exe"
    build_root = ROOT / "runs" / "packaging" / "backend"
    if build_root.exists():
        shutil.rmtree(build_root)
    dist_root = build_root / "dist"
    work_root = build_root / "work"
    spec_root = build_root / "spec"
    for path in (dist_root, work_root, spec_root):
        path.mkdir(parents=True, exist_ok=True)
    command = [
        str(python), "-m", "PyInstaller", "--noconfirm", "--clean",
        "--onefile", "--noconsole", "--name", "jarvis-backend",
        "--distpath", str(dist_root), "--workpath", str(work_root),
        "--specpath", str(spec_root), "--paths", str(ROOT),
        "--collect-submodules", "core", "--collect-submodules", "config",
        str(ROOT / "scripts" / "packaged_backend.py"),
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    built = dist_root / "jarvis-backend.exe"
    if not built.is_file() or built.stat().st_size < 1024 * 1024:
        raise RuntimeError(f"PyInstaller не создал backend: {built}")
    target = output / "runtime" / "jarvis-backend.exe"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built, target)
    return target


def stage(*, output: Path, include_fallback: bool = False,
          backend_python: str | None = None, backend_executable: str | None = None,
          dry_run: bool = False) -> dict:
    from config import load_config
    from core.llm.llama_server import find_llama_server

    settings = load_config()
    model = settings.local_model.resolved_gguf_path
    if model is None or not model.is_file():
        raise FileNotFoundError(f"локальный GGUF не найден: {model}")
    server = find_llama_server(settings.local_model.server_binary_path)
    if server is None:
        raise FileNotFoundError("llama-server не найден: установите официальный llama.cpp")

    fallback = ROOT / "data" / "models" / "Qwen3-1.7B-Q6_K.gguf"
    files = [model]
    if include_fallback and fallback.is_file() and fallback.resolve() != model.resolve():
        files.append(fallback)
    dlls = sorted(server.parent.glob("*.dll"))
    configured_voice = getattr(settings.voice, "resolved_primary_piper_model", None)
    if configured_voice is None:
        configured_voice = getattr(settings.voice, "resolved_piper_model", None)
    voice_model = Path(configured_voice) if configured_voice is not None else (
        ROOT / "data" / "models" / "piper" / "ru_RU-denis-medium.onnx"
    )
    voice_config = voice_model.with_name(voice_model.name + ".json")
    voice_runtime = ROOT / "data" / "runtime" / "piper"
    if not voice_model.is_file() or not voice_config.is_file():
        raise FileNotFoundError(
            f"Русский Piper voice не найден: {voice_model}(.json)"
        )
    if not (voice_runtime / "piper.exe").is_file():
        raise FileNotFoundError("Проверенный Piper runtime не найден: data/runtime/piper/piper.exe")

    if not dry_run and output.exists():
        shutil.rmtree(output)

    if backend_executable:
        backend = Path(backend_executable).expanduser().resolve()
        if not dry_run and not backend.is_file():
            raise FileNotFoundError(f"backend executable not found: {backend}")
    else:
        backend = _build_backend_executable(
            output=output, python=_select_backend_python(backend_python), dry_run=dry_run,
        )
    manifest = {
        "format": 2,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "offline": True,
        "cloud_api": False,
        # The manifest is shipped to another machine.  Keep it reproducible
        # without leaking the builder's drive, user profile, or workspace.
        "server": {"source": "bundled llama.cpp", "filename": "runtime/llama-server.exe"},
        "backend": {"source": "bundled PyInstaller backend", "filename": "runtime/jarvis-backend.exe", "windowless": True},
        "voice": {"provider": "piper", "language": "ru", "model": f"data/models/piper/{voice_model.name}", "runtime": "runtime/piper/piper.exe"},
        "model_family": str(getattr(settings, "model_family", "ministral") or "ministral"),
        "models": [],
        "files": [],
    }
    for item in files:
        manifest["models"].append({
            "filename": f"data/models/{item.name}",
            "size_bytes": item.stat().st_size,
            "sha256": _sha256(item),
            "source": "official Ministral GGUF",
        })
    for item in [server, *dlls]:
        manifest["files"].append({"filename": f"runtime/{item.name}", "size_bytes": item.stat().st_size, "sha256": _sha256(item)})
    manifest["files"].append({
        "filename": "runtime/jarvis-backend.exe",
        "size_bytes": backend.stat().st_size if backend.is_file() else 0,
        "sha256": _sha256(backend) if backend.is_file() else "",
    })
    for item in (voice_model, voice_config):
        manifest["files"].append({
            "filename": f"data/models/piper/{item.name}",
            "size_bytes": item.stat().st_size,
            "sha256": _sha256(item),
        })
    for item in voice_runtime.rglob("*"):
        if item.is_file():
            manifest["files"].append({
                "filename": f"runtime/piper/{item.relative_to(voice_runtime).as_posix()}",
                "size_bytes": item.stat().st_size,
                "sha256": _sha256(item),
            })
    total_bytes = sum(int(item["size_bytes"]) for item in manifest["models"] + manifest["files"])
    manifest["total_bytes"] = total_bytes
    if dry_run:
        return manifest

    (output / "data" / "models" / "piper").mkdir(parents=True, exist_ok=True)
    (output / "runtime").mkdir(parents=True, exist_ok=True)
    for item in files:
        shutil.copy2(item, output / "data" / "models" / item.name)
    for item in [server, *dlls]:
        shutil.copy2(item, output / "runtime" / item.name)
    backend_target = output / "runtime" / "jarvis-backend.exe"
    if backend.resolve() != backend_target.resolve():
        shutil.copy2(backend, backend_target)
    shutil.copy2(voice_model, output / "data" / "models" / "piper" / voice_model.name)
    shutil.copy2(voice_config, output / "data" / "models" / "piper" / voice_config.name)
    shutil.copytree(voice_runtime, output / "runtime" / "piper", dirs_exist_ok=True)

    # Include the small Python application tree beside the model.  The GGUF
    # is large; the orchestration source is not, and a packaged resource must
    # not point back to this developer's E: drive.
    for source_name in ("core", "config", "persona"):
        source = ROOT / source_name
        if source.is_dir():
            shutil.copytree(source, output / source_name, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "settings.json"))
    notices = ROOT / "THIRD_PARTY_NOTICES.txt"
    if notices.is_file():
        shutil.copy2(notices, output / notices.name)

    config = json.loads((ROOT / "config" / "settings.example.json").read_text(encoding="utf-8"))
    config["offline_mode"] = True
    config["auto_download_models"] = False
    config["model_family"] = "ministral"
    config["model_tiers"] = {key: "Ministral-3-3B-Reasoning-2512" for key in ("fast", "analyst", "coder", "architect", "research")}
    config["tier_providers"] = {key: "local" for key in ("fast", "analyst", "coder", "architect", "research")}
    config["local_model"].update({
        "gguf_path": f"data/models/{model.name}",
        "runtime_backend": "llama-server",
        "server_binary_path": "runtime/llama-server.exe",
        "server_start_timeout_sec": 90.0,
        "n_gpu_layers": -1,
    })
    config["local_coder_model"]["gguf_path"] = f"data/models/{model.name}"
    config.setdefault("launcher", {}).update({
        "backend_command": ["runtime/jarvis-backend.exe"],
        "backend_workdir": "",
        "autostart": True,
        # Startup stays silent.  The first spoken response belongs to the
        # user's first command; an unsolicited greeting used to look like a
        # phantom analysis run in the UI and made the voice path feel broken.
        "greeting_enabled": False,
    })
    config.setdefault("logging", {}).update({
        "console": False,
    })
    config.setdefault("voice", {}).update({
        "tts_enabled": True,
        "tts_always_on": True,
        "provider": "piper",
        "language": "ru",
        "voice": voice_model.stem,
        "fallback": "none",
        # Keep the legacy field for additive compatibility; PiperTTS uses the
        # explicit primary path for the shipped voice.
        "piper_model_path": "data/models/piper/ru_RU-dmitri-medium.onnx",
        "primary_piper_model_path": f"data/models/piper/{voice_model.name}",
        "piper_binary_path": "runtime/piper/piper.exe",
    })
    (output / "config").mkdir(parents=True, exist_ok=True)
    (output / "config" / "settings.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "runtime-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "jarvis" / "src-tauri" / "resources" / "jarvis-runtime")
    parser.add_argument("--include-fallback", action="store_true", help="добавить имеющийся 1.7B fallback для слабых машин")
    parser.add_argument("--backend-python", default=None, help="Python с зависимостями PyInstaller/pydantic/websockets")
    parser.add_argument("--backend-exe", default=None, help="готовый windowless jarvis-backend.exe; пропускает PyInstaller")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    manifest = stage(
        output=args.output,
        include_fallback=args.include_fallback,
        backend_python=args.backend_python,
        backend_executable=args.backend_exe,
        dry_run=args.dry_run,
    )
    print(json.dumps({
        "output": str(args.output),
        "dry_run": args.dry_run,
        "total_bytes": manifest["total_bytes"],
        "models": manifest["models"],
        "server": manifest["server"],
        "backend": manifest["backend"],
        "voice": manifest["voice"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
