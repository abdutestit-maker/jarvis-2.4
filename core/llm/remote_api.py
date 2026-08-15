"""Удалённый бэкенд: OpenAI-совместимые API (DeepSeek / Kimi / Claude).

Реализовано ровно то, что требует контракт совета мудрецов:
    * retry на 429 и 5xx — 3 попытки с экспоненциальной задержкой (tenacity);
    * timeout из ``settings.limits.response_timeout_sec``;
    * при исчерпании попыток — :class:`BackendUnavailable`, а не голый traceback;
    * каждый вызов логируется: модель, latency, успех/ошибка.

Anthropic Claude поддерживается через его нативный ``/v1/messages`` —
он не OpenAI-совместим по формату, поэтому для провайдера ``claude``
включается отдельный диалект запроса/ответа.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Generator, List, Optional

import requests
from tenacity import (
    RetryCallState,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.llm.backend import (
    BackendConfigError,
    BackendUnavailable,
    LLMBackend,
    normalize_messages,
    prepend_system,
    strip_reasoning_blocks,
)
from core.utils.logger import get_logger

__all__ = ["RemoteAPIBackend", "RetryableHTTPError"]

log = get_logger(__name__)

#: Коды, при которых повтор осмыслен.
_RETRYABLE_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504, 522, 524})

#: Провайдеры с нативным Anthropic-диалектом.
_ANTHROPIC_PROVIDERS = frozenset({"claude", "anthropic"})

_ANTHROPIC_VERSION = "2023-06-01"


class RetryableHTTPError(RuntimeError):
    """Временная ошибка HTTP (429/5xx) — имеет смысл повторить запрос."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code


