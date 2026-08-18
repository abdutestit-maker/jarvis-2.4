"""Локальный бэкенд: Qwen 4B GGUF через llama-cpp-python.

Это «лицо» Джарвиса: единственная модель, которая всегда под рукой,
работает без сети и решает — ответить самой или позвать модель посильнее.

Особенности реализации:
    * ``llama_cpp`` импортируется **лениво** — проект должен импортироваться
      и на машине без собранного llama-cpp-python (например, в CI);
    * загрузка весов выполняется в ``warm_up()`` (явно, при старте main.py),
      а не при первом запросе — так задержка предсказуема;
    * генерация сериализована через ``threading.RLock``: один экземпляр
      ``Llama`` не потокобезопасен, а к нему обращаются и роутер, и
      проактивный фоновый цикл.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from core.llm.backend import (
    BackendConfigError,
    BackendUnavailable,
    LLMBackend,
    normalize_messages,
    prepend_system,
    strip_reasoning_blocks,
)
from core.utils.logger import get_logger

__all__ = ["LocalQwenBackend"]

log = get_logger(__name__)

#: Стоп-последовательности ChatML — страхуют от «болтовни за себя».
_DEFAULT_STOP = ["<|im_end|>", "<|endoftext|>"]


class LocalQwenBackend(LLMBackend):
    """Обёртка над ``llama_cpp.Llama`` для локальной Qwen 4B.

    Args:
        gguf_path: путь к файлу модели ``*.gguf``.
        model_id: логическое имя модели для логов (из ``settings.model_tiers.fast``).
        n_gpu_layers: сколько слоёв выгрузить на GPU (0 = CPU, -1 = все).
        n_ctx: размер контекстного окна.
        n_threads: число потоков CPU (``None`` = решает llama.cpp).
        n_batch: размер батча промпта.
        temperature: температура по умолчанию.
        max_tokens: лимит генерации по умолчанию.
        chat_format: имя chat-шаблона llama-cpp (``None`` = взять из метаданных GGUF).
        verbose: пробрасывать ли подробный вывод llama.cpp.
        embedding: включить ли режим эмбеддингов у основной модели.
    """

    supports_tools = False

    def __init__(
        self,
        gguf_path: Path | str,
        model_id: str = "qwen-4b-local",
        n_gpu_layers: int = 0,
        n_ctx: int = 4096,
        n_threads: Optional[int] = None,
        n_batch: int = 512,
        temperature: float = 0.6,
        max_tokens: int = 512,
        chat_format: Optional[str] = None,
        verbose: bool = False,
        embedding: bool = False,
    ) -> None:
        self._gguf_path = Path(gguf_path)
        self.model = model_id
        self.name = f"local:{model_id}"
        self._n_gpu_layers = int(n_gpu_layers)
        self._n_ctx = int(n_ctx)
        self._n_threads = n_threads
        self._n_batch = int(n_batch)
        self._temperature = float(temperature)
        self._max_tokens = int(max_tokens)
        self._chat_format = chat_format
        self._verbose = bool(verbose)
        self._embedding_mode = bool(embedding)
        self.supports_embeddings = bool(embedding)

        self._llama: Optional[Any] = None
        self._lock = threading.RLock()
        self._load_failed_reason: Optional[str] = None
        self._warmup_ms: float | None = None
        self._warmup_complete = False
        self._gpu_offload_supported: bool | None = None

    # ------------------------------------------------------------------ #
    #  Загрузка модели
    # ------------------------------------------------------------------ #

    @property
    def gguf_path(self) -> Path:
        """Путь к файлу модели."""
        return self._gguf_path

    @property
    def is_loaded(self) -> bool:
        """Загружены ли веса в память."""
        return self._llama is not None

    def _model_file_error(self) -> str:
        """Понятное сообщение о проблеме с файлом модели."""
        path = self._gguf_path
        if not path.exists():
            return (
                f"Файл модели не найден: {path}\n"
                f"Что сделать: скачайте GGUF-модель Qwen 4B (например, "
                f"qwen3-4b-instruct-q4_k_m.gguf) в каталог {path.parent} "
                f"и укажите точный путь в settings.json -> local_model.gguf_path"
            )
        if path.is_dir():
            return (
                f"Указанный путь — каталог, а не файл модели: {path}\n"
                f"Укажите в settings.json -> local_model.gguf_path конкретный *.gguf файл"
            )
        if path.stat().st_size < 1024 * 1024:
            return (
                f"Файл модели подозрительно мал ({path.stat().st_size} байт): {path}\n"
                f"Вероятно, загрузка не завершилась — скачайте модель заново"
            )
        return ""

    def _import_llama_cpp(self) -> Any:
        """Ленивый импорт llama_cpp с понятной диагностикой."""
        try:
            from llama_cpp import Llama  # noqa: WPS433 (ленивый импорт — намеренно)
        except ImportError as exc:
            raise BackendUnavailable(
                "Библиотека llama-cpp-python не установлена.\n"
                "Установка (CPU):  pip install llama-cpp-python==0.3.16\n"
                "Установка (CUDA): pip install llama-cpp-python==0.3.16 "
                "--extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124\n"
                f"Причина: {exc}"
            ) from exc
        return Llama

    def _load(self) -> Any:
        """Загружает веса модели (идемпотентно, под локом).

        Raises:
            BackendUnavailable: файла нет или llama.cpp не смог загрузить модель.
        """
        with self._lock:
            if self._llama is not None:
                return self._llama

            file_problem = self._model_file_error()
            if file_problem:
                self._load_failed_reason = file_problem
                raise BackendUnavailable(file_problem)

            llama_cls = self._import_llama_cpp()

            kwargs: Dict[str, Any] = {
                "model_path": str(self._gguf_path),
                "n_ctx": self._n_ctx,
                "n_gpu_layers": self._n_gpu_layers,
                "n_batch": self._n_batch,
                "verbose": self._verbose,
                "embedding": self._embedding_mode,
            }
            if self._n_threads:
                kwargs["n_threads"] = self._n_threads
            if self._chat_format:
                kwargs["chat_format"] = self._chat_format

            started = time.perf_counter()
            log.info(
                "Загружаю локальную модель %s (n_ctx=%d, n_gpu_layers=%d)",
                self._gguf_path.name, self._n_ctx, self._n_gpu_layers,
            )
            try:
                self._llama = llama_cls(**kwargs)
            except (ValueError, RuntimeError, OSError, MemoryError) as exc:
                reason = (
                    f"llama.cpp не смог загрузить модель {self._gguf_path}: {exc}\n"
                    f"Проверьте: (1) файл не повреждён, (2) хватает ОЗУ/VRAM, "
                    f"(3) n_gpu_layers={self._n_gpu_layers} соответствует сборке "
                    f"llama-cpp-python (CPU-сборка требует 0)"
                )
                self._load_failed_reason = reason
                log.error(reason)
                raise BackendUnavailable(reason) from exc

            elapsed = time.perf_counter() - started
            self._load_failed_reason = None
            log.info("Модель %s загружена за %.2f с", self._gguf_path.name, elapsed)
            return self._llama

    def warm_up(self) -> None:
        """Загружает веса и делает пробную генерацию одного токена.

        Вызывается явно при старте ``main.py``.

        Raises:
            BackendUnavailable: модель не загрузилась.
        """
        llama = self._load()
        started = time.perf_counter()
        try:
            with self._lock:
                llama.create_chat_completion(
                    messages=[{"role": "user", "content": "ok"}],
                    max_tokens=1,
                    temperature=0.0,
                )
        except (ValueError, RuntimeError, OSError) as exc:
            raise BackendUnavailable(
                f"Прогрев локальной модели не удался: {exc}"
            ) from exc
        self._warmup_ms = (time.perf_counter() - started) * 1000.0
        self._warmup_complete = True
        log.info("Прогрев локальной модели завершён за %.2f с", self._warmup_ms / 1000.0)

    # ------------------------------------------------------------------ #
    #  Генерация
    # ------------------------------------------------------------------ #

    def _completion_kwargs(self, max_tokens: Optional[int],
                           temperature: Optional[float]) -> Dict[str, Any]:
        """Общие параметры генерации."""
        return {
            "max_tokens": int(max_tokens) if max_tokens else self._max_tokens,
            "temperature": self._temperature if temperature is None else float(temperature),
            "stop": list(_DEFAULT_STOP),
        }

    @staticmethod
    def _extract_text(response: Dict[str, Any]) -> str:
        """Достаёт текст из ответа create_chat_completion."""
        choices = response.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        content = message.get("content")
        if content is None:
            content = choices[0].get("text", "")
        return strip_reasoning_blocks(str(content))

    def chat(self, messages: List[Dict[str, Any]], system: Optional[str] = None,
             max_tokens: Optional[int] = None,
             temperature: Optional[float] = None) -> str:
        """Диалог через chat-шаблон модели (create_chat_completion)."""
        payload = prepend_system(normalize_messages(messages), system)
        if not payload:
            raise ValueError("chat(): пустой список сообщений")

        llama = self._load()
        started = time.perf_counter()
        try:
            with self._lock:
                response = llama.create_chat_completion(
                    messages=payload,
                    **self._completion_kwargs(max_tokens, temperature),
                )
        except (ValueError, RuntimeError, OSError) as exc:
            log.error("Ошибка генерации локальной модели: %s", exc)
            raise BackendUnavailable(f"Локальная модель не смогла ответить: {exc}") from exc

        elapsed = time.perf_counter() - started
        text = self._extract_text(response if isinstance(response, dict) else {})
        log.debug("local chat: %.2f с, %d символов", elapsed, len(text))
        return text

    def direct(self, prompt: str, system: Optional[str] = None,
               max_tokens: Optional[int] = None,
               temperature: Optional[float] = None) -> str:
        """Одиночный запрос без истории."""
        if not (prompt or "").strip():
            raise ValueError("direct(): пустой prompt")
        return self.chat([{"role": "user", "content": prompt}], system=system,
                         max_tokens=max_tokens, temperature=temperature)

    def streaming(self, messages: List[Dict[str, Any]], system: Optional[str] = None,
                  max_tokens: Optional[int] = None,
                  temperature: Optional[float] = None) -> Generator[str, None, None]:
        """Потоковая генерация: отдаёт дельты текста по мере готовности."""
        payload = prepend_system(normalize_messages(messages), system)
        if not payload:
            raise ValueError("streaming(): пустой список сообщений")

        llama = self._load()
        try:
            with self._lock:
                stream = llama.create_chat_completion(
                    messages=payload,
                    stream=True,
                    **self._completion_kwargs(max_tokens, temperature),
                )
                for chunk in stream:
                    if not isinstance(chunk, dict):
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    piece = delta.get("content")
                    if piece:
                        yield str(piece)
        except (ValueError, RuntimeError, OSError) as exc:
            log.error("Ошибка потоковой генерации локальной модели: %s", exc)
            raise BackendUnavailable(f"Локальная модель прервала поток: {exc}") from exc

    # ------------------------------------------------------------------ #
    #  Эмбеддинги
    # ------------------------------------------------------------------ #

    def embed(self, text: str) -> List[float]:
        """Эмбеддинг текста (только если модель загружена с ``embedding=True``).

        Для памяти проект использует эмбеддер ChromaDB (Часть 3); этот метод —
        опция для случая, когда пользователь указал отдельную GGUF-модель
        эмбеддингов.
        """
        if not self._embedding_mode:
            raise NotImplementedError(
                f"Бэкенд {self.name} загружен без режима embedding. "
                "Укажите local_model.embedding_gguf_path в settings.json "
                "или используйте эмбеддер ChromaDB."
            )
        if not (text or "").strip():
            raise ValueError("embed(): пустой текст")

        llama = self._load()
        try:
            with self._lock:
                result = llama.create_embedding(input=text)
        except (ValueError, RuntimeError, OSError) as exc:
            raise BackendUnavailable(f"Не удалось построить эмбеддинг: {exc}") from exc

        data = (result or {}).get("data") or []
        if not data:
            raise BackendUnavailable("Пустой ответ эмбеддера локальной модели")
        vector = data[0].get("embedding") or []
        # llama.cpp может вернуть вложенный список (по токенам) — усредняем
        if vector and isinstance(vector[0], list):
            columns = len(vector[0])
            return [sum(row[i] for row in vector) / len(vector) for i in range(columns)]
        return [float(value) for value in vector]

    # ------------------------------------------------------------------ #
    #  Сервис
    # ------------------------------------------------------------------ #

    def list_models(self) -> List[str]:
        """Локально доступна ровно одна модель — файл из конфига."""
        return [self.model] if self._gguf_path.is_file() else []

    def is_available(self) -> bool:
        """Быстрая проверка: файл на месте и (если загружали) загрузка не падала."""
        if self._llama is not None:
            return True
        if self._load_failed_reason:
            return False
        return self._gguf_path.is_file() and not self._model_file_error()

    def unavailable_reason(self) -> Optional[str]:
        """Причина недоступности для показа пользователю (или ``None``)."""
        if self._llama is not None:
            return None
        return self._load_failed_reason or (self._model_file_error() or None)

    def runtime_info(self) -> Dict[str, Any]:
        """Bounded diagnostics used by the startup audit and UI telemetry."""
        if self._gpu_offload_supported is None:
            try:
                import llama_cpp
                probe = getattr(llama_cpp, "llama_supports_gpu_offload", None)
                self._gpu_offload_supported = bool(probe()) if callable(probe) else None
            except Exception:
                self._gpu_offload_supported = None
        return {
            "backend": self.name,
            "runtime_backend": "cuda" if self._n_gpu_layers != 0 else "cpu",
            "model_path": str(self._gguf_path),
            "model_exists": self._gguf_path.is_file(),
            "loaded": self.is_loaded,
            "n_gpu_layers": self._n_gpu_layers,
            "n_threads": self._n_threads,
            "n_batch": self._n_batch,
            "n_ctx": self._n_ctx,
            "embedding": self._embedding_mode,
            "load_failed": self._load_failed_reason,
            "warmup_ms": self._warmup_ms,
            "warmup_complete": self._warmup_complete,
            "gpu_offload_supported": self._gpu_offload_supported,
        }

    def close(self) -> None:
        """Выгружает модель из памяти."""
        with self._lock:
            if self._llama is None:
                return
            try:
                closer = getattr(self._llama, "close", None)
                if callable(closer):
                    closer()
            except (RuntimeError, OSError) as exc:
                log.debug("Ошибка при выгрузке локальной модели: %s", exc)
            finally:
                self._llama = None
                log.info("Локальная модель выгружена из памяти")

    # ------------------------------------------------------------------ #
    #  Фабричный конструктор
    # ------------------------------------------------------------------ #

    @classmethod
    def from_settings(cls, settings: Any, model_id: Optional[str] = None,
                      embedding: bool = False) -> "LocalQwenBackend":
        """Создаёт бэкенд из объекта ``Settings``.

        Args:
            settings: объект :class:`config.settings.Settings`.
            model_id: логическое имя модели (по умолчанию — из ``model_tiers.fast``).
            embedding: создать экземпляр в режиме эмбеддингов, используя
                ``local_model.embedding_gguf_path``, если он задан.

        Raises:
            BackendConfigError: путь к модели не указан в конфигурации.
        """
        local = settings.local_model
        if embedding:
            path = local.resolved_embedding_path or local.resolved_gguf_path
        else:
            path = local.resolved_gguf_path

        if path is None:
            raise BackendConfigError(
                "В settings.json не задан local_model.gguf_path — "
                "укажите путь к GGUF-модели Qwen 4B"
            )

        return cls(
            gguf_path=path,
            model_id=model_id or settings.get_model_id("fast") or "qwen-4b-local",
            n_gpu_layers=local.n_gpu_layers,
            n_ctx=local.n_ctx,
            n_threads=local.effective_threads,
            n_batch=local.n_batch,
            temperature=local.temperature,
            max_tokens=local.max_tokens,
            chat_format=local.chat_format,
            verbose=local.verbose,
            embedding=embedding,
        )
