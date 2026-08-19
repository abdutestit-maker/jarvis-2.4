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
import shutil
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


def stage(*, output: Path, include_fallback: bool = False, dry_run: bool = False) -> dict:
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
    manifest = {
        "format": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "offline": True,
        "cloud_api": False,
        "server": {"source": str(server), "filename": "runtime/llama-server.exe"},
        "models": [],
        "files": [],
    }
    for item in files:
        manifest["models"].append({
            "filename": f"data/models/{item.name}",
            "size_bytes": item.stat().st_size,
            "sha256": _sha256(item),
            "source": str(item),
        })
    for item in [server, *dlls]:
        manifest["files"].append({"filename": f"runtime/{item.name}", "size_bytes": item.stat().st_size, "sha256": _sha256(item)})
    total_bytes = sum(int(item["size_bytes"]) for item in manifest["models"] + manifest["files"])
    manifest["total_bytes"] = total_bytes
    if dry_run:
        return manifest

    if output.exists():
        shutil.rmtree(output)
    (output / "data" / "models").mkdir(parents=True, exist_ok=True)
    (output / "runtime").mkdir(parents=True, exist_ok=True)
    for item in files:
        shutil.copy2(item, output / "data" / "models" / item.name)
    for item in [server, *dlls]:
        shutil.copy2(item, output / "runtime" / item.name)

    # Include the small Python application tree beside the model.  The GGUF
    # is large; the orchestration source is not, and a packaged resource must
    # not point back to this developer's E: drive.
    for source_name in ("core", "config", "persona"):
        source = ROOT / source_name
        if source.is_dir():
            shutil.copytree(source, output / source_name, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "settings.json"))

    config = json.loads((ROOT / "config" / "settings.example.json").read_text(encoding="utf-8"))
    config["offline_mode"] = True
    config["auto_download_models"] = False
    config["model_tiers"] = {key: "Qwen3-4B-Instruct-2507-Q5_K_M" for key in ("fast", "analyst", "coder", "architect", "research")}
    config["tier_providers"] = {key: "local" for key in ("fast", "analyst", "coder", "architect", "research")}
    config["local_model"].update({
        "gguf_path": f"data/models/{model.name}",
        "runtime_backend": "llama-server",
        "server_binary_path": "runtime/llama-server.exe",
        "n_gpu_layers": 0,
    })
    config["local_coder_model"]["gguf_path"] = f"data/models/{model.name}"
    config.setdefault("launcher", {})["backend_workdir"] = ""
    (output / "config").mkdir(parents=True, exist_ok=True)
    (output / "config" / "settings.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "runtime-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "jarvis" / "src-tauri" / "resources" / "jarvis-runtime")
    parser.add_argument("--include-fallback", action="store_true", help="добавить имеющийся 1.7B fallback для слабых машин")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    manifest = stage(output=args.output, include_fallback=args.include_fallback, dry_run=args.dry_run)
    print(json.dumps({"output": str(args.output), "dry_run": args.dry_run, "total_bytes": manifest["total_bytes"], "models": manifest["models"], "server": manifest["server"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
