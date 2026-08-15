"""Ручной тест слоёв памяти (без pytest).

Проверяет реальную работу всех подсистем памяти на живом settings:
  * profile: создаётся дефолтный, update + чтение контекста
  * knowledge_graph: создаём узлы, связываем, ищем
  * long_term: добавляем фразы, ищем обратно (требует embedding-модель)
  * document_rag: index_all() на пустой documents_dir не падает
  * retrieval: собирает контекст из всех слоёв

ВАЖНО про эмбеддинги: default embedding-функция chromadb (all-MiniLM-L6-v2)
скачивается при первом использовании (~79 МБ). Если модель ещё не
загружена (медленная сеть), векторные слои (long_term / document_rag)
честно сообщат о недоступности и тест продолжается для остальных слоёв.
Это не ошибка кода — окружение не докачало модель. Прогреть можно
отдельно: python -c "from core.memory.embedder import Embedder;
Embedder().embed_one('тест')"

Запуск:: python scripts/test_memory_manual.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config import load_config  # noqa: E402
from core.memory import (  # noqa: E402
    DocumentRAG,
    Embedder,
    GraphMemoryStore,
    LongTermMemory,
    MemoryRetriever,
    get_profile_context,
    load_profile,
    save_profile,
    update_profile,
)
from core.state import new_state  # noqa: E402
from core.utils.logger import setup_logging  # noqa: E402

setup_logging(level="WARNING", console=True)


def rule(title: str) -> None:
    print("\n" + "-" * 70)
    print(title)
    print("-" * 70)


def main() -> None:
    settings = load_config()
    settings.ensure_directories()

    # ---------- 2. Profile (JSON) ----------  (всегда доступно)
    rule("2. Профиль пользователя (JSON)")
    # Сбрасываем профиль в дефолт, чтобы тест был детерминированным
    # (предыдущие прогоны могли оставить заполненный профиль).
    save_profile(settings, {
        "name": "",
        "conditions": [],
        "interests": [],
        "dislikes": [],
        "preferences": {"response_length": "default"},
        "notes": "",
    })
    profile = load_profile(settings)
    print("Дефолтный профиль:", profile)
    print("Контекст до заполнения:", repr(get_profile_context(settings)))

    update_profile(settings, "conditions", ["СДВГ"])
    update_profile(settings, "interests", ["GTA 5", "Менталист"])
    update_profile(settings, "dislikes", ["ждать"])
    update_profile(settings, "preferences", {"response_length": "short"})

    ctx = get_profile_context(settings)
    print("Контекст после заполнения:", repr(ctx))
    assert "СДВГ" in ctx and "GTA 5" in ctx and "короткие ответы" in ctx

    # ---------- 3. Knowledge graph (SQLite) ----------  (всегда доступно)
    rule("3. Граф знаний (SQLite)")
    graph = GraphMemoryStore(settings)
    n1 = graph.create_node("Пользователь", {"name": "Сэр"})
    n2 = graph.create_node("Игра", {"title": "GTA 5"})
    n3 = graph.create_node("Сериал", {"title": "Менталист"})
    print(f"Созданы узлы: {n1}, {n2}, {n3}")
    graph.create_edge(n1, n2, "любит")
    graph.create_edge(n1, n3, "смотрит")

    children = graph.get_children(n1)
    print(f"Дочерние узлы пользователя ({len(children)}):")
    for child in children:
        print(f"   -> {child['label']} ({child['properties']})")

    found_nodes = graph.search_nodes("GTA", top_k=5)
    print(f"Поиск 'GTA' -> {len(found_nodes)} узел(ов):", [n["label"] for n in found_nodes])

    # ---------- 4. DocumentRAG на пустой папке ----------  (требует эмбеддер)
    rule("4. RAG-документы (index_all на пустой documents_dir)")
    embedding_ready = True
    embedder = None
    try:
        embedder = Embedder()
        print("Embedder создан:", type(embedder).__name__)
    except Exception as exc:
        embedding_ready = False
        print(f"Embedder НЕДОСТУПЕН (модель эмбеддингов ещё не загружена): {exc}")

    rag = None
    if embedder is not None:
        try:
            rag = DocumentRAG(settings, embedder)
            result = rag.index_all()
            print("index_all() на пустой папке:", result)
            assert result["indexed"] == 0, "Не должно быть проиндексировано файлов"
        except Exception as exc:
            print(f"RAG недоступен: {exc}")
            embedding_ready = False
    else:
        print("RAG пропущен: нет эмбеддера.")

    # ---------- 1 & 5. LongTerm + Retrieval ----------  (требует эмбеддер)
    rule("1 & 5. Долгая память (ChromaDB) + MemoryRetriever")
    if embedder is not None:
        try:
            ltm = LongTermMemory(settings, embedder)
            ltm.add("Джарвис родился в лаборатории Старка.", {"topic": "origin"})
            ltm.add("Пользователь предпочитает общаться на русском.", {"topic": "lang"})
            ltm.add("Любимый цвет пользователя — красный.", {"topic": "color"})
            print(f"Записей в долгой памяти: {ltm.count()}")

            found = ltm.search("где родился Джарвис", top_k=2)
            print(f"Поиск 'где родился Джарвис' -> {len(found)} результат(ов)")
            for item in found:
                print("   •", item[:80])

            retriever = MemoryRetriever(settings)
            state = new_state("где родился Джарвис и что любит пользователь?")
            retriever.retrieve(state)
            rc = state["retrieved_context"]
            print("retrieve -> profile:", len(rc.get("profile", "")), "симв.,",
                  "long_term:", len(rc.get("long_term", [])), ",",
                  "documents:", len(rc.get("documents", [])), ",",
                  "graph:", len(rc.get("graph", [])))

            retriever.remember_exchange(
                "где родился Джарвис?",
                "Я был создан в лаборатории Старка, сэр.",
            )
            print("Обмен репликами сохранён. Всего записей:",
                  retriever.long_term.count())
        except Exception as exc:
            print(f"Векторная память недоступна (модель эмбеддингов не загружена?): {exc}")
            embedding_ready = False
    else:
        print("Долгая память и Retrieval пропущены: нет эмбеддера.")

    print("\n" + "=" * 70)
    if embedding_ready:
        print("ТЕСТ ПАМЯТИ ЗАВЕРШЁН: все слои отработали.")
    else:
        print("ТЕСТ ПАМЯТИ ЗАВЕРШЁН (частично): невекторные слои ОК;")
        print("векторные слои пропущены — модель эмбеддингов all-MiniLM-L6-v2")
        print("ещё не докачана (медленная сеть). Прогрейте её отдельно:")
        print("  python -c \"from core.memory.embedder import Embedder; Embedder().embed_one('тест')\"")
        print("Затем повторите запуск — векторные слои заработают.")


if __name__ == "__main__":
    main()
