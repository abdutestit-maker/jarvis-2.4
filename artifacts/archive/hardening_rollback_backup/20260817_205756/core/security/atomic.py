"""Crash-safe, bounded local JSON persistence."""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any


def _flush_directory(directory: Path) -> None:
    if os.name == "nt":
        return
    try:
        fd = os.open(str(directory), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def atomic_write_bytes(path: str | Path, data: bytes) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_tmp = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    tmp = Path(raw_tmp)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, target)
        _flush_directory(target.parent)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
    return target


def atomic_write_text(path: str | Path, text: str) -> Path:
    return atomic_write_bytes(path, text.encode("utf-8"))


def atomic_json_write(path: str | Path, value: Any) -> Path:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return atomic_write_text(path, payload)


def load_json(path: str | Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return default


class BoundedJSONStore:
    """Small append-only store with importance, recency and record bounds."""

    def __init__(self, path: str | Path, *, max_records: int = 1000, ttl_seconds: float | None = None) -> None:
        self.path = Path(path)
        self.max_records = max(1, int(max_records))
        self.ttl_seconds = ttl_seconds
        self._lock = threading.RLock()

    def load(self) -> list[dict[str, Any]]:
        with self._lock:
            raw = load_json(self.path, default=[])
            records = raw.get("records", []) if isinstance(raw, dict) else raw
            if not isinstance(records, list):
                return []
            return [dict(item) for item in records if isinstance(item, dict)]

    def append(self, record: dict[str, Any]) -> None:
        now = time.time()
        item = dict(record)
        item.setdefault("created_at_epoch", now)
        item["last_used_epoch"] = now
        with self._lock:
            records = self.load()
            record_id = item.get("id")
            if record_id:
                records = [old for old in records if old.get("id") != record_id]
            records.append(item)
            if self.ttl_seconds is not None:
                cutoff = now - max(0, float(self.ttl_seconds))
                records = [old for old in records if float(old.get("created_at_epoch", now)) >= cutoff or float(old.get("importance", 0.0)) >= 0.9]
            records.sort(key=lambda old: (float(old.get("importance", 0.0)), float(old.get("last_used_epoch", 0.0))), reverse=True)
            records = records[: self.max_records]
            atomic_json_write(self.path, {"records": records})

    def compact(self) -> list[dict[str, Any]]:
        records = self.load()
        atomic_json_write(self.path, {"records": records[: self.max_records]})
        return records[: self.max_records]

