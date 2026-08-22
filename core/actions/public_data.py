"""Честно бесплатные публичные API (без ключа) для живого Джарвиса.

Набор источников, которые работают БЕЗ api-ключей и без подписок — то, о
чём говорил пользователь («погода, новости и что-то такое»):

    * Новости по запросу — через Google News RSS (свободный, без ключа).
    * Краткая справка/факт — Wikipedia (REST + русская выжимка).
    * Курсы валют — open.er-api.com (бесплатно, без ключа).
    * Геолокация по IP — ipapi.co (как уже в weather.py).

Инструменты регистрируются как обычные ``Tool`` (name/description/
input_schema/run) в ``DEFAULT_REGISTRY`` — тот же паттерн, что weather.py.

Сетевые сбои НЕ роняют процесс: возвращают ActionResult(ok=False) с честной
ошибкой (фикс A3 — никаких canned-«сохранено для повторной попытки»).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from core.actions.base import ActionResult, Tool, ToolContext
from core.actions.registry import DEFAULT_REGISTRY
from core.utils.logger import get_logger

__all__ = [
    "PublicDataTool",
    "news_search",
    "wiki_summary",
    "currency_rates",
]

log = get_logger(__name__)

_TIMEOUT = 10
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Jarvis/2.4"


# --------------------------------------------------------------------------- #
#  Источники (без ключей)
# --------------------------------------------------------------------------- #


from core.data.public_sources import currency_rates, news_search, wiki_summary


# --------------------------------------------------------------------------- #
#  Tool
# --------------------------------------------------------------------------- #


class PublicDataTool(Tool):
    """Инструмент: быстрые факты из бесплатных публичных источников."""

    @property
    def name(self) -> str:
        return "public_data"

    @property
    def description(self) -> str:
        return (
            "Быстрые факты из бесплатных публичных источников (без api-ключа): "
            "новости (news_search), справка (wiki), курсы валют (currency). "
            "usage: {'kind': 'news'|'wiki'|'currency', ...}."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["news", "wiki", "currency"],
                         "description": "Тип запроса"},
                "query": {"type": "string", "description": "Для news/wiki — тема"},
                "max_results": {"type": "integer", "default": 5},
            },
            "required": ["kind"],
            "additionalProperties": False,
        }

    def run(self, args: Dict[str, Any], context: ToolContext) -> ActionResult:
        kind = str(args.get("kind") or "").lower()
        query = str(args.get("query") or "").strip()
        max_results = max(1, min(int(args.get("max_results", 5)), 10))

        try:
            if kind == "news":
                return self._news(query, max_results)
            if kind == "wiki":
                return self._wiki(query)
            if kind == "currency":
                return self._currency()
        except Exception as exc:  # noqa: BLE001
            return ActionResult(self.name, args, False, error=f"public_data: {exc}")
        return ActionResult(self.name, args, False, error=f"unknown kind: {kind}")

    @staticmethod
    def _news(query: str, max_results: int) -> ActionResult:
        if not query:
            return ActionResult("public_data", {"kind": "news"}, False,
                                error="query обязателен для news")
        items = news_search(query, max_results)
        if not items:
            return ActionResult("public_data", {"kind": "news", "query": query},
                                False, error="новости недоступны (сеть/пусто)")
        lines = [f"- {it['title']}\n  {it['url']}" for it in items]
        return ActionResult("public_data", {"kind": "news", "query": query}, True,
                            {"items": items, "text": "\n".join(lines)})

    @staticmethod
    def _wiki(query: str) -> ActionResult:
        if not query:
            return ActionResult("public_data", {"kind": "wiki"}, False,
                                error="query обязателен для wiki")
        text = wiki_summary(query)
        if not text:
            return ActionResult("public_data", {"kind": "wiki", "query": query},
                                False, error="статья не найдена/сеть")
        return ActionResult("public_data", {"kind": "wiki", "query": query}, True,
                            {"text": text})

    @staticmethod
    def _currency() -> ActionResult:
        rates = currency_rates("RUB")
        if not rates:
            return ActionResult("public_data", {"kind": "currency"}, False,
                                error="курсы недоступны (сеть)")
        pick = {k: rates[k] for k in ("USD", "EUR", "KZT", "CNY") if k in rates}
        return ActionResult("public_data", {"kind": "currency"}, True,
                            {"rates": pick})


DEFAULT_REGISTRY.register(PublicDataTool())
