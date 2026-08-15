"""Proxy-клиент LLM (П1 §1.4) — ключ автора НЕ в клиенте.

J.A.R.V.I.S. НЕ должен хранить ключ автора в клиенте на машине
пользователя. Вместо этого клиент шлёт запрос на ЛОКАЛЬНЫЙ
proxy-сервер (``settings.proxy.endpoint``), а ключ автора добавляется
СЕРВЕРОМ при форвардинге к реальному провайдеру.

В заголовках клиента — только локальный ``proxy_token`` (маркер доступа
к локальному proxy), НЕ ключ провайдера. Сам proxy-сервер — отдельная
инфра-задача (см. docs/P1_BLOCKERS.md, BLOCKER-1), в этом спринте не
реализуется, но клиентская часть готова и НЕ вшивает секрет автора.

Клиент совместим с OpenAI-форматом (``/chat/completions``) — proxy-сервер
ожидается той же формы.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Generator, List, Optional

import requests
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.llm.backend import (
    BackendConfigError,
    BackendUnavailable,
    LLMBackend,
    prepend_system,
)
from core.llm.remote_api import RetryableHTTPError
from core.utils.logger import get_logger

__all__ = ["ProxyLLMClient", "PROXY_HEADER_NAME"]

log = get_logger(__name__)

#: Имя заголовка, которым клиент аутентифицируется перед локальным proxy.
#: НЕ путать с ключом провайдера — это отдельный, локальный маркер.
PROXY_HEADER_NAME = "X-Jarvis-Proxy-Token"

#: Статусы HTTP, при которых повтор осмыслен.
_RETRYABLE_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504, 522, 524})


class ProxyLLMClient(LLMBackend):
    """Клиент, шлющий запросы на локальный proxy-сервер, а не на провайдера.

    Аргумент ``proxy_token`` — это локальный маркер доступа к proxy, НЕ ключ
    провайдера. Ключ автора остаётся на сервере и в клиент не передаётся.
    """

    supports_tools = True

    def __init__(
        self,
        provider: str,
        model_id: str,
        proxy_endpoint: str,
        proxy_token: str = "",
        timeout: float = 15.0,
        max_retries: int = 3,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> None:
        self.provider = (provider or "").strip().lower()
        self.model = (model_id or "").strip()
        self.name = f"proxy:{self.provider}:{self.model}"
        self._proxy_endpoint = (proxy_endpoint or "").strip().rstrip("/")
        self._proxy_token = (proxy_token or "").strip()
        self._timeout = float(timeout)
        self._max_retries = max(1, int(max_retries))
        self._temperature = float(temperature)
        self._max_tokens = int(max_tokens)

        if not self._proxy_endpoint:
            raise BackendConfigError(
                "Proxy-клиент: не задан proxy_endpoint "
                "(settings.proxy.endpoint — куда слать запросы вместо провайдера)"
            )
        if not self.model:
            raise BackendConfigError(
                f"Для провайдера '{self.provider}' не указан model-id "
                f"(settings.json -> model_tiers.<тир>)"
            )

        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "living-jarvis/0.1",
            # Ключ автора НЕ передаётся. Только локальный proxy-маркер.
            PROXY_HEADER_NAME: self._proxy_token,
        })

    # ------------------------------------------------------------------ #
    #  Низкий уровень
    # ------------------------------------------------------------------ #

    def _headers(self) -> Dict[str, str]:
        """Заголовки: локальный proxy-token, НЕ ключ провайдера (П1 §1.4)."""
        return {
            "Content-Type": "application/json",
            "User-Agent": "living-jarvis/0.1",
            PROXY_HEADER_NAME: self._proxy_token,
        }

    def _chat_url(self) -> str:
        """URL локального proxy, а НЕ прямого endpoint провайдера."""
        return f"{self._proxy_endpoint}/chat/completions"

    def _build_payload(self, messages, system, max_tokens, temperature, stream):
        tokens = int(max_tokens) if max_tokens else self._max_tokens
        temp = self._temperature if temperature is None else float(temperature)
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": prepend_system(messages, system),
            "max_tokens": tokens,
            "temperature": temp,
            # Передаём провайдера серверу, чтобы он знал, куда форвардить
            # и какой ключ подставить (ключ живёт на сервере).
            "provider": self.provider,
        }
        if stream:
            payload["stream"] = True
        return payload

    @staticmethod
    def _error_snippet(response: requests.Response) -> str:
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
        return json.dumps(data, ensure_ascii=False)[:300]

    def _request(self, payload, stream=False):
        url = self._chat_url()
        try:
            response = self._session.post(
                url, headers=self._headers(), json=payload,
                timeout=self._timeout, stream=stream,
            )
        except requests.Timeout as exc:
            raise BackendUnavailable(f"Прокси-таймаут {self._timeout}с: {url}") from exc
        except requests.ConnectionError as exc:
            raise BackendUnavailable(f"Нет соединения с proxy {url}: {exc}") from exc
        except requests.RequestException as exc:
            raise BackendUnavailable(f"Сбой запроса к proxy {url}: {exc}") from exc

        if response.status_code in _RETRYABLE_STATUS:
            snippet = self._error_snippet(response)
            response.close()
            raise RetryableHTTPError(response.status_code, snippet)
        if response.status_code >= 400:
            snippet = self._error_snippet(response)
            response.close()
            raise BackendUnavailable(
                f"Proxy вернул HTTP {response.status_code}: {snippet}"
            )
        return response

    # ------------------------------------------------------------------ #
    #  LLMBackend API
    # ------------------------------------------------------------------ #

    def chat(self, messages, system=None, max_tokens=None, temperature=None,
             stream: bool = False) -> str:
        payload = self._build_payload(messages, system, max_tokens, temperature, stream)
        started = time.perf_counter()
        try:
            for attempt in Retrying(
                stop=stop_after_attempt(self._max_retries),
                wait=wait_exponential(multiplier=1, min=1, max=10),
                # RetryableHTTPError (429/5xx) — повторяем; BackendUnavailable
                # (постоянная ошибка) — нет.
                retry=retry_if_exception_type(RetryableHTTPError),
                reraise=True,
            ):
                with attempt:
                    response = self._request(payload, stream=False)
                    data = response.json()
                    response.close()
                    content = _extract_content(data)
                    log.info("Proxy LLM OK | %s | %.2fs", self.name,
                             time.perf_counter() - started)
                    return content
        except RetryableHTTPError:
            # Исчерпаны попытки на временной ошибке — деградируем честно.
            raise BackendUnavailable(
                f"Proxy {self.name}: исчерпаны попытки после временных сбоев"
            )
        except Exception as exc:  # noqa: BLE001
            log.error("Proxy LLM вызов упал: %s", exc)
            raise BackendUnavailable(f"Proxy LLM недоступен: {exc}") from exc

    def direct(self, prompt: str, system=None, max_tokens=None, temperature=None) -> str:
        messages = [{"role": "user", "content": prompt}]
        if system:
            messages.insert(0, {"role": "system", "content": system})
        return self.chat(messages, system=None, max_tokens=max_tokens,
                         temperature=temperature)

    def streaming(self, messages, system=None, max_tokens=None, temperature=None):
        payload = self._build_payload(messages, system, max_tokens, temperature, True)
        try:
            response = self._request(payload, stream=True)
            for line in response.iter_lines():
                if not line:
                    continue
                text = line.decode("utf-8") if isinstance(line, bytes) else line
                if text.startswith("data:"):
                    text = text[5:].strip()
                if text in ("[DONE]", ""):
                    continue
                try:
                    data = json.loads(text)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    piece = delta.get("content")
                    if piece:
                        yield piece
                except ValueError:
                    continue
        except Exception as exc:  # noqa: BLE001
            log.warning("Proxy streaming упал: %s", exc)

    def list_models(self) -> List[str]:
        return [self.model]

    def warm_up(self) -> None:
        try:
            self.chat([{"role": "user", "content": "ping"}], max_tokens=1,
                      temperature=0.0)
        except Exception as exc:  # noqa: BLE001
            log.debug("Proxy warm_up не удался: %s", exc)

    def is_available(self) -> bool:
        return bool(self._proxy_endpoint and self.model)

    def close(self) -> None:
        try:
            self._session.close()
        except (OSError, RuntimeError) as exc:
            log.debug("Ошибка закрытия proxy-сессии: %s", exc)


def _extract_content(data: Dict[str, Any]) -> str:
    """Извлекает текст ответа из OpenAI-совместимого JSON."""
    if isinstance(data, dict):
        choices = data.get("choices") or []
        if choices:
            msg = choices[0].get("message") or {}
            return str(msg.get("content") or "")
    return ""
