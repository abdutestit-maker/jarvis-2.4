"""Единый эмбеддер проекта на базе ChromaDB default embedding function.

Зачем отдельный класс: long_term, document_rag и knowledge_graph должны
использовать ОДИН и тот же эмбеддер, иначе векторы в разных коллекциях
будут несовместимы (нельзя сравнивать эмбеддинги от разных моделей).

По умолчанию берём ``chromadb.DefaultEmbeddingFunction`` (all-MiniLM-L6-v2,
скачивается самим chromadb при первом вызове). Это надёжнее, чем
полагаться на ``LLMBackend.embed()``, который может бросить
``NotImplementedError`` на локальной модели.

Опционально: если в venv установлен ``fastembed`` и задан
``settings.local_model.embedding_gguf_path``-аналог — можно расширить,
но по умолчанию используем стандартный путь.
"""

from __future__ import annotations

from typing import List
from pathlib import Path

from core.utils.logger import get_logger
from core.utils.paths import PROJECT_ROOT

__all__ = ["Embedder"]

log = get_logger(__name__)


class Embedder:
    """Обёртка над embedding-функцией ChromaDB (all-MiniLM-L6-v2)."""

    def __init__(self) -> None:
        """Лениво подтягивает дефолтную embedding-функцию chromadb.

        Raises:
            RuntimeError: если chromadb недоступен в окружении.
        """
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError(
                "Библиотека chromadb не установлена — невозможно создать эмбеддер"
            ) from exc

        # В chromadb 0.5.x дефолтная embedding-функция (all-MiniLM-L6-v2) живёт в
        # chromadb.utils.embedding_functions. Подстраховываемся цепочкой импортов,
        # чтобы не зависеть от минорной версии.
        embedding_fn = None
        try:
            # Import the concrete implementation, not only Chroma's lazy
            # factory.  The factory references ONNXMiniLM_L6_V2 by a module
            # global, which PyInstaller can omit from a frozen backend.
            from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import (
                ONNXMiniLM_L6_V2,
            )
            bundled_model = PROJECT_ROOT / "data" / "models" / "embeddings" / "all-MiniLM-L6-v2"
            if (bundled_model / "onnx" / "model.onnx").is_file():
                ONNXMiniLM_L6_V2.DOWNLOAD_PATH = Path(bundled_model)
            embedding_fn = ONNXMiniLM_L6_V2()
        except (ImportError, AttributeError):
            try:
                from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
                embedding_fn = DefaultEmbeddingFunction()
            except (ImportError, AttributeError):
                if hasattr(chromadb, "DefaultEmbeddingFunction"):
                    embedding_fn = chromadb.DefaultEmbeddingFunction()
        if embedding_fn is None:
            raise RuntimeError("Не удалось найти дефолтную embedding-функцию chromadb")
        self._fn = embedding_fn
        log.debug("Embedder инициализирован (chromadb default embedding function)")

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Векторизует список текстов.

        Args:
            texts: непустой список строк.

        Returns:
            Список векторов (по одному на текст).

        Raises:
            ValueError: если передан пустой список.
        """
        if not texts:
            raise ValueError("embed(): пустой список текстов")
        clean = [str(text) for text in texts]
        try:
            vectors = self._fn(clean)
        except Exception as exc:  # chromadb может бросить разные ошибки сети/модели
            log.error("Ошибка эмбеддинга батча из %d текстов: %s", len(clean), exc)
            raise
        return [list(map(float, vector)) for vector in vectors]

    def embed_one(self, text: str) -> List[float]:
        """Векторизует один текст.

        Args:
            text: строка для векторизации.

        Returns:
            Вектор-список чисел.
        """
        if not text:
            raise ValueError("embed_one(): пустой текст")
        return self.embed([text])[0]
