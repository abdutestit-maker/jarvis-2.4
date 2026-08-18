"""Safe GGUF discovery and controlled one-at-a-time model lifecycle."""
from __future__ import annotations

import re
import struct
import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class GGUFModelInfo:
    path: Path
    exists: bool
    size_bytes: int
    architecture: str
    version: int | None
    tensor_count: int | None
    metadata_count: int | None
    compatible: bool
    loaded: bool = False


class LocalModelManager:
    def __init__(self, paths: tuple[str | Path, ...] | list[str | Path]) -> None:
        self.paths = tuple(Path(path) for path in paths)

    def discover(self) -> tuple[GGUFModelInfo, ...]:
        found: dict[Path, GGUFModelInfo] = {}
        for root in self.paths:
            candidates = (root,) if root.is_file() else tuple(root.glob("*.gguf")) if root.is_dir() else ()
            for path in candidates:
                resolved = path.resolve()
                found[resolved] = self.inspect(resolved)
        return tuple(found[path] for path in sorted(found, key=lambda item: str(item).casefold()))

    @staticmethod
    def inspect(path: str | Path) -> GGUFModelInfo:
        target = Path(path)
        size = target.stat().st_size if target.is_file() else 0
        version = tensors = metadata = None
        compatible = False
        parsed_architecture = ""
        if target.is_file():
            try:
                with target.open("rb") as stream:
                    header = stream.read(24)
                if len(header) >= 24 and header[:4] == b"GGUF":
                    version, tensors, metadata = struct.unpack("<IQQ", header[4:24])
                    compatible = version in {2, 3}
                    parsed_architecture = LocalModelManager._read_architecture(target, metadata)
            except OSError:
                pass
        name = target.name.casefold()
        architecture = parsed_architecture or "unknown"
        for needle, label in (
            ("qwen", "qwen"), ("llama", "llama"), ("mistral", "mistral"),
            ("gemma", "gemma"), ("phi", "phi"), ("deepseek", "deepseek"),
        ):
            if architecture == "unknown" and re.search(needle, name):
                architecture = label
                break
        return GGUFModelInfo(
            target, target.is_file(), size, architecture, version,
            tensors, metadata, compatible, False,
        )

    @staticmethod
    def _read_architecture(path: Path, metadata_count: int | None) -> str:
        """Read only the bounded `general.architecture` GGUF key."""
        if not metadata_count or metadata_count > 4096:
            return ""
        try:
            with path.open("rb") as stream:
                stream.seek(24)

                def read(fmt: str):
                    size = struct.calcsize(fmt)
                    data = stream.read(size)
                    if len(data) != size:
                        raise ValueError("truncated GGUF metadata")
                    return struct.unpack(fmt, data)[0]

                def string() -> str:
                    length = int(read("<Q"))
                    if length > 1_048_576:
                        raise ValueError("oversized GGUF string")
                    return stream.read(length).decode("utf-8", errors="replace")

                def value(kind: int):
                    formats = {
                        0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i",
                        6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d",
                    }
                    if kind == 8:
                        return string()
                    if kind == 9:
                        element_kind = int(read("<I"))
                        count = min(int(read("<Q")), 1024)
                        return [value(element_kind) for _ in range(count)]
                    if kind not in formats:
                        raise ValueError("unknown GGUF metadata type")
                    return read(formats[kind])

                for _ in range(int(metadata_count)):
                    key = string()
                    kind = int(read("<I"))
                    item = value(kind)
                    if key == "general.architecture" and isinstance(item, str):
                        return item
        except (OSError, UnicodeError, ValueError, struct.error):
            return ""
        return ""

    @staticmethod
    def estimated_ram_bytes(info: GGUFModelInfo) -> int:
        return int(info.size_bytes * 1.25) + 64 * 1024 * 1024

    @classmethod
    def can_load(cls, info: GGUFModelInfo, *, available_ram_bytes: int,
                 background: bool, background_fraction: float = 0.25) -> bool:
        available = max(0, int(available_ram_bytes))
        budget = (int(available * max(0.0, min(1.0, background_fraction)))
                  if background else available)
        return info.compatible and cls.estimated_ram_bytes(info) <= budget


class LocalModelLifecycle:
    def __init__(self, *, loader: Callable[[Path], Any],
                 warmer: Callable[[Any], None] | None = None,
                 unloader: Callable[[Any], None] | None = None,
                 max_loaded: int = 1) -> None:
        self.loader = loader
        self.warmer = warmer or (lambda _handle: None)
        self.unloader = unloader or (lambda handle: getattr(handle, "close", lambda: None)())
        self.max_loaded = max(1, int(max_loaded))
        self._handles: OrderedDict[Path, Any] = OrderedDict()
        self._lock = threading.RLock()

    def load(self, path: str | Path) -> Any:
        target = Path(path)
        with self._lock:
            if target in self._handles:
                self._handles.move_to_end(target)
                return self._handles[target]
            while len(self._handles) >= self.max_loaded:
                _old_path, old_handle = self._handles.popitem(last=False)
                self.unloader(old_handle)
            handle = self.loader(target)
            self._handles[target] = handle
            return handle

    def warm(self, path: str | Path) -> None:
        self.warmer(self.load(path))

    def idle(self, path: str | Path) -> bool:
        target = Path(path)
        with self._lock:
            if target not in self._handles:
                return False
            self._handles.move_to_end(target, last=False)
            return True

    def unload(self, path: str | Path) -> bool:
        target = Path(path)
        with self._lock:
            handle = self._handles.pop(target, None)
        if handle is None:
            return False
        self.unloader(handle)
        return True

    def unload_all(self) -> None:
        for path in self.loaded_paths():
            self.unload(path)

    def loaded_paths(self) -> tuple[Path, ...]:
        with self._lock:
            return tuple(self._handles)


__all__ = ["GGUFModelInfo", "LocalModelManager", "LocalModelLifecycle"]
