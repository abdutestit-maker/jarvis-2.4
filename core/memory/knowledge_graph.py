"""Простой граф знаний на SQLite (связи, НЕ векторы).

Хранит узлы и рёбра (отношения между узлами). Поиск — простой LIKE
по меткам и свойствам (без эмбеддингов — это MVP). Используется
 оркестратором и модулями памяти для связывания фактов.

Таблицы создаются автоматически (CREATE TABLE IF NOT EXISTS).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import Settings
from core.utils.logger import get_logger

__all__ = ["GraphMemoryStore"]

log = get_logger(__name__)


class GraphMemoryStore:
    """Граф знаний на SQLite."""

    def __init__(self, settings: Settings) -> None:
        """
        Args:
            settings: конфигурация (берётся ``settings.paths.graph_dir``).

        Raises:
            RuntimeError: если не удалось создать/открыть БД.
        """
        graph_dir = settings.paths.resolved("graph_dir")
        graph_dir.mkdir(parents=True, exist_ok=True)
        db_path = graph_dir / "jarvis_graph.db"

        try:
            self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._init_schema()
            log.info("Граф знаний инициализирован: %s", db_path)
        except sqlite3.Error as exc:
            raise RuntimeError(f"Не удалось открыть граф-БД {db_path}: {exc}") from exc

    # ------------------------------------------------------------------ #
    #  Схема
    # ------------------------------------------------------------------ #

    def _init_schema(self) -> None:
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                properties TEXT NOT NULL DEFAULT '{}',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_id INTEGER NOT NULL,
                to_id INTEGER NOT NULL,
                relation TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_id) REFERENCES nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (to_id) REFERENCES nodes(id) ON DELETE CASCADE
            )"""
        )
        self._conn.commit()

    # ------------------------------------------------------------------ #
    #  Узлы
    # ------------------------------------------------------------------ #

    def create_node(self, label: str, properties: Optional[Dict[str, Any]] = None) -> int:
        """Создаёт узел. Возвращает его id (или -1 при ошибке)."""
        if not label or not label.strip():
            raise ValueError("create_node(): пустая метка")
        properties = properties or {}
        # П1 §1.5/§1.8: не пишем секреты/сырые данные в граф знаний.
        from core.memory.secret_filter import sanitize_for_memory, contains_secret_or_raw
        safe_label = sanitize_for_memory(label)
        if not safe_label or not safe_label.strip():
            log.debug("create_node(): метка пуста после очистки секретов, пропуск")
            return -1
        # Очищаем значения свойств от секретов (ключи оставляем как есть).
        safe_props: Dict[str, Any] = {}
        for key, value in properties.items():
            if isinstance(value, str):
                safe_props[key] = sanitize_for_memory(value)
            else:
                safe_props[key] = value
        try:
            cursor = self._conn.execute(
                "INSERT INTO nodes (label, properties) VALUES (?, ?)",
                (safe_label, json.dumps(safe_props, ensure_ascii=False)),
            )
            self._conn.commit()
            node_id = int(cursor.lastrowid)
            log.debug("Создан узел #%d '%s'", node_id, safe_label)
            return node_id
        except sqlite3.Error as exc:
            log.error("Ошибка создания узла '%s': %s", safe_label, exc)
            return -1

    # ------------------------------------------------------------------ #
    #  Рёбра
    # ------------------------------------------------------------------ #

    def create_edge(self, from_id: int, to_id: int, relation: str) -> None:
        """Создаёт направленное ребро from_id -> to_id с отношением ``relation``."""
        if from_id <= 0 or to_id <= 0:
            raise ValueError("create_edge(): некорректные id узлов")
        if not relation or not relation.strip():
            raise ValueError("create_edge(): пустое отношение")
        try:
            self._conn.execute(
                "INSERT INTO edges (from_id, to_id, relation) VALUES (?, ?, ?)",
                (from_id, to_id, relation),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            log.error("Ошибка создания ребра %d->%d (%s): %s", from_id, to_id, relation, exc)

    # ------------------------------------------------------------------ #
    #  Чтение
    # ------------------------------------------------------------------ #

    def get_node(self, node_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает узел по id или ``None``."""
        try:
            row = self._conn.execute(
                "SELECT id, label, properties FROM nodes WHERE id = ?", (node_id,)
            ).fetchone()
        except sqlite3.Error as exc:
            log.error("Ошибка чтения узла #%d: %s", node_id, exc)
            return None
        if row is None:
            return None
        return self._row_to_node(row)

    def get_children(self, node_id: int) -> List[Dict[str, Any]]:
        """Возвращает дочерние узлы (куда ведут рёбра из ``node_id``)."""
        try:
            rows = self._conn.execute(
                """SELECT n.id, n.label, n.properties
                   FROM edges e JOIN nodes n ON n.id = e.to_id
                   WHERE e.from_id = ?""",
                (node_id,),
            ).fetchall()
        except sqlite3.Error as exc:
            log.error("Ошибка чтения дочерних узлов #%d: %s", node_id, exc)
            return []
        return [self._row_to_node(r) for r in rows]

    def search_nodes(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Простой LIKE-поиск по метке и свойствам.

        Args:
            query: поисковая строка.
            top_k: сколько узлов вернуть.

        Returns:
            Список словарей узлов (id, label, properties).
        """
        if not query or not query.strip():
            return []
        pattern = f"%{query}%"
        try:
            rows = self._conn.execute(
                """SELECT id, label, properties FROM nodes
                   WHERE label LIKE ? OR properties LIKE ?
                   ORDER BY id DESC LIMIT ?""",
                (pattern, pattern, max(1, top_k)),
            ).fetchall()
        except sqlite3.Error as exc:
            log.error("Ошибка поиска узлов по '%s': %s", query, exc)
            return []
        return [self._row_to_node(r) for r in rows]

    # ------------------------------------------------------------------ #
    #  Утилиты
    # ------------------------------------------------------------------ #

    @staticmethod
    def _row_to_node(row: sqlite3.Row) -> Dict[str, Any]:
        """Преобразует строку БД в словарь узла с распарсенными свойствами."""
        raw_props = row["properties"] or "{}"
        try:
            props = json.loads(raw_props)
        except json.JSONDecodeError:
            props = {}
        return {"id": row["id"], "label": row["label"], "properties": props}

    def close(self) -> None:
        """Закрывает соединение с БД."""
        try:
            self._conn.close()
        except sqlite3.Error as exc:
            log.debug("Ошибка закрытия граф-БД: %s", exc)

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
