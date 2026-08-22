"""Честно бесплатные публичные источники без API-ключей.

Это чистый слой данных: без импорта core.actions, чтобы его можно было
тестировать и использовать отдельно от реестра инструментов.
"""
from __future__ import annotations
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from urllib.parse import quote_plus
import requests

_TIMEOUT = 10
_USER_AGENT = "Jarvis/2.4 public-data client"


def news_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    if not (query or '').strip():
        return []
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=ru&gl=RU&ceid=RU:ru"
    try:
        response = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=_TIMEOUT)
        response.raise_for_status()
        root = ET.fromstring(response.text)
    except (requests.RequestException, ET.ParseError):
        return []
    out = []
    for item in root.iter("item"):
        if len(out) >= max(1, min(int(max_results), 10)):
            break
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if title and link:
            out.append({"title": title, "url": link})
    return out


def wiki_summary(topic: str, lang: str = "ru") -> Optional[str]:
    if not (topic or '').strip():
        return None
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote_plus(topic)}"
    try:
        response = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=_TIMEOUT)
        response.raise_for_status()
        extract = (response.json().get("extract") or "").strip()
        return extract or None
    except (requests.RequestException, ValueError):
        return None


def currency_rates(base: str = "RUB") -> Optional[Dict[str, float]]:
    url = f"https://open.er-api.com/v6/latest/{(base or 'RUB').upper()}"
    try:
        response = requests.get(url, timeout=_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return None
    if data.get("result") != "success":
        return None
    return {str(k): float(v) for k, v in (data.get("rates") or {}).items()}
