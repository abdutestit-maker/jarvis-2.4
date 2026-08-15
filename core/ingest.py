"""Ingest — приём и обработка ОГРОМНЫХ входов (§5).

Пользователь может прислать огромный ТЗ, документацию, книгу, большой кусок
кода, десятки файлов, длинную переписку. Это НОРМАЛЬНАЯ задача. НЕЛЬЗЯ
отвечать "слишком длинный запрос / не могу обработать" только из-за размера.

LARGE REQUEST -> INGEST -> CHUNK / SUMMARIZE / INDEX -> MISSION -> PROCESS -> SYNTHESIS

Модуль:
    1. принимает input (строка или список файлов);
    2. определяет размер;
    3. разбивает на части (chunking по границам предложений/абзацев);
    4. строит индекс (заголовки/ключевые фразы) для быстрого поиска;
    5. сохраняет промежуточные результаты в data/ingest/<task_id>/;
    6. предоставляет retrieval по чанкам (извлечение релевантного).

НЕ зависит от LLM — работает на чистом тексте. Если доступна локальная
модель, вызывающий (agent) может суммаризировать чанки, но сам ingest
детерминирован и дешёв.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config.settings import Settings
from core.utils.logger import get_logger
from core.utils.paths import PROJECT_ROOT, resolve_path

__all__ = ["IngestedInput", "ingest_text", "ingest_files", "IngestStore"]

log = get_logger(__name__)


# Границы предложений/абзацев для аккуратного разбиения.
_SENT_SPLIT = re.compile(r"(?<=[\.\!\?])\s+|(?<=[\.\!\?])\n+|\n{2,}")
_WORD_SPLIT = re.compile(r"\s+")


def _estimate_tokens(text: str) -> int:
    """Грубая оценка токенов (~1.3 слова/токен для рус/англ смешанного)."""
    words = len(_WORD_SPLIT.findall(text))
    return max(1, int(words / 1.3))


@dataclass
class IngestedInput:
    """Результат приёма большого input."""

    task_id: str
    source_kind: str              # "text" | "files" | "mixed"
    raw_char_count: int
    estimated_tokens: int
    chunk_count: int
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    index: List[Dict[str, Any]] = field(default_factory=list)   # заголовки/якоря
    store_dir: Optional[Path] = None
    meta: Dict[str, Any] = field(default_factory=dict)


def _chunk_text(text: str, max_chars: int = 4000, overlap: int = 200) -> List[Dict[str, Any]]:
    """Разбивает текст на чанки по границам предложений с перекрытием.

    Алгоритм: сначала делим по абзацам/предложениям, набираем окно <= max_chars,
    перекрываем на overlap символов, чтобы не терять контекст на стыках.
    """
    sentences = [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]
    chunks: List[Dict[str, Any]] = []
    buf: List[str] = []
    buf_len = 0
    idx = 0
    i = 0
    n = len(sentences)

    def flush() -> None:
        nonlocal buf, buf_len, idx
        if not buf:
            return
        body = " ".join(buf)
        chunks.append({
            "index": idx,
            "char_count": buf_len,
            "tokens": _estimate_tokens(body),
            "text": body,
            "head": body[:120],
        })
        idx += 1
        buf = []
        buf_len = 0

    while i < n:
        s = sentences[i]
        sl = len(s) + 1
        if buf_len + sl > max_chars and buf:
            flush()
            # перекрытие: добавляем последнее предложение снова (если влезает)
            if buf and overlap > 0:
                last = buf[-1]
                if len(last) <= overlap:
                    buf = [last]
                    buf_len = len(last) + 1
                else:
                    buf = []
                    buf_len = 0
        buf.append(s)
        buf_len += sl
        i += 1
    flush()

    # Если весь текст — одно гигантское "предложение" (нет точек), режем жёстко.
    if not chunks and text.strip():
        for start in range(0, len(text), max_chars - overlap):
            piece = text[start:start + max_chars].strip()
            if piece:
                chunks.append({
                    "index": len(chunks),
                    "char_count": len(piece),
                    "tokens": _estimate_tokens(piece),
                    "text": piece,
                    "head": piece[:120],
                })
    return chunks


def _build_index(chunks: List[Dict[str, Any]], raw_text: str) -> List[Dict[str, Any]]:
    """Строит лёгкий индекс: первые строки-заголовки и ключевые слова.

    Индекс помогает agent быстро найти релевантный чанк без перечитывания всего.
    """
    index: List[Dict[str, Any]] = []
    # Якоря по маркдаун-заголовкам и нумерованным секциям.
    for m in re.finditer(r"^(#{1,6}\s+.+|(\d+\.)+\s+[A-ZА-Я].+|[IVXLC]+\.\s+[A-ZА-Я].+)", raw_text, re.MULTILINE):
        line = m.group(0).strip()
        # к какому чанку ближе всего
        pos = m.start()
        near = None
        for c in chunks:
            if c["text"] in raw_text and raw_text.find(c["text"]) <= pos <= raw_text.find(c["text"]) + len(c["text"]):
                near = c["index"]
                break
        index.append({"anchor": line[:80], "char_pos": pos, "chunk_index": near})
    # Если заголовков нет — индекс по "head" первых 10 чанков.
    if not index:
        for c in chunks[:10]:
            index.append({"anchor": c["head"][:80], "char_pos": -1, "chunk_index": c["index"]})
    return index


def ingest_text(task_id: str, text: str, settings: Optional[Settings] = None,
               max_chars: int = 4000, overlap: int = 200) -> IngestedInput:
    """Принимает большой текст, разбивает на чанки, индексирует, сохраняет.

    НЕ падает на больших размерах — единственное реальное ограничение:
    нехватка диска (обрабатывается как исключение, ловится вызывающим).
    """
    char_count = len(text)
    tokens = _estimate_tokens(text)
    chunks = _chunk_text(text, max_chars=max_chars, overlap=overlap)
    index = _build_index(chunks, text)

    ingested = IngestedInput(
        task_id=task_id,
        source_kind="text",
        raw_char_count=char_count,
        estimated_tokens=tokens,
        chunk_count=len(chunks),
        chunks=chunks,
        index=index,
    )
    store_dir = _persist(ingested, text, settings)
    ingested.store_dir = store_dir
    log.info("Ingest text: %d символов, ~%d токенов, %d чанков (task=%s)",
             char_count, tokens, len(chunks), task_id)
    return ingested


def ingest_files(task_id: str, files: List[str], settings: Optional[Settings] = None,
                 max_chars: int = 4000, overlap: int = 200) -> IngestedInput:
    """Принимает несколько файлов, объединяет в единый пронумерованный текст."""
    parts: List[str] = []
    seen: Dict[str, int] = {}
    for f in files:
        p = resolve_path(f)
        if p is None or not Path(p).is_file():
            log.warning("Ingest: файл не найден, пропускаю: %s", f)
            continue
        try:
            data = Path(p).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            log.warning("Ingest: не удалось прочитать %s: %s", f, exc)
            continue
        header = f"\n\n=== FILE: {Path(p).name} ===\n"
        parts.append(header + data)
        seen[str(p)] = len(data)
    combined = "\n".join(parts)
    ingested = ingest_text(task_id, combined, settings, max_chars=max_chars, overlap=overlap)
    ingested.source_kind = "files"
    ingested.meta["files"] = {k: v for k, v in seen.items()}
    return ingested


def _persist(ingested: IngestedInput, raw_text: str,
             settings: Optional[Settings]) -> Optional[Path]:
    """Сохраняет сырьё и чанки в data/ingest/<task_id>/ для долгой обработки."""
    try:
        if settings is not None:
            base = settings.paths.resolved("data_dir") or (PROJECT_ROOT / "data")
        else:
            base = PROJECT_ROOT / "data"
        store = Path(base) / "ingest" / ingested.task_id
        store.mkdir(parents=True, exist_ok=True)
        (store / "raw.txt").write_text(raw_text, encoding="utf-8")
        # Индекс чанков как JSON (без полного текста — экономим память при чтении).
        import json
        (store / "chunks.json").write_text(
            json.dumps(
                [{"index": c["index"], "char_count": c["char_count"],
                  "tokens": c["tokens"], "head": c["head"]} for c in ingested.chunks],
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )
        (store / "index.json").write_text(
            json.dumps(ingested.index, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return store
    except OSError as exc:
        log.warning("Ingest: не удалось сохранить промежуточные данные: %s", exc)
        return None


class IngestStore:
    """Ленивый доступ к чанкам из data/ingest/<task_id>/.

    Позволяет agent извлекать только релевантные чанки (по ключевым словам),
    не загружая весь большой input в prompt целиком.
    """

    def __init__(self, store_dir: Path) -> None:
        self._dir = Path(store_dir)
        self._raw: Optional[str] = None

    @classmethod
    def open(cls, task_id: str, settings: Optional[Settings] = None) -> "IngestStore":
        if settings is not None:
            base = settings.paths.resolved("data_dir") or (PROJECT_ROOT / "data")
        else:
            base = PROJECT_ROOT / "data"
        return cls(Path(base) / "ingest" / task_id)

    def exists(self) -> bool:
        return self._dir.is_dir()

    def raw(self) -> str:
        if self._raw is None:
            rp = self._dir / "raw.txt"
            self._raw = rp.read_text(encoding="utf-8", errors="replace") if rp.exists() else ""
        return self._raw

    def retrieve(self, query: str, top_k: int = 5) -> List[str]:
        """Извлекает топ-k наиболее релевантных чанков по ключевым словам запроса."""
        raw = self.raw()
        q_words = {w.lower() for w in _WORD_SPLIT.findall(query) if len(w) > 2}
        if not q_words:
            # без ключевых слов — вернём начало
            return [raw[:4000]]
        chunks = _chunk_text(raw)
        scored: List[Tuple[int, str]] = []
        for c in chunks:
            text_l = c["text"].lower()
            score = sum(1 for w in q_words if w in text_l)
            if score:
                scored.append((score, c["text"]))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in scored[:top_k]]
