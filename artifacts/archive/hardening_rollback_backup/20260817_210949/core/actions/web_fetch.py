"""Загрузка и извлечение текста веб-страниц (web_fetch).

Инструмент:
- ``WebFetchTool`` — скачивает страницу через requests, извлекает основной
  текст через BeautifulSoup (удаляет script/style/nav/header/footer),
  обрезает до разумной длины (~3000 символов).

Сетевые ошибки не роняют процесс — возвращают ok=False.
"""

from __future__ import annotations

import html
from urllib.parse import urljoin
from typing import Any, Dict

import requests
from bs4 import BeautifulSoup

from config.settings import Settings
from core.actions.base import ActionResult, Tool, ToolContext
from core.actions.registry import DEFAULT_REGISTRY
from core.utils.logger import get_logger

__all__ = ["WebFetchTool", "fetch_page"]

log = get_logger(__name__)

#: User-Agent
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

#: Таймаут
_REQUEST_TIMEOUT = 15

#: Максимальная длина извлечённого текста
_MAX_TEXT_LENGTH = 3000

#: Селекторы для удаления (шум)
_REMOVE_SELECTORS = [
    "script",
    "style",
    "noscript",
    "iframe",
    "svg",
    "canvas",
    "nav",
    "header",
    "footer",
    "aside",
    ".ad",
    ".ads",
    ".advertisement",
    ".cookie",
    ".banner",
    ".popup",
    ".modal",
    ".sidebar",
    ".menu",
    ".navigation",
    "[role=navigation]",
    "[role=banner]",
    "[role=contentinfo]",
]


def fetch_page(url: str, max_length: int = _MAX_TEXT_LENGTH) -> str:
    """Скачивает страницу и извлекает чистый текст.

    Args:
        url: URL страницы (http/https).
        max_length: максимальная длина возвращаемого текста.

    Returns:
        Извлечённый текст (обрезанный до max_length) или пустая строка при ошибке.

    Raises:
        requests.RequestException: при сетевых ошибках (перехватывается в Tool).
    """
    if not url or not url.strip():
        raise ValueError("Пустой URL")

    # Нормализация URL
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # §21/Q05 — SSRF-защита: блокируем внутренние/зарезервированные адреса
    # (loopback, private, link-local/cloud-metadata, file:// и пр.) ДО запроса.
    from core.network_guard import assert_safe_url, safe_redirect_url
    assert_safe_url(url)

    headers = {"User-Agent": _USER_AGENT}
    current_url = url
    resp = None
    for _hop in range(4):
        resp = requests.get(current_url, headers=headers, timeout=_REQUEST_TIMEOUT,
                            allow_redirects=False, stream=True)
        if 300 <= resp.status_code < 400 and resp.headers.get("Location"):
            current_url = safe_redirect_url(current_url, resp.headers["Location"])
            resp.close()
            continue
        break
    if resp is None:
        raise ValueError("Пустой ответ")
    if int(resp.headers.get("Content-Length", "0") or 0) > 5 * 1024 * 1024:
        resp.close()
        raise ValueError("Ответ превышает лимит 5 MB")
    resp.raise_for_status()

    # Определяем кодировку
    resp.encoding = resp.apparent_encoding or "utf-8"

    max_bytes = 5 * 1024 * 1024
    body_buffer = bytearray()
    iterator = getattr(resp, "iter_content", None)
    if callable(iterator):
        for chunk in iterator(64 * 1024):
            if not chunk:
                continue
            body_buffer.extend(chunk)
            if len(body_buffer) > max_bytes:
                resp.close()
                raise ValueError("Ответ превышает лимит 5 MB")
        body = bytes(body_buffer)
    else:
        body = bytes(getattr(resp, "content", b""))[:max_bytes]
    soup = BeautifulSoup(body, "html.parser")

    # Удаляем шум
    for selector in _REMOVE_SELECTORS:
        for elem in soup.select(selector):
            elem.decompose()

    # Пытаемся найти основной контент
    # Приоритет: main, article, .content, .post, .entry, #content
    main_content = None
    for selector in ["main", "article", ".content", ".post", ".entry", "#content", ".main"]:
        main_content = soup.select_one(selector)
        if main_content:
            break

    if main_content is None:
        main_content = soup.body or soup

    # Извлекаем текст
    text = main_content.get_text(separator="\n", strip=True)

    # Нормализуем пробелы
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    # Обрезаем
    if len(text) > max_length:
        text = text[:max_length].rsplit(" ", 1)[0] + "… [обрезано]"

    log.debug("fetch_page: %s -> %d символов", url, len(text))
    return text


import re  # noqa: E402 (после функции для чистоты)


# --------------------------------------------------------------------------- #
# Tool-обёртка
# --------------------------------------------------------------------------- #


class WebFetchTool(Tool):
    """Инструмент: загрузка и извлечение текста веб-страницы."""

    @property
    def name(self) -> str:
        return "web_fetch"

    @property
    def description(self) -> str:
        return (
            "Скачивает веб-страницу по URL и извлекает основной текстовый контент "
            "(удаляет скрипты, стили, навигацию, рекламу). Возвращает до ~3000 символов. "
            "Полезно для чтения статей, документации, новостей."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL страницы (http/https). Можно без схемы — добавится https://.",
                },
                "max_length": {
                    "type": "integer",
                    "description": "Максимальная длина возвращаемого текста.",
                    "default": 3000,
                    "minimum": 500,
                    "maximum": 10000,
                },
            },
            "required": ["url"],
            "additionalProperties": False,
        }

    def run(self, args: Dict[str, Any], context: ToolContext) -> ActionResult:
        url = args["url"]
        max_length = args.get("max_length", _MAX_TEXT_LENGTH)

        try:
            text = fetch_page(url, max_length)
            if not text:
                return ActionResult(
                    tool=self.name,
                    args=args,
                    ok=False,
                    error="Страница загружена, но текст не извлечён (пусто или только скрипты)",
                )

            # §22 — контент из сети это ДАННЫЕ, не команды. Оборачиваем явным
            # конвертом на границе инструмент→модель (wrap_untrusted идемпотентен,
            # дубли не создаёт, если вызывается повторно, напр. из research.py).
            from core.safety import wrap_untrusted
            preview = wrap_untrusted(
                text[:500] + ("…" if len(text) > 500 else ""),
                source=f"web_fetch ({url})",
            )
            return ActionResult(
                tool=self.name,
                args=args,
                ok=True,
                output=f"Содержимое {url}:\n\n{preview}",
            )
        except requests.RequestException as exc:
            log.error("Ошибка загрузки %s: %s", url, exc)
            return ActionResult(
                tool=self.name,
                args=args,
                ok=False,
                error=f"Сетевая ошибка: {exc}",
            )
        except Exception as exc:
            log.error("Ошибка обработки %s: %s", url, exc)
            return ActionResult(
                tool=self.name,
                args=args,
                ok=False,
                error=f"Ошибка извлечения текста: {exc}",
            )


# Авто-регистрация
DEFAULT_REGISTRY.register(WebFetchTool())
