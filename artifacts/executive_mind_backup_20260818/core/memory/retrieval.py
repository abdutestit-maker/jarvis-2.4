"""Сборщик памяти для оркестратора (Часть 5).

``MemoryRetriever`` создаёт и кэширует все слои памяти единожды, затем
заполняет ``state["retrieved_context"]`` из каждого слоя. Главное правило:
сбой одного слоя НЕ должен ронять остальные — каждый вызов обёрнут в
try/except, и в контекст попадает то, что удалось собрать.

Не трогает ``persona``/``time_context`` — это забота других модулей.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config.settings import Settings
from core.memory.document_rag import DocumentRAG
from core.memory.embedder import Embedder
from core.memory.knowledge_graph import GraphMemoryStore
from core.memory.long_term import LongTermMemory
from core.memory.profile import get_profile_context
from core.state import JarvisState, RetrievedContext
from core.utils.logger import get_logger

__all__ = ["MemoryRetriever"]

log = get_logger(__name__)


class MemoryRetriever:
    """Единая точка доступа ко всем слоям памяти."""

    def __init__(self, settings: Settings) -> None:
        """
        Args:
            settings: конфигурация проекта.
        """
        self._settings = settings
        self._rag_top_k = getattr(settings.limits, "rag_top_k", 3) or 3
        self._memory_top_k = getattr(settings.limits, "memory_top_k", 5) or 5

        # Создаём слои лениво в первом же вызове retrieve(), чтобы не падать
        # в конструкторе, если какая-то подсистема временно недоступна.
        self._embedder: Optional[Embedder] = None
        self._long_term: Optional[LongTermMemory] = None
        self._document_rag: Optional[DocumentRAG] = None
        self._graph: Optional[GraphMemoryStore] = None
        self._initialized = False

    # ------------------------------------------------------------------ #
    #  Ленивая инициализация слоёв
    # ------------------------------------------------------------------ #

    def _build_layers(self) -> None:
        if self._initialized:
            return
        try:
            self._embedder = Embedder()
        except Exception as exc:
            log.error("Не удалось создать эмбеддер: %s", exc)
            self._embedder = None

        if self._embedder is not None:
            try:
                self._long_term = LongTermMemory(self._settings, self._embedder)
            except Exception as exc:
                log.error("Не удалось создать долгую память: %s", exc)
                self._long_term = None
            try:
                self._document_rag = DocumentRAG(self._settings, self._embedder)
            except Exception as exc:
                log.error("Не удалось создать RAG-документы: %s", exc)
                self._document_rag = None
        else:
            log.warning("Эмбеддер недоступен — векторные слои памяти отключены")

        try:
            self._graph = GraphMemoryStore(self._settings)
        except Exception as exc:
            log.error("Не удалось создать граф знаний: %s", exc)
            self._graph = None

        self._initialized = True

    # ------------------------------------------------------------------ #
    #  Сборка контекста
    # ------------------------------------------------------------------ #

    def retrieve(self, state: JarvisState) -> JarvisState:
        """Заполняет ``state["retrieved_context"]`` из всех доступных слоёв.

        Каждый слой обёрнут в try/except: если он упал — логируем и
        пропускаем, остальные слои продолжают работать.

        Args:
            state: состояние витка (мутируется: дописывается ``retrieved_context``).

        Returns:
            Тот же объект ``state``.
        """
        self._build_layers()
        query = (state.get("user_input") or "").strip()

        context: RetrievedContext = {
            "profile": "",
            "long_term": [],
            "documents": [],
            "graph": [],
        }

        # 1) Профиль — всегда доступен (простой JSON).
        try:
            context["profile"] = get_profile_context(self._settings)
        except Exception as exc:
            log.warning("Ошибка сборки контекста профиля: %s", exc)

        # 2) Долгая память.
        if self._long_term is not None and query:
            try:
                context["long_term"] = self._long_term.search(query, self._rag_top_k)
            except Exception as exc:
                log.warning("Ошибка поиска в долгой памяти: %s", exc)

        # 3) RAG по документам.
        if self._document_rag is not None and query:
            try:
                context["documents"] = self._document_rag.search_documents(query, self._rag_top_k)
            except Exception as exc:
                log.warning("Ошибка поиска по документам: %s", exc)

        # 4) Граф знаний (LIKE-поиск, без эмбеддингов).
        if self._graph is not None and query:
            try:
                nodes = self._graph.search_nodes(query, self._memory_top_k)
                # RetrievedContext.graph — List[str]; сериализуем узлы в читаемый вид.
                context["graph"] = [
                    f"[{node['label']}] {json_dumps(node['properties'])}"
                    for node in nodes
                ]
            except Exception as exc:
                log.warning("Ошибка поиска в графе знаний: %s", exc)

        state["retrieved_context"] = context
        log.debug(
            "Контекст собран: profile=%d симв., long_term=%d, documents=%d, graph=%d",
            len(context["profile"]), len(context["long_term"]),
            len(context["documents"]), len(context["graph"]),
        )
        return state

    # ------------------------------------------------------------------ #
    #  Запись обмена репликами
    # ------------------------------------------------------------------ #

    def remember_exchange(self, user_text: str, assistant_text: str) -> None:
        """Сохраняет пару «пользователь — ассистент» в долгую память.

        Перед записью текст очищается от секретов/сырых данных (П1 §1.5, §1.8):
        J.A.R.V.I.S. хранит СМЫСЛ диалога, а не ключи/пароли/сырые ошибки.
        Пустые после очистки реплики не сохраняются.

        Args:
            user_text: реплика пользователя.
            assistant_text: ответ ассистента.
        """
        from core.memory.secret_filter import sanitize_for_memory

        self._build_layers()
        if self._long_term is None:
            return
        user_safe = sanitize_for_memory(user_text or "")
        if user_safe and user_safe.strip():
            self._long_term.add(
                f"Пользователь: {user_safe.strip()}",
                metadata={"type": "user", "source": "conversation",
                          "stored_at": _now_iso()},
            )
        assistant_safe = sanitize_for_memory(assistant_text or "")
        if assistant_safe and assistant_safe.strip():
            self._long_term.add(
                f"АТЛАС: {assistant_safe.strip()}",
                metadata={"type": "assistant", "source": "conversation",
                          "stored_at": _now_iso()},
            )

    # ------------------------------------------------------------------ #
    #  Доступ к слоям (для прямого использования в тестах/других модулях)
    # ------------------------------------------------------------------ #

    @property
    def embedder(self) -> Optional[Embedder]:
        self._build_layers()
        return self._embedder

    @property
    def long_term(self) -> Optional[LongTermMemory]:
        self._build_layers()
        return self._long_term

    @property
    def document_rag(self) -> Optional[DocumentRAG]:
        self._build_layers()
        return self._document_rag

    @property
    def knowledge_graph(self) -> Optional[GraphMemoryStore]:
        self._build_layers()
        return self._graph


def json_dumps(value: Any) -> str:
    """Безопасная сериализация свойств узла графа в строку."""
    import json
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def _now_iso() -> str:
    """Текущее UTC-время в ISO-формате (для меток stored_at в памяти)."""
    return datetime.now(timezone.utc).isoformat()
