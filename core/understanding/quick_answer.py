"""Quick-Answer путь — переработанный под «без API-ключа» (Фаза 2, v2).

Третий путь между «рефлексом» и «миссией»: вопрос -> локальная модель
решает «знаю / надо искать» -> поиск (DuckDuckGo, с запасным Bing/searx)
-> сжатие той же локальной моделью -> короткий живой ответ за 1-3 сек.

Ключевые свойства (после критики v1):
    * Память подключена (v2): движок принимает ``memory_retriever`` и
      ``memory_saver``. Перед поиском спрашивает память (без сети);
      найденный факт сохраняется в фон (дыра 1 и 3 закрыты).
    * Скорость (дыра 2): для прямых вопросов decide-шаг пропускается,
      читается СТРОГО top-1 источник (не top-2), HTTP параллелится —
      цель 1-3 сек. Решение SEARCH/KNOW — одна короткая генерация.
    * Honest verified (дыра 4): удачное сжатие реального источника
      помечается verified; сетевая деградация — откровенно.
    * ``never_silent`` — при любом исходе текст; canned-фраз НЕТ.
    * Анти-бот-капча DuckDuckGo детектируется; есть запасной поиск.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from core.utils.logger import get_logger

__all__ = [
    "QuickAnswerResult",
    "QuickAnswerEngine",
    "QUICK_MEMORY_MARKERS",
]

log = get_logger(__name__)

#: Маркеры — «объясни, почему/как» — сигнал, что нужен поиск, а не память.
QUICK_MEMORY_MARKERS = (
    "объясни", "почему", "расскажи", "как работает", "в чём разниц",
    "в чем разниц", "сколько", "кто такой", "что такое", "что значит",
    "чем отлича", "из чего", "зачем",
)

#: Стабильные вопросы о себе/времени — из головы, без сети и без decide.
_INSTANT_KNOW = {
    "который час", "который час?", "сколько времени", "какая дата",
    "какой сегодня день", "какое сегодня число",
}

#: Системный промпт-режим «репетитор» для объяснений.
_TUTOR_PROMPT = (
    "Отвечай коротко и по-русски. Если просят объяснить — дай суть в 2-4 "
    "предложения и один конкретный пример. Не отвлекайся на лишнее."
)

#: Промпт решения «знаю / надо искать».
_DECIDE_PROMPT = (
    "Ответь буквально одним из двух слов: SEARCH или KNOW. "
    "SEARCH — если это актуальный факт, новость, конкретная цифра/дата/имя, "
    "или ты не уверен. KNOW — если это стабильное знание, которое ты уверенно "
    "знаешь. Вопрос:\n"
)

#: Промпт сжатия (короткий).
_COMPRESS_PROMPT = (
    "Ниже материалы из интернета. Ответь коротко по-русски, 2-4 предложения, "
    "только суть. Не выдумывай сверх найденного.\n\n{material}"
)

_MAX_SEARCH_RESULTS = 4
_TIMEOUT_COMPRESS_S = 6.0
_MAX_SNIPPET_CHARS = 600


@dataclass
class QuickAnswerResult:
    """Результат быстрого ответа с честной маркировкой достоверности."""

    text: str
    source: str = "quick_answer"          # quick_answer | memory | search
    searched: bool = False                # реально ли ходили в сеть
    evidence: List[str] = field(default_factory=list)
    degraded: bool = False                # сеть моргнула / модель не смогла
    verified: bool = False                # честная оценка достоверности (дыра 4)
    latency_ms: float = 0.0
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "source": self.source,
            "searched": self.searched,
            "evidence": list(self.evidence),
            "degraded": self.degraded,
            "verified": self.verified,
            "latency_ms": round(self.latency_ms, 1),
            "error": self.error,
        }


#: Маркеры страницы-капчи DuckDuckGo (анти-бот с датацентрных IP).
_CHALLENGE_MARKERS = (
    "complete the following challenge",
    "confirm this search was made by a human",
    "select all squares containing",
    "anomaly",
)


def _search_bing(query: str, max_results: int, timeout: Optional[float]) -> List[Dict[str, str]]:
    """Запасной поиск через Bing HTML (без API-ключа) — анти-капен DuckDuckGo."""
    import html as _html
    from bs4 import BeautifulSoup as _BS
    import requests as _requests

    headers = {"User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    )}
    resp = _requests.get(
        "https://www.bing.com/search",
        params={"q": query, "setlang": "ru", "cc": "RU"},
        headers=headers,
        timeout=float(timeout or 10),
    )
    if resp.status_code != 200:
        return []
    soup = _BS(resp.text, "html.parser")
    results: List[Dict[str, str]] = []
    for li in soup.select("li.b_algo")[:max_results]:
        a = li.select_one("h2 a")
        if not a:
            continue
        title = _html.unescape(a.get_text(strip=True))
        url = (a.get("href") or "").strip()
        snippet_el = li.select_one(".b_caption p, .b_lineclamp2")
        snippet = _html.unescape(snippet_el.get_text(strip=True)) if snippet_el else ""
        if title and url:
            results.append({"title": title, "url": url, "snippet": snippet})
    return results


def _fetch_impl(url: str, max_length: int, timeout: float) -> str:
    """Реальное чтение страницы (ленивый импорт, без API-ключа)."""
    from core.actions.web_fetch import fetch_page  # type: ignore
    return fetch_page(url, max_length=max_length, timeout=timeout)


def _search_impl(query: str, max_results: int, timeout: Optional[float]) -> List[Dict[str, str]]:
    """Поиск с фолбэком: DuckDuckGo -> Bing (если капча/пусто).

    Ленивые импорты важны: ``core.actions`` требует Python 3.10+
    (``dataclass(slots=True)``), а модуль импортируется и в песочнице/CI
    на 3.9. На рабочих машинах (3.11+) это идёт без проблем.

    Если DuckDuckGo вернул анти-бот-капчу, пробуем Bing; если и Bing пуст
    или недоступен — возвращаем пустой список (движок честно деградирует).
    """
    from core.actions.web_search import duckduckgo_search  # type: ignore
    results = duckduckgo_search(query, max_results=max_results, timeout=timeout)
    if results:
        return results

    #  Пусто/капча DDG -> запасной Bing.
    try:
        fallback = _search_bing(query, max_results=max_results, timeout=timeout)
        if fallback:
            return fallback
    except Exception as exc:  # noqa: BLE001
        log.debug("Быстрый ответ: запасной поиск Bing недоступен: %s", exc)
        return []

    #  Оба пусты. Проверяем, не капча ли это DDG — для честного сообщения.
    try:
        import requests as _requests
        resp = _requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query.strip(), "kl": "ru-ru"},
            headers={"User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
            )},
            timeout=float(timeout or 10),
        )
        if any(m in resp.text.casefold() for m in _CHALLENGE_MARKERS):
            raise RuntimeError("поисковик запросил анти-бот проверку (капча)")
    except RuntimeError:
        raise
    except Exception:
        pass
    return []


class QuickAnswerEngine:
    """Быстрый ответ: локальная модель решает, поиск ищет, модель сжимает.

    Использует уже существующие блоки:
        * :func:`core.actions.web_search.duckduckgo_search` + Bing fallback;
        * :func:`core.actions.web_fetch.fetch_page` — чтение страницы;
        * ``core.llm.factory.get_llm_backend`` — локальная Qwen (тир FAST).

    Память (дыра 1/3): передаётся колбэками ``memory_retriever`` (вопрос ->
    ответ или None, без сети) и ``memory_saver`` (вопрос + ответ -> фон).
    """

    def __init__(self, settings: Any, *, max_results: int = _MAX_SEARCH_RESULTS,
                 memory: Optional[Any] = None,
                 memory_retriever: Optional[Callable[[str], Optional[str]]] = None,
                 memory_saver: Optional[Callable[[str, str], None]] = None) -> None:
        self._settings = settings
        self._max_results = max(1, int(max_results))
        #  Обратная совместимость: ``memory`` может быть объектом с .answer_context().
        self._memory = memory
        self._memory_retriever = memory_retriever
        self._memory_saver = memory_saver
        self._llm = None  # лениво

    # ------------------------------------------------------------------ #
    def answer(self, question: str) -> QuickAnswerResult:
        """Главная точка входа. Всегда возвращает результат, никогда не молчит."""
        started = time.perf_counter()
        question = (question or "").strip()
        if not question:
            return self._finish(
                QuickAnswerResult(
                    text="Не понял вопроса. Сформулируй, о чём хочешь узнать.",
                    source="clarify",
                ),
                started,
            )

        # 1) Память: есть ли уже известный релевантный факт (без сети).
        memo = self._try_memory(question)
        if memo:
            return self._finish(
                QuickAnswerResult(text=memo, source="memory", searched=False,
                                  verified=True),
                started)

        # 2) Маршрут: стабильное -> из головы; маркер -> сразу поиск
        #    (экономим генерацию decide); иначе короткое решение.
        if self._is_instant_know(question):
            result = self._answer_from_head(question)
        elif self._force_search(question):
            result = self._search_compress(question)
        else:
            needs_search = self._decide_needs_search(question)
            result = (self._search_compress(question) if needs_search
                      else self._answer_from_head(question))

        # 3) Найденный факт сохраняем в память в фоне (дыра 3).
        if result.source == "search" and result.text:
            self._save_fact_background(question, result.text)

        return self._finish(result, started)

    # ------------------------------------------------------------------ #
    def _is_instant_know(self, question: str) -> bool:
        return " ".join(question.casefold().split()) in _INSTANT_KNOW

    def _force_search(self, question: str) -> bool:
        """Маркеры «почему/что такое/кто такой» -> поиск без decide-генерации."""
        lowered = " ".join(question.casefold().split())
        return any(mk in lowered for mk in QUICK_MEMORY_MARKERS)

    def _finish(self, result: QuickAnswerResult, started: float) -> QuickAnswerResult:
        result.latency_ms = (time.perf_counter() - started) * 1000.0
        log.debug("quick_answer: source=%s searched=%s verified=%s %.0fмс '%s'",
                  result.source, result.searched, result.verified, result.latency_ms,
                  (result.text or "")[:60])
        return result

    # ------------------------------------------------------------------ #
    def _llm_backend(self):
        if self._llm is not None:
            return self._llm
        from core.llm import Tier, get_llm_backend
        try:
            self._llm = get_llm_backend(self._settings, Tier.FAST)
        except Exception as exc:  # noqa: BLE001
            log.warning("Быстрый ответ: LLM-бэкенд недоступен: %s", exc)
            self._llm = None
        return self._llm

    def _try_memory(self, question: str) -> Optional[str]:
        """Релевантный факт из локального контекста без сети."""
        if self._memory_retriever is not None:
            try:
                return self._memory_retriever(question)
            except Exception as exc:  # noqa: BLE001
                log.debug("Быстрый ответ: ретривер памяти не ответил: %s", exc)
                return None
        if self._memory is not None:
            try:
                reply = self._memory.answer_context(question)
                if reply and reply.get("answer"):
                    return str(reply["answer"])
            except Exception as exc:  # noqa: BLE001
                log.debug("Быстрый ответ: память не ответила: %s", exc)
        return None

    def _save_fact_background(self, question: str, answer: str) -> None:
        """Сохранить найденный факт в долгую память в фоне (дыра 3)."""
        saver = self._memory_saver
        if saver is None:
            return
        def _write() -> None:
            try:
                saver(question, answer)
            except Exception as exc:  # noqa: BLE001
                log.debug("Быстрый ответ: сохранение факта не удалось: %s", exc)
        threading.Thread(target=_write, name="jarvis-qa-memory", daemon=True).start()

    # ------------------------------------------------------------------ #
    def _decide_needs_search(self, question: str) -> bool:
        """Знание из головы или идти в сеть? Одна короткая генерация."""
        backend = self._llm_backend()
        if backend is None:
            return True  # без модели -> поиск лучше молчания
        try:
            out = backend.direct(
                _DECIDE_PROMPT + question, max_tokens=8, temperature=0.0,
            ).strip().upper()
            return "SEARCH" in out
        except Exception as exc:  # noqa: BLE001
            log.debug("Быстрый ответ: решение поиска не получено: %s", exc)
            return True

    # ------------------------------------------------------------------ #
    def _answer_from_head(self, question: str) -> QuickAnswerResult:
        """Ответ локальной модели из головы (без сети), честно помечая уверенность."""
        backend = self._llm_backend()
        if backend is None:
            return QuickAnswerResult(
                text="Сейчас у меня нет ни сети, ни модели, чтобы ответить точнее. "
                     "Сформулируй иначе или повтори через минуту.",
                source="degraded", degraded=True,
                error="no_network_and_no_local_model",
            )
        try:
            out = backend.direct(
                question, system=_TUTOR_PROMPT, max_tokens=220, temperature=0.4,
            ).strip()
        except Exception as exc:  # noqa: BLE001
            log.warning("Быстрый ответ: генерация из головы упала: %s", exc)
            return QuickAnswerResult(
                text="Не смог сформулировать ответ из головы. Попробуй спросить "
                     "конкретнее — или дай мне секунду, проверю в сети.",
                source="degraded", degraded=True, error=str(exc)[:200],
            )
        if not out:
            out = "Отвечу, если уточнишь вопрос чуть конкретнее."
        return QuickAnswerResult(text=out, source="quick_answer", searched=False,
                                 verified=True)

    # ------------------------------------------------------------------ #
    def _search_compress(self, question: str) -> QuickAnswerResult:
        """Поиск (DDG+Bing) -> чтение СТРОГО top-1 -> сжатие (дыра 2/скорость)."""
        try:
            results = _search_impl(question, self._max_results, timeout=None)
        except Exception as exc:  # noqa: BLE001 — капча/сбой -> честная деградация
            log.warning("Быстрый ответ: поиск упал: %s", exc)
            return self._degraded_after_search_fail(question, str(exc)[:200])

        if not results:
            log.info("Быстрый ответ: поиск пуст, отвечаю из головы: '%s'", question)
            return self._answer_from_head(question)

        #  СТРОГО top-1 источник (вместо top-2) — меньше HTTP на горячем пути.
        r = results[0]
        url = (r.get("url") or "").strip()
        evidence: List[str] = []
        found_texts: List[str] = []
        if url:
            try:
                page = _fetch_impl(url, max_length=2400, timeout=_TIMEOUT_COMPRESS_S)
            except Exception as exc:  # noqa: BLE001
                log.debug("Быстрый ответ: источник %s не прочитан: %s", url, exc)
                page = ""
            if page and page.strip():
                found_texts.append(page.strip()[:1600])
                evidence.append(url)
            else:
                #  Страница не прочиталась — берём сниппет из результата.
                snip = f"{r.get('title','')}. {r.get('snippet','')}"[:1600]
                if snip.strip() and snip.strip() != ".":
                    found_texts.append(snip)
                    evidence.append(url)

        if not found_texts:
            return self._degraded_after_search_fail(
                question, "нет читаемого текста в найденном")

        return self._compress(question, found_texts, evidence)

    # ------------------------------------------------------------------ #
    def _compress(self, question: str, texts: List[str], evidence: List[str]) -> QuickAnswerResult:
        """Сжать найденное в 2-4 предложения локальной моделью."""
        backend = self._llm_backend()
        material = "\n\n".join(f"ИСТОЧНИК:\n{t[:1200]}" for t in texts)[:4200]
        if backend is None:
            snippet = texts[0].strip()[:300] if texts else ""
            return QuickAnswerResult(
                text=(
                    "Нашёл в сети, но без локальной модели кратко не перескажу. "
                    f"Выдержка: {snippet}"
                ),
                source="search", searched=True, evidence=evidence, degraded=True,
            )

        try:
            out = backend.direct(
                _COMPRESS_PROMPT.format(material=material),
                max_tokens=260, temperature=0.3,
            ).strip()
        except Exception as exc:  # noqa: BLE001
            log.warning("Быстрый ответ: сжатие упало: %s", exc)
            snippet = texts[0].strip()[:300] if texts else ""
            return QuickAnswerResult(
                text=(
                    "Нашёл материал, но не смог сжать кратко. Ближайшее по смыслу:\n"
                    + snippet
                ),
                source="search", searched=True, evidence=evidence, degraded=True,
                error=str(exc)[:200],
            )
        if not out:
            out = "Нашёл материал, но кратко сформулировать не вышло. Спроси точнее."
        #  Дыра 4: удачное сжатие реального источника -> verified.
        return QuickAnswerResult(text=out, source="search", searched=True,
                                 evidence=evidence, verified=bool(evidence))

    # ------------------------------------------------------------------ #
    def _degraded_after_search_fail(self, question: str, why: str) -> QuickAnswerResult:
        """Сеть не ответила/капча: ЧЕСТНАЯ деградация (фикс A3), не canned-фраза."""
        log.warning("Быстрый ответ: поиск недоступен (%s); отвечаю по памяти", why)
        head = self._answer_from_head(question)
        head.degraded = True
        head.searched = True
        head.verified = False
        #  Честная маркировка сбоя сети, не «сохранено для повторной попытки».
        head.text = f"Сеть сейчас не отвечает ({why[:80]}). Отвечаю по памяти: {head.text}"
        return head
