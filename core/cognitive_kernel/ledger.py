"""Local SQLite WAL ledger for resumable missions and evidence."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from .models import MissionRecord, utcnow


class MissionLedger:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        if self.path.suffix.casefold() != ".db":
            self.path = self.path / "missions.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=NORMAL")
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS missions (
                mission_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL UNIQUE,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS mission_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                mission_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_mission_events_mission
                ON mission_events(mission_id, event_id);
            """
        )
        self._db.commit()

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def create(self, mission: MissionRecord, *, event_type: str = "mission.created") -> MissionRecord:
        payload = json.dumps(mission.to_dict(), ensure_ascii=False, sort_keys=True)
        with self._lock:
            self._db.execute(
                "INSERT OR IGNORE INTO missions(mission_id, task_id, payload, updated_at) VALUES (?, ?, ?, ?)",
                (mission.id, mission.task_id, payload, mission.updated_at),
            )
            self._db.execute(
                "INSERT INTO mission_events(mission_id, event_type, payload, created_at) VALUES (?, ?, ?, ?)",
                (mission.id, event_type, payload, utcnow()),
            )
            self._db.commit()
        return mission

    def save(self, mission: MissionRecord, *, event_type: str = "mission.updated") -> MissionRecord:
        mission.updated_at = utcnow()
        payload = json.dumps(mission.to_dict(), ensure_ascii=False, sort_keys=True)
        with self._lock:
            self._db.execute(
                "INSERT INTO missions(mission_id, task_id, payload, updated_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(mission_id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at",
                (mission.id, mission.task_id, payload, mission.updated_at),
            )
            self._db.execute(
                "INSERT INTO mission_events(mission_id, event_type, payload, created_at) VALUES (?, ?, ?, ?)",
                (mission.id, event_type, payload, mission.updated_at),
            )
            self._db.commit()
        return mission

    def load(self, mission_id: str) -> MissionRecord | None:
        with self._lock:
            row = self._db.execute("SELECT payload FROM missions WHERE mission_id = ?", (mission_id,)).fetchone()
        if row is None:
            return None
        return MissionRecord(**json.loads(row["payload"]))

    def load_by_task(self, task_id: str) -> MissionRecord | None:
        with self._lock:
            row = self._db.execute("SELECT payload FROM missions WHERE task_id = ?", (task_id,)).fetchone()
        return MissionRecord(**json.loads(row["payload"])) if row else None

    def load_by_idempotency(self, key: str) -> MissionRecord | None:
        """Find a mission submitted with the same caller idempotency key.

        ``contract`` is JSON rather than a second mutable mission table, so
        this bounded lookup deliberately scans the small mission ledger.  It
        keeps the schema additive for existing databases and prevents a
        reconnect from minting duplicate TaskContract UUIDs.
        """
        wanted = str(key or "").strip()
        if not wanted:
            return None
        with self._lock:
            rows = self._db.execute("SELECT payload FROM missions ORDER BY updated_at DESC").fetchall()
        for row in rows:
            payload = json.loads(row["payload"])
            contract = payload.get("contract") if isinstance(payload, dict) else None
            if isinstance(contract, dict) and str(contract.get("idempotency_key", "")) == wanted:
                return MissionRecord(**payload)
        return None

    def events(self, mission_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT event_id, event_type, payload, created_at FROM mission_events WHERE mission_id = ? ORDER BY event_id",
                (mission_id,),
            ).fetchall()
        return [
            {"event_id": int(row["event_id"]), "event_type": row["event_type"],
             "payload": json.loads(row["payload"]), "created_at": row["created_at"]}
            for row in rows
        ]


__all__ = ["MissionLedger"]