class RemoteAPIBackend(LLMBackend):
    """Клиент удалённой модели через ``requests``.

    Args:
        provider: имя провайдера ('deepseek' / 'kimi' / 'claude' / 'openrouter').
        model_id: реальный model-id, который уходит в запрос.
        base_url: базовый URL без завершающего слэша.
        api_key: ключ авторизации.
        timeout: таймаут одного HTTP-запроса, сек.
        max_retries: сколько всего попыток делать (включая первую).
        temperature: температура по умолчанию.
        max_tokens: лимит генерации по умолчанию.
    """

    supports_tools = True

    def __init__(
        self,
        provider: str,
        model_id: str,
        base_url: str,
        api_key: Optional[str],
        timeout: float = 15.0,
        max_retries: int = 3,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> None:
        self.provider = (provider or "").strip().lower()
        self.model = (model_id or "").strip()
        self.name = f"{self.provider}:{self.model}"
        self._base_url = (base_url or "").strip().rstrip("/")
        self._api_key = (api_key or "").strip() or None
        self._timeout = float(timeout)
        self._max_retries = max(1, int(max_retries))
        self._temperature = float(temperature)
        self._max_tokens = int(max_tokens)

        if not self.model:
            raise BackendConfigError(
                f"Для провайдера '{self.provider}' не указан model-id "
                f"(settings.json -> model_tiers)"
            )
        if not self._base_url:
            raise BackendConfigError(
                f"Для провайдера '{self.provider}' не указан endpoint "
                f"(settings.json -> api_endpoints.{self.provider})"
            )

        self._is_anthropic = self.provider in _ANTHROPIC_PROVIDERS
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "living-jarvis/0.1",
        })

    # ------------------------------------------------------------------ #
    #  Низкий уровень: заголовки, URL, тело запроса
    # ------------------------------------------------------------------ #

    def _headers(self) -> Dict[str, str]:
        """Заголовки авторизации в диалекте провайдера."""
        if not self._api_key:
            raise BackendConfigError(
                f"Не задан API-ключ провайдера '{self.provider}' "
                f"(settings.json -> api_keys.{self.provider} "
                f"или переменная окружения JARVIS_{self.provider.upper()}_API_KEY)"
            )
        if self._is_anthropic:
            return {"x-api-key": self._api_key, "anthropic-version": _ANTHROPIC_VERSION}
        return {"Authorization": f"Bearer {self._api_key}"}

    def _chat_url(self) -> str:
        """URL эндпоинта диалога."""
        if self._is_anthropic:
            return f"{self._base_url}/messages"
        return f"{self._base_url}/chat/completions"

    def _build_payload(self, messages: List[Dict[str, str]], system: Optional[str],
                       max_tokens: Optional[int], temperature: Optional[float],
                       stream: bool) -> Dict[str, Any]:
        """Собирает тело запроса под диалект провайдера."""
        tokens = int(max_tokens) if max_tokens else self._max_tokens
        temp = self._temperature if temperature is None else float(temperature)

        if self._is_anthropic:
            # Anthropic: system — отдельное поле, роль 'tool' не поддерживается
            normalized = normalize_messages(messages)
            system_parts: List[str] = []
            if system and system.strip():
                system_parts.append(system.strip())
            dialogue: List[Dict[str, str]] = []
            for message in normalized:
                if message["role"] == "system":
                    system_parts.append(message["content"])
                elif message["role"] == "tool":
                    dialogue.append({
                        "role": "user",
                        "content": f"[Результат инструмента]\n{message['content']}",
                    })
                else:
                    dialogue.append({"role": message["role"], "content": message["content"]})

            payload: Dict[str, Any] = {
                "model": self.model,
                "messages": dialogue,
                "max_tokens": tokens,
                "temperature": temp,
            }
            if system_parts:
                payload["system"] = "\n\n".join(system_parts)
            if stream:
                payload["stream"] = True
            return payload

        payload = {
            "model": self.model,
            "messages": prepend_system(messages, system),
            "max_tokens": tokens,
            "temperature": temp,
        }
        if stream:
            payload["stream"] = True
        return payload

    @staticmethod
    def _error_snippet(response: requests.Response) -> str:
        """Короткая выжимка ошибки из тела ответа."""
        try:
            data = response.json()
        except ValueError:
            return (response.text or "")[:300]
        if isinstance(data, dict):
            error = data.get("error")
            if isinstance(error, dict):
                return str(error.get("message") or error)[:300]
            if isinstance(error, str):
                return error[:300]
            message = data.get("message")
            if message:
                return str(message)[:300]
        return json.dumps(data, ensure_ascii=False)[:300]

    def _request(self, payload: Dict[str, Any], stream: bool = False) -> requests.Response:
        """Один HTTP-запрос. Поднимает ``RetryableHTTPError`` на 429/5xx.

        Raises:
            RetryableHTTPError: временная ошибка, повтор осмыслен.
            BackendUnavailable: постоянная ошибка (401/404/400 и пр.).
        """
        url = self._chat_url()
        try:
            response = self._session.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=self._timeout,
                stream=stream,
            )
        except requests.Timeout as exc:
            raise RetryableHTTPError(408, f"таймаут {self._timeout} с при обращении к {url}") from exc
        except requests.ConnectionError as exc:
            raise RetryableHTTPError(503, f"нет соединения с {url}: {exc}") from exc
        except requests.RequestException as exc:
            raise BackendUnavailable(f"Сбой HTTP-запроса к {url}: {exc}") from exc

        if response.status_code in _RETRYABLE_STATUS:
            snippet = self._error_snippet(response)
            response.close()
            raise RetryableHTTPError(response.status_code, snippet)

        if response.status_code >= 400:
            snippet = self._error_snippet(response)
            status = response.status_code
            response.close()
            hint = ""
            if status in (401, 403):
                # Конфигурационная ошибка: ключ пуст/невалиден/отклонён
                # провайдером. Совет мудрецов ДОЛЖЕН явно сообщить об этом
                # пользователю (а не тихо откатываться на локальную модель).
                hint = (f" Проверьте api_keys.{self.provider} в settings.json — "
                        f"ключ отклонён провайдером.")
                raise BackendConfigError(
                    f"Провайдер {self.provider} вернул HTTP {status}: {snippet}.{hint}"
                )
            elif status == 404:
                hint = (f" Проверьте api_endpoints.{self.provider} и model_tiers: "
                        f"модель '{self.model}' не найдена по адресу {url}.")
            raise BackendUnavailable(
                f"Провайдер {self.provider} вернул HTTP {status}: {snippet}.{hint}"
            )
        return response

    def _log_retry(self, state: RetryCallState) -> None:
        """Пишет в лог каждую неудачную попытку."""
        exception = state.outcome.exception() if state.outcome else None
        log.warning(
            "Повтор запроса к %s (попытка %d/%d): %s",
            self.name, state.attempt_number, self._max_retries, exception,
        )

    def _request_with_retry(self, payload: Dict[str, Any],
                            stream: bool = False) -> requests.Response:
        """HTTP-запрос с exponential backoff по ``RetryableHTTPError``.

        Raises:
            BackendUnavailable: все попытки исчерпаны либо ошибка постоянная.
        """
        started = time.perf_counter()
        last_error: Optional[BaseException] = None
        try:
            for attempt in Retrying(
                stop=stop_after_attempt(self._max_retries),
                wait=wait_exponential(multiplier=1, min=1, max=10),
                retry=retry_if_exception_type(RetryableHTTPError),
                before_sleep=self._log_retry,
                reraise=True,
            ):
                with attempt:
                    response = self._request(payload, stream=stream)
                    log.info(
                        "LLM-вызов OK | модель=%s | latency=%.2f с | попытка=%d",
                        self.name, time.perf_counter() - started,
                        attempt.retry_state.attempt_number,
                    )
                    return response
        except RetryableHTTPError as exc:
            last_error = exc
        except BackendUnavailable as exc:
            log.error("LLM-вызов ОШИБКА | модель=%s | latency=%.2f с | %s",
                      self.name, time.perf_counter() - started, exc)
            raise

        log.error(
            "LLM-вызов ПРОВАЛ | модель=%s | latency=%.2f с | попыток=%d | %s",
            self.name, time.perf_counter() - started, self._max_retries, last_error,
        )
        raise BackendUnavailable(
            f"Провайдер {self.provider} недоступен: исчерпаны {self._max_retries} "
            f"попыток. Последняя ошибка: {last_error}"
        )

    # ------------------------------------------------------------------ #
    #  Разбор ответа
    # ------------------------------------------------------------------ #

    def _extract_text(self, data: Dict[str, Any]) -> str:
        """Достаёт текст ответа из JSON в диалекте провайдера."""
        if self._is_anthropic:
            blocks = data.get("content") or []
            parts = [
                str(block.get("text", ""))
                for block in blocks
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            return strip_reasoning_blocks("".join(parts))

        choices = data.get("choices") or []
        if not choices:
            return ""
        first = choices[0]
        message = first.get("message") if isinstance(first, dict) else None
        if isinstance(message, dict):
            content = message.get("content")
            # некоторые провайдеры отдают reasoning отдельным полем
            if not content:
                content = message.get("reasoning_content") or ""
            return strip_reasoning_blocks(str(content))
        return strip_reasoning_blocks(str(first.get("text", "")))

    # ------------------------------------------------------------------ #
    #  Публичный интерфейс LLMBackend
    # ------------------------------------------------------------------ #

    def chat(self, messages: List[Dict[str, Any]], system: Optional[str] = None,
             max_tokens: Optional[int] = None,
             temperature: Optional[float] = None) -> str:
        """Диалог с историей. Возвращает текст ответа."""
        normalized = normalize_messages(messages)
        if not normalized:
            raise ValueError("chat(): пустой список сообщений")

        payload = self._build_payload(normalized, system, max_tokens, temperature, stream=False)
        response = self._request_with_retry(payload)
        try:
            data = response.json()
        except ValueError as exc:
            raise BackendUnavailable(
                f"Провайдер {self.provider} вернул не-JSON ответ: {exc}"
            ) from exc
        finally:
            response.close()

        if not isinstance(data, dict):
            raise BackendUnavailable(f"Провайдер {self.provider} вернул неожиданный формат ответа")

        text = self._extract_text(data)
        if not text.strip():
            log.warning("Пустой ответ от %s", self.name)
        return text

    def direct(self, prompt: str, system: Optional[str] = None,
               max_tokens: Optional[int] = None,
               temperature: Optional[float] = None) -> str:
        """Одиночный запрос без истории."""
        if not (prompt or "").strip():
            raise ValueError("direct(): пустой prompt")
        return self.chat([{"role": "user", "content": prompt}], system=system,
                         max_tokens=max_tokens, temperature=temperature)

    def _iter_sse_lines(self, response: requests.Response) -> Generator[Dict[str, Any], None, None]:
        """Разбирает Server-Sent Events в словари JSON."""
        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            line = raw_line.strip()
            if not line.startswith("data:"):
                continue
            chunk = line[len("data:"):].strip()
            if not chunk or chunk == "[DONE]":
                if chunk == "[DONE]":
                    return
                continue
            try:
                parsed = json.loads(chunk)
            except json.JSONDecodeError:
                log.debug("Пропущен нечитаемый SSE-чанк от %s", self.name)
                continue
            if isinstance(parsed, dict):
                yield parsed

    def streaming(self, messages: List[Dict[str, Any]], system: Optional[str] = None,
                  max_tokens: Optional[int] = None,
                  temperature: Optional[float] = None) -> Generator[str, None, None]:
        """Потоковая генерация через SSE."""
        normalized = normalize_messages(messages)
        if not normalized:
            raise ValueError("streaming(): пустой список сообщений")

        payload = self._build_payload(normalized, system, max_tokens, temperature, stream=True)
        response = self._request_with_retry(payload, stream=True)
        try:
            for event in self._iter_sse_lines(response):
                if self._is_anthropic:
                    if event.get("type") == "content_block_delta":
                        delta = event.get("delta") or {}
                        piece = delta.get("text")
                        if piece:
                            yield str(piece)
                    continue
                choices = event.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                piece = delta.get("content")
                if piece:
                    yield str(piece)
        except requests.RequestException as exc:
            raise BackendUnavailable(
                f"Поток от {self.provider} прервался: {exc}"
            ) from exc
        finally:
            response.close()

    def embed(self, text: str) -> List[float]:
        """Эмбеддинг через ``/embeddings`` (если провайдер поддерживает)."""
        if self._is_anthropic:
            raise NotImplementedError(
                "Anthropic не предоставляет эндпоинт эмбеддингов — "
                "используйте эмбеддер ChromaDB (Часть 3)"
            )
        if not (text or "").strip():
            raise ValueError("embed(): пустой текст")

        url = f"{self._base_url}/embeddings"
        started = time.perf_counter()
        try:
            response = self._session.post(
                url,
                headers=self._headers(),
                json={"model": self.model, "input": text},
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise BackendUnavailable(f"Сбой запроса эмбеддинга к {url}: {exc}") from exc

        try:
            if response.status_code >= 400:
                raise BackendUnavailable(
                    f"Эмбеддинги {self.provider}: HTTP {response.status_code} — "
                    f"{self._error_snippet(response)}"
                )
            data = response.json()
        except ValueError as exc:
            raise BackendUnavailable(f"Эмбеддинги {self.provider}: не-JSON ответ: {exc}") from exc
        finally:
            response.close()

        items = (data or {}).get("data") or []
        if not items:
            raise BackendUnavailable(f"Эмбеддинги {self.provider}: пустой ответ")
        log.debug("embed OK | модель=%s | latency=%.2f с", self.name,
                  time.perf_counter() - started)
        return [float(value) for value in (items[0].get("embedding") or [])]

    def list_models(self) -> List[str]:
        """Список моделей провайдера (пустой, если эндпоинт недоступен)."""
        if self._is_anthropic:
            return [self.model]
        url = f"{self._base_url}/models"
        try:
            response = self._session.get(url, headers=self._headers(), timeout=min(self._timeout, 8.0))
        except (requests.RequestException, BackendConfigError) as exc:
            log.debug("list_models(%s) недоступен: %s", self.provider, exc)
            return []
        try:
            if response.status_code >= 400:
                log.debug("list_models(%s): HTTP %s", self.provider, response.status_code)
                return []
            data = response.json()
        except ValueError:
            return []
        finally:
            response.close()

        items = (data or {}).get("data") or []
        names: List[str] = []
        for item in items:
            if isinstance(item, dict):
                model_id = item.get("id") or item.get("name")
                if model_id:
                    names.append(str(model_id))
        return names

    def warm_up(self) -> None:
        """Проверяет доступность: один запрос на 1 токен.

        Raises:
            BackendUnavailable: провайдер недоступен или ключ отклонён.
        """
        started = time.perf_counter()
        self.chat([{"role": "user", "content": "ping"}], max_tokens=1, temperature=0.0)
        log.info("Прогрев %s завершён за %.2f с", self.name, time.perf_counter() - started)

    def is_available(self) -> bool:
        """Быстрая проверка конфигурации без сетевых запросов."""
        return bool(self._api_key and self._base_url and self.model)

    def close(self) -> None:
        """Закрывает HTTP-сессию."""
        try:
            self._session.close()
        except (OSError, RuntimeError) as exc:
            log.debug("Ошибка закрытия сессии %s: %s", self.name, exc)

    # ------------------------------------------------------------------ #
    #  Фабричный конструктор
    # ------------------------------------------------------------------ #

    @classmethod
    def from_settings(cls, settings: Any, provider: str,
                      model_id: Optional[str] = None) -> "RemoteAPIBackend":
        """Создаёт бэкенд из объекта ``Settings``.

        Поддерживает ДВА режима (П1 §1.4 — ключ автора НЕ в клиенте):

        * прямой (по умолчанию): клиент сам шлёт запрос провайдеру,
          передавая ``api_key`` провайдера в заголовке. Ключ берётся из
          settings.json/api_keys или переменной окружения.
        * proxy (рекомендуется): клиент шлёт запрос на ЛОКАЛЬНЫЙ
          proxy-сервер (``settings.proxy.endpoint``), а ключ автора
          добавляется СЕРВЕРОМ (он живёт только на сервере, не в клиенте).
          В заголовках клиента — только локальный ``proxy_token``, НЕ ключ
          провайдера. Включается, когда ``settings.proxy.enabled = True``.

        Raises:
            BackendConfigError: нет endpoint / ключа / model-id.
        """
        name = (provider or "").strip().lower()
        proxy = getattr(settings, "proxy", None)
        use_proxy = bool(getattr(proxy, "enabled", False)) and bool(getattr(proxy, "endpoint", ""))

        if use_proxy:
            # ---- PROXY-РЕЖИМ: ключ автора НЕ попадает в клиент ----
            from core.llm.proxy_client import PROXY_HEADER_NAME, ProxyLLMClient
            endpoint = (getattr(proxy, "endpoint") or "").strip().rstrip("/")
            proxy_token = getattr(proxy, "proxy_token", "") or ""
            if not endpoint:
                raise BackendConfigError(
                    f"Proxy-режим включён, но не задан settings.proxy.endpoint "
                    f"(куда слать запросы вместо провайдера)"
                )
            # Честный резолв model-id: ищем тир, обслуживаемый этим
            # провайдером, и берём его model-id (П1 §1.4). provider != tier,
            # поэтому get_model_id() нельзя звать напрямую с именем провайдера.
            model_id_resolved = model_id
            if not model_id_resolved:
                from core.llm.tiers import Tier
                for _tier in Tier:
                    if settings.get_provider(_tier) == name:
                        model_id_resolved = settings.get_model_id(_tier)
                        break
            if not model_id_resolved:
                raise BackendConfigError(
                    f"Для провайдера '{name}' не указан model-id "
                    f"(settings.json -> model_tiers.<тир>)"
                )
            return ProxyLLMClient(  # type: ignore[return-value]
                provider=name,
                model_id=model_id_resolved,
                proxy_endpoint=endpoint,
                proxy_token=proxy_token,
                timeout=settings.limits.response_timeout_sec,
                max_retries=settings.limits.max_retries,
                temperature=0.7,
                max_tokens=2048,
            )

        # ---- ПРЯМОЙ режим (ключ провайдера в клиенте) ----
        endpoint = settings.get_endpoint(name)
        if not endpoint:
            raise BackendConfigError(
                f"Не задан endpoint провайдера '{name}' "
                f"(settings.json -> api_endpoints.{name})"
            )
        api_key = settings.get_api_key(name)
        if not api_key:
            raise BackendConfigError(
                f"Не задан API-ключ провайдера '{name}' "
                f"(settings.json -> api_keys.{name})"
            )
        return cls(
            provider=name,
            model_id=model_id or "",
            base_url=endpoint,
            api_key=api_key,
            timeout=settings.limits.response_timeout_sec,
            max_retries=settings.limits.max_retries,
        )
