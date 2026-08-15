"""Тест слоёв памяти, НЕ требующих эмбеддингов (profile JSON + SQLite graph).

Полезно для быстрой проверки логики без скачивания MiniLM-модели ChromaDB.
Запуск:: python scripts/test_memory_novec.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config import load_config  # noqa: E402
from core.memory import (  # noqa: E402
    GraphMemoryStore,
    get_profile_context,
    load_profile,
    save_profile,
    update_profile,
)
from core.utils.logger import setup_logging  # noqa: E402

setup_logging(level="WARNING", console=True)


def main() -> None:
    settings = load_config()
    settings.ensure_directories()

    print("=== ПРОФИЛЬ (JSON) ===")
    # Делаем тест детерминированным: сбрасываем профиль в дефолтное пустое
    # состояние перед проверкой (предыдущие прогоны могли его заполнить).
    save_profile(settings, {
        "name": "",
        "conditions": [],
        "interests": [],
        "dislikes": [],
        "preferences": {"response_length": "default"},
        "notes": "",
    })
    profile = load_profile(settings)
    print("Дефолт:", profile)
    assert isinstance(profile, dict)
    ctx0 = get_profile_context(settings)
    print("Контекст (пустой):", repr(ctx0))
    assert ctx0 == ""

    update_profile(settings, "conditions", ["СДВГ"])
    update_profile(settings, "interests", ["GTA 5", "Менталист"])
    update_profile(settings, "dislikes", ["ждать"])
    update_profile(settings, "preferences", {"response_length": "short"})

    ctx = get_profile_context(settings)
    print("Контекст:", repr(ctx))
    assert "СДВГ" in ctx and "GTA 5" in ctx and "короткие ответы" in ctx

    print("\n=== ГРАФ ЗНАНИЙ (SQLite) ===")
    graph = GraphMemoryStore(settings)
    n1 = graph.create_node("Пользователь", {"name": "Сэр"})
    n2 = graph.create_node("Игра", {"title": "GTA 5"})
    n3 = graph.create_node("Сериал", {"title": "Менталист"})
    print("Узлы:", n1, n2, n3)
    assert all(x > 0 for x in (n1, n2, n3))
    graph.create_edge(n1, n2, "любит")
    graph.create_edge(n1, n3, "смотрит")

    children = graph.get_children(n1)
    print("Дети пользователя:", [(c["label"], c["properties"]) for c in children])
    assert len(children) == 2

    found = graph.search_nodes("GTA", top_k=5)
    print("Поиск 'GTA':", [n["label"] for n in found])
    assert any(n["label"] == "Игра" for n in found)

    print("\n=== ТЕСТ БЕЗ ВЕКТОРОВ ЗАВЕРШЁН ===")


if __name__ == "__main__":
    main()
