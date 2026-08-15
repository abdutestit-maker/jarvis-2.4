"""Долговременная память на ChromaDB (персистентный клиент).

Хранит факты и диалоги в векторной БД для семантического поиска.
Коллекция ``conversations`` — основное хранилище долгой памяти.

Гарантии надёжности: любой сбой ChromaDB (нет диска, битая коллекция)
ловится и логируется, методы поиска/добавления не роняют процесс —
возвращают пустой результат. Это критично: память не должна ломать
основной цикл ассистента.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from config.settings import Settings
from core.memory.embedder import Embedder
from core.utils.logger import get_logger

__all__ = ["LongTermMemory", "CONVERSATIONS_COLLECTION", "disable_chroma_telemetry_noise"]

log = get_logger(__name__)

#: Имя коллекции для диалогов/фактов долгой памяти.
CONVERSATIONS_COLLECTION = "conversations"


def disable_chroma_telemetry_noise() -> None:
    """Глушит сломанную телеметрию ChromaDB без потери функциональности.

    В chromadb 0.5.x внутренний вызов ``posthog.capture(user_id, name, props)``
    (3 позиционных аргумента) несовместим с сигнатурой установленного пакета
    ``posthog`` (``capture(self, event)``). Из-за этого при каждой операции
    с коллекцией сыплются WARNING вида
    ``Failed to send telemetry event ... capture() takes 1 positional
    argument but 3 were given``.

    Это НЕ влияет на память/RAG (телеметрия — побочный сетевой шум), но
    засоряет логи. Функция один раз подменяет ``posthog.capture`` совместимым
    no-op-адаптером. Безопасно: не трогает логику Chroma, вызывается только
    при инициализации наших клиентов памяти.
    """
    try:
        import posthog  # type: ignore
    except Exception:
        return
    original = getattr(posthog, "capture", None)
    if original is None or getattr(original, "_jarvis_patched", False):
        return

    def _patched_capture(*args, **kwargs):
        # Совместим с обеими сигнатурами: (user_id, event_name, props) и
        # (event). Ничего не отправляем — телеметрия нам не нужна.
        try:
            if len(args) >= 1 and hasattr(args[0], "name"):
                pass  # новая сигнатура: capture(self, event)
            # старая сигнатура: capture(user_id, event_name, properties)
        except Exception:
            pass

    _patched_capture._jarvis_patched = True  # type: ignore[attr-defined]
    posthog.capture = _patched_capture


class LongTermMemory:
    """Персистентная векторная память на ChromaDB."""

    def __init__(self, settings: Settings, embedder: Embedder) -> None:
        """
        Args:
            settings: конфигурация (берётся ``settings.paths.memory_dir``).
            embedder: общий эмбеддер проекта (тот же, что у document_rag).
        """
        self._settings = settings
        self._embedder = embedder
        self._client = None
        self._collection = None
        self._initialized = False
        self._init_client()

    # ------------------------------------------------------------------ #
    #  Инициализация
    # ------------------------------------------------------------------ #

    def _init_client(self) -> None:
        """Создаёт PersistentClient и коллекцию (лень, при первом вызове метода)."""
        try:
            import chromadb
        except ImportError as exc:
            log.error("chromadb не установлен: долгая память недоступна: %s", exc)
            return

        # Подавляем сломанную телеметрию ChromaDB. В chromadb 0.5.x внутренний
        # вызов posthog.capture(user_id, event_name, props) несовместим с
        # сигнатурой установленного posthog-пакета (capture(self, event)),
        # из-за чего сыплются WARNING "capture() takes 1 positional argument
        # but 3 were given". Это НЕ влияет на память/RAG — только шум в логах.
        # Ставим совместимый no-op, не трогая логику Chroma.
        disable_chroma_telemetry_noise()

        try:
            persist_dir = self._settings.paths.resolved("memory_dir")
            persist_dir.mkdir(parents=True, exist_ok=True)
            # anonymized_telemetry=False — отключаем сетевую телеметрию
            # ChromaDB (шум в логах capture() takes 1 positional argument...),
            # функциональность памяти/RAG не меняется.
            self._client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=chromadb.Settings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=CONVERSATIONS_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
            self._initialized = True
            log.info("Долгая память инициализирована: %s", persist_dir)
        except Exception as exc:  # chromadb поднимает разные исключения
            log.error("Не удалось инициализировать ChromaDB: %s", exc)
            self._initialized = False

    def _ensure(self) -> bool:
        """Возвращает True, если клиент готов к работе."""
        if self._initialized and self._collection is not None:
            return True
        if self._client is None:
            self._init_client()
        return self._initialized and self._collection is not None

    # ------------------------------------------------------------------ #
    #  Запись
    # ------------------------------------------------------------------ #

    def add(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Добавляет текст в долгую память. Возвращает id записи.

        Перед записью текст очищается от секретов/сырых данных (П1 §1.5, §1.8):
        J.A.R.V.I.S. хранит СМЫСЛ диалога, а не ключи/пароли/сырые ошибки.
        Если после очистки текст пуст — запись пропускается (мусор не пишем).

        Args:
            text: текст для запоминания (не пустой).
            metadata: произвольные метаданные (строки/числа).

        Returns:
            Идентификатор добавленной записи. Пустая строка при ошибке/пустоте.
        """
        from core.memory.secret_filter import sanitize_for_memory

        safe_text = sanitize_for_memory(text or "")
        if not safe_text or not safe_text.strip():
            log.debug("add(): текст пуст после очистки секретов, пропуск")
            return ""
        if not self._ensure():
            return ""

        import uuid
        record_id = uuid.uuid4().hex
        safe_metadata: Dict[str, Any] = {}
        if metadata:
            # ChromaDB требует плоские метаданные из примитивов.
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    safe_metadata[str(key)] = value
        try:
            self._collection.add(
                documents=[safe_text],
                ids=[record_id],
                metadatas=[safe_metadata] if safe_metadata else None,
            )
            log.debug("Добавлена запись долгой памяти: %s...", safe_text[:60])
            return record_id
        except Exception as exc:
            log.error("Ошибка добавления в долгую память: %s", exc)
            return ""

    # ------------------------------------------------------------------ #
    #  Поиск
    # ------------------------------------------------------------------ #

    def search(self, query: str, top_k: int = 3) -> List[str]:
        """Семантический поиск по долгой памяти.

        Args:
            query: поисковый запрос.
            top_k: сколько результатов вернуть.

        Returns:
            Список найденных текстов (пустой при отсутствии результатов/ошибке).
        """
        if not query or not query.strip():
            return []
        if not self._ensure():
            return []

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=max(1, top_k),
            )
        except Exception as exc:
            log.error("Ошибка поиска в долгой памяти: %s", exc)
            return []

        # chromadb возвращает вложенные списки: documents[0] — список текстов.
        documents = (results or {}).get("documents") or [[]]
        return [str(doc) for doc in documents[0] if doc]

    def count(self) -> int:
        """Число записей в коллекции (0 при ошибке)."""
        if not self._ensure():
            return 0
        try:
            return int(self._collection.count())
        except Exception as exc:
            log.error("Ошибка подсчёта записей долгой памяти: %s", exc)
            return 0

    # ------------------------------------------------------------------ #
    #  Forget / TTL (П1 §1.8) — устаревшие записи НЕ храним вечно
    # ------------------------------------------------------------------ #

    # Срок жизни записи в памяти (3 дня). Старше — выметаются при sweep.
    FORGET_TTL_DAYS: float = 3.0

    def sweep_expired(self, ttl_days: Optional[float] = None) -> int:
        """Удаляет записи старше TTL (П1 §1.8). Возвращает число удалённых.

        Записи без метки ``stored_at`` считаются «вечными» (не трогаем —
        это старые данные до введения TTL). Сама операция не роняет рантайм:
        любая ошибка ChromaDB логируется и возвращает 0 удалённых.

        Args:
            ttl_days: переопределить TTL (по умолчанию :attr:`FORGET_TTL_DAYS`).

        Returns:
            Число удалённых записей (0 при ошибке/отсутствии ChromaDB).
        """
        if not self._ensure():
            return 0
        ttl = float(ttl_days if ttl_days is not None else self.FORGET_TTL_DAYS)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=ttl)).isoformat()
        try:
            # ChromaDB where-фильтр: stored_at < cutoff (ISO-строки
            # лексикографически упорядочены как время при UTC-Z).
            old = self._collection.get(
                where={"stored_at": {"$lt": cutoff}},
                include=["metadatas"],
            )
            ids = old.get("ids") or []
            if not ids:
                return 0
            self._collection.delete(ids=ids)
            log.info("Forget-TTL: выметено %d устаревших записей (старше %s дней)",
                     len(ids), ttl)
            return len(ids)
        except Exception as exc:
            log.warning("Forget-TTL sweep не удался: %s", exc)
            return 0

    def delete_by_text(self, text_substring: str) -> int:
        """Явное забывание: удаляет записи, содержащие подстроку (П1 §1.8).

        Используется, когда пользователь просит «забудь X». Возвращает
        число удалённых (0 при ошибке/отсутствии совпадений).
        """
        if not text_substring or not text_substring.strip():
            return 0
        if not self._ensure():
            return 0
        try:
            all_docs = self._collection.get(include=["documents"])
            ids = all_docs.get("ids") or []
            docs = all_docs.get("documents") or []
            to_delete = [
                ids[i] for i, d in enumerate(docs)
                if d and text_substring.lower() in str(d).lower()
            ]
            if not to_delete:
                return 0
            self._collection.delete(ids=to_delete)
            log.info("Forget: удалено %d записей по подстроке '%s'",
                     len(to_delete), text_substring[:40])
            return len(to_delete)
        except Exception as exc:
            log.warning("Forget по подстроке не удался: %s", exc)
            return 0
