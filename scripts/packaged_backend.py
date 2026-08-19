"""Frozen backend entrypoint used by the Windows installer.

The Tauri process sets ``JARVIS_HOME`` to the extracted resource directory
before launching this executable.  Keeping the anchor outside the frozen
PyInstaller temp directory makes config, model, Piper and user data paths
portable across machines.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _install_root() -> Path:
    configured = os.environ.get("JARVIS_HOME", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_dir():
            return candidate.resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent.parent
    return Path(__file__).resolve().parents[1]


_ROOT = _install_root()
os.environ.setdefault("JARVIS_HOME", str(_ROOT))
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.ws_server import run_server  # noqa: E402


if __name__ == "__main__":
    run_server()
