"""Абстрактный контракт LLM-бэкенда.

Все модели совета — и локальная Qwen 4B, и удалённые DeepSeek/Kimi/Claude —
реализуют один интерфейс ``LLMBackend``. Роутер (Часть 2) работает только
с этим интерфейсом и ничего не знает про llama-cpp или requests.

Исключения образуют иерархию, чтобы вызывающий код мог отличить
«модель недоступна» (можно эскалировать/деградировать) от «неверный запрос».
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, Iterable, List, Optional, Sequence

__all__ = [
    "LLMError",
    "BackendUnavailable",
    "BackendConfigError",
    "ToolsNotSupportedError",
    "LLMBackend",
    "normalize_messages",
    "prepend_system",
    "messages_to_prompt",
    "ToolCallResponse",
]

from core.llm.tool_calls import ToolCallResponse


# --------------------------------------------------------------------------- #
#  Исключения
# --------------------------------------------------------------------------- #

class LLMError(RuntimeError):
    """Базовая ошибка работы с языковой моделью."""


class BackendUnavailable(LLMError):
    """Бэкенд недоступен: сеть, все retry исчерпаны, модель не загружается.

    Роутер обязан ловить это исключение и либо переходить к другому тиру,
    либо деградировать до локальной модели с честным сообщением пользователю.
    """


class BackendConfigError(LLMError):
    """Ошибка конфигурации бэкенда: нет ключа, пути, model-id."""


class ToolsNotSupportedError(LLMError):
    """Модель/эндпоинт не поддерживает tool calling."""


# --------------------------------------------------------------------------- #
#  Вспомогательные функции формата сообщений
# --------------------------------------------------------------------------- #

_ALLOWED_ROLES = frozenset({"system", "user", "assistant", "tool"})


def normalize_messages(messages: Optional[Iterable[Dict[str, Any]]]) -> List[Dict[str, str]]:
    """Приводит список сообщений к формату OpenAI chat.

    * оставляет только ключи ``role``/``content``/``name``;
    * выбрасывает записи с неизвестной ролью или пустым содержимым;
    * приводит содержимое к ``str`` (модели не принимают None/числа).
    """
    result: List[Dict[str, str]] = []
    for item in messages or ():
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().lower()
        if role not in _ALLOWED_ROLES:
            continue
        content = item.get("content")
        if content is None:
            continue
        text = content if isinstance(content, str) else str(content)
        if not text.strip():
            continue
        entry: Dict[str, str] = {"role": role, "content": text}
        name = item.get("name")
        if isinstance(name, str) and name.strip():
            entry["name"] = name.strip()
        result.append(entry)
    return result


def prepend_system(messages: Sequence[Dict[str, str]],
                   system: Optional[str]) -> List[Dict[str, str]]:
    """Ставит системный промпт первым сообщением.

    Если системное сообщение уже есть в начале, новый текст дописывается
    к нему через пустую строку — так persona не теряется.
    """
    normalized = normalize_messages(messages)
    system_text = (system or "").strip()
    if not system_text:
        return normalized

    if normalized and normalized[0]["role"] == "system":
        merged = f"{system_text}\n\n{normalized[0]['content']}".strip()
        return [{"role": "system", "content": merged}, *normalized[1:]]
    return [{"role": "system", "content": system_text}, *normalized]


def messages_to_prompt(messages: Sequence[Dict[str, str]]) -> str:
    """Плоский текстовый промпт из истории — fallback без chat-шаблона."""
    role_titles = {
        "system": "Инструкции",
        "user": "Пользователь",
        "assistant": "Ассистент",
        "tool": "Результат инструмента",
    }
    parts: List[str] = []
    for message in normalize_messages(messages):
        title = role_titles.get(message["role"], message["role"])
        parts.append(f"{title}: {message['content']}")
    parts.append("Ассистент:")
    return "\n\n".join(parts)


_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_reasoning_blocks(text: str) -> str:
    """Убирает служебные блоки размышлений (``<think>...</think>``).

    Qwen3 и ряд reasoning-моделей возвращают их в ответе; пользователю и
    TTS они не нужны.
    """
    cleaned = _THINK_BLOCK_RE.sub("", text or "")
    # незакрытый блок в конце потока
    if "<think>" in cleaned.lower():
        cleaned = re.split(r"<think>", cleaned, maxsplit=1, flags=re.IGNORECASE)[0]
    return cleaned.strip()


# --------------------------------------------------------------------------- #
#  Интерфейс бэкенда
# --------------------------------------------------------------------------- #

class LLMBackend(ABC):
    """Единый интерфейс языковой модели.

    Реализации: :class:`core.llm.local_qwen.LocalQwenBackend` и
    :class:`core.llm.remote_api.RemoteAPIBackend`.

    Контракт для реализаций:
        * методы генерации возвращают **чистый текст** без служебных блоков;
        * при недоступности модели поднимается :class:`BackendUnavailable`;
        * ``is_available()`` НЕ поднимает исключений и не делает сетевых
          запросов дольше секунды — это быстрая проверка для роутера.
    """

    #: Человекочитаемое имя бэкенда (для логов): 'local:qwen-4b', 'deepseek:...'.
    name: str = "llm-backend"

    #: Реальный model-id, с которым работает бэкенд.
    model: str = ""

    #: Поддерживает ли бэкенд эмбеддинги.
    supports_embeddings: bool = False

    #: Поддерживает ли бэкенд tool calling (заполняется реализацией).
    supports_tools: bool = False

    # ------------------------------ генерация ------------------------------ #

    @abstractmethod
    def direct(self, prompt: str, system: Optional[str] = None,
               max_tokens: Optional[int] = None,
               temperature: Optional[float] = None) -> str:
        """Один запрос без истории. Возвращает текст ответа.

        Raises:
            BackendUnavailable: модель недоступна.
        """

    @abstractmethod
    def chat(self, messages: List[Dict[str, Any]], system: Optional[str] = None,
             max_tokens: Optional[int] = None,
             temperature: Optional[float] = None) -> str:
        """Диалог с историей сообщений. Возвращает текст ответа.

        Args:
            messages: список ``{"role": ..., "content": ...}``.
            system: системный промпт (persona + контекст памяти).

        Raises:
            BackendUnavailable: модель недоступна.
        """

    @abstractmethod
    def streaming(self, messages: List[Dict[str, Any]], system: Optional[str] = None,
                  max_tokens: Optional[int] = None,
                  temperature: Optional[float] = None) -> Generator[str, None, None]:
        """Потоковая генерация: отдаёт текст порциями (для GUI/TTS).

        Raises:
            BackendUnavailable: модель недоступна.
        """

    def chat_with_tools(self, messages: List[Dict[str, Any]],
                        tools: Sequence[Dict[str, Any]],
                        system: Optional[str] = None,
                        tool_choice: str | Dict[str, Any] = "auto",
                        max_tokens: Optional[int] = None,
                        temperature: Optional[float] = None) -> ToolCallResponse:
        """Optional native function-calling boundary.

        Providers that do not expose structured calls keep the old text/JSON
        planner path by raising :class:`ToolsNotSupportedError`.  The method
        is deliberately non-abstract so existing test and plugin backends do
        not need a flag-day interface change.
        """
        raise ToolsNotSupportedError(
            f"Бэкенд {self.name} не поддерживает нативные tool calls"
        )

    # ------------------------------ эмбеддинги ----------------------------- #

    def embed(self, text: str) -> List[float]:
        """Векторное представление текста.

        Базовая реализация не поддерживает эмбеддинги.

        Raises:
            NotImplementedError: если бэкенд не умеет embeddings.
        """
        raise NotImplementedError(
            f"Бэкенд {self.name} не поддерживает построение эмбеддингов"
        )

    def embed_batch(self, texts: Sequence[str]) -> List[List[float]]:
        """Эмбеддинги для набора текстов. По умолчанию — поштучно."""
        return [self.embed(text) for text in texts]

    # ------------------------------ сервис --------------------------------- #

    @abstractmethod
    def list_models(self) -> List[str]:
        """Список доступных моделей. Пустой список — если узнать нельзя."""

    @abstractmethod
    def warm_up(self) -> None:
        """Прогрев: загрузка весов / проверка эндпоинта.

        Вызывается один раз при старте ``main.py``, чтобы первый ответ
        пользователю не ждал загрузки модели.

        Raises:
            BackendUnavailable: прогрев не удался.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Быстрая проверка доступности. Не поднимает исключений."""

    # ------------------------------ прочее --------------------------------- #

    def close(self) -> None:
        """Освобождает ресурсы (веса модели, HTTP-сессия). По умолчанию — no-op."""
        return None

    def __repr__(self) -> str:
        return f"<{type(self).__name__} name={self.name!r} model={self.model!r}>"
