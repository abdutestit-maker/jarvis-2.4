from __future__ import annotations

import json

from core.security.atomic import atomic_json_write, load_json, BoundedJSONStore


def test_atomic_json_write_roundtrip_and_no_temp_left(tmp_path) -> None:
    path = tmp_path / "state.json"
    atomic_json_write(path, {"ok": True, "items": [1, 2]})
    assert load_json(path) == {"ok": True, "items": [1, 2]}
    assert not list(tmp_path.glob("*.tmp"))


def test_bounded_store_keeps_recent_and_important_records(tmp_path) -> None:
    store = BoundedJSONStore(tmp_path / "memory.json", max_records=2)
    store.append({"id": "old", "importance": 0.1})
    store.append({"id": "important", "importance": 1.0})
    store.append({"id": "new", "importance": 0.2})
    ids = {item["id"] for item in store.load()}
    assert ids == {"important", "new"}
    json.loads((tmp_path / "memory.json").read_text(encoding="utf-8"))

