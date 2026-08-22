"""Профиль вкусов (TasteProfile) — музыка/медиа «по душе» хранится структурно.

Поддерживает музыкальный сценарий из архитектуры: «бро, поставь музыку,
скучна» -> движок понимает настроение и подбирает треки под профиль вкуса.

Дизайн повторяет проверенный паттерн ``PreferenceLearner``
(``core/memory/relationship/learning.py``): файл-JSON под RLock + опциональная
запись фактов в ``RelationshipMemoryStore.remember`` для поиска по смыслу.

Осознанно вдохновлено (MIT/Apache доноры, без копирования кода):
    * vibe-music-agent (crownkrebs) — профиль вкуса evolves из accept/reject,
      «Negative space» (что НЕ слушает) учитывается;
    * spotAIfy (theautoroboto) — «аудио-хватка» (energy/valence/tempo buckets)
      как отдельная грань помимо жанров/артистов.

Структура профиля (JSON):
    {
      "genres":  {"rock": 0.8, "lo-fi": 0.4},   # жанр -> сила предпочтения 0..1
      "artists": {"queen": 0.9},                # исполнитель -> сила
      "moods":   {"energetic": 0.8, "calm": 0.5},
      "audio":   {"energy": "low", "valence": "mix", "tempo": "slow"},
      "negative_space": ["опера"],              # что пользователь НЕ любит
      "signals": {"count": 12, "accepted": 8, "rejected": 3, "ignored": 1},
      "updated_at": "ISO"
    }
"""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from core.utils.logger import get_logger

__all__ = [
    "TasteProfile",
    "DEFAULT_TASTE",
    "extract_taste_signals",
]

log = get_logger(__name__)

#: Поля профиля по умолчанию (пустые — заполняется из общения).
DEFAULT_TASTE: Dict[str, Any] = {
    "genres": {},
    "artists": {},
    "moods": {},
    "audio": {"energy": "", "valence": "", "tempo": ""},
    "negative_space": [],
    "signals": {"count": 0, "accepted": 0, "rejected": 0, "ignored": 0},
    "updated_at": "",
}

# --------------------------------------------------------------------------- #
#  Русские сигнал-карты: настроения, эмоции, команды музыки/медиа
# --------------------------------------------------------------------------- #

#: Слово -> настроение (мood bucket). Совпадает с «скучна» -> low-energy.
MOOD_KEYWORDS: Dict[str, str] = {
    "скучн": "calm", "спокойн": "calm", "расслаб": "calm", "лоу": "calm",
    "устал": "calm", "сонн": "calm", "тих": "calm", "медленн": "calm",
    "грустн": "sad", "меланхол": "sad", "тосклив": "sad", "лиричн": "sad",
    "весел": "energetic", "бодр": "energetic", "энергичн": "energetic",
    "праздник": "energetic", "кача": "energetic", "зажигат": "energetic",
    "спорт": "energetic", "зарядк": "energetic", "тренировк": "energetic",
    "фокус": "focus", "работа": "focus", "учёб": "focus", "концентр": "focus",
    "кодинг": "focus", "работать": "focus",
}

#: Слово -> жанр (явная просьба о жанре).
GENRE_KEYWORDS: Dict[str, str] = {
    "рок": "rock", "метал": "metal", "поп": "pop", "хаус": "house",
    "техно": "techno", "реп": "rap", "хип-хоп": "hip-hop",
    "джаз": "jazz", "блюз": "blues", "классик": "classical",
    "ло-фай": "lo-fi", "lofi": "lo-fi", "дабстеп": "dubstep",
    "диско": "disco", "фанк": "funk", "соул": "soul", "кантри": "country",
    "шансон": "chanson", "эмбиент": "ambient", "загородн": "indie",
}

#: Ключевые слова, что включили медиа (чтобы не трактовать любой текст как вкус).
MEDIA_TRIGGERS = (
    "поставь музыку", "включи музыку", "поставь песню", "включи песню",
    "поставь трек", "музыку по", "что послушать", "послушаем", "поставь что-нибудь",
    "включи что-нибудь", "музыка", "playlist", "трек", "песню", "песня",
)


def extract_taste_signals(text: str) -> Dict[str, Any]:
    """Извлечь сигналы вкуса из реплики пользователя (жанр, настроение).

    Returns:
        {"media_request": bool, "mood": str|"", "genre": str|"", "artist_hint": str|""}
    """
    lowered = " ".join((text or "").casefold().replace("ё", "е").split())
    mood = ""
    genre = ""
    for word, m in MOOD_KEYWORDS.items():
        if word in lowered:
            mood = m
            break
    for word, g in GENRE_KEYWORDS.items():
        if word in lowered:
            genre = g
            break
    media_request = any(t in lowered for t in MEDIA_TRIGGERS)
    # Хинт на исполнителя: «что-нибудь в духе X», «похоже на X».
    artist_hint = ""
    m = re.search(r"(?:в духе|похоже на|что-нибудь как|типа)\s+([\w .'-]{2,30})", lowered)
    if m:
        artist_hint = m.group(1).strip()
    return {
        "media_request": media_request,
        "mood": mood,
        "genre": genre,
        "artist_hint": artist_hint,
    }


# --------------------------------------------------------------------------- #
#  Профиль вкусов
# --------------------------------------------------------------------------- #


class TasteProfile:
    """Структурный профиль музыкальных/медийных предпочтений.

    Файловое хранилище под RLock (как ``PreferenceLearner``). Опционально
    транслирует осмысленные факты в сущностную память через ``store.remember``.
    """

    def __init__(self, directory: Path | str,
                 store: Optional[Any] = None) -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)
        self.path = self._dir / "taste_profile.json"
        self._store = store
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = {}

    # ------------------------------------------------------------------ #
    #  Чтение
    # ------------------------------------------------------------------ #
    def load(self) -> Dict[str, Any]:
        """Загрузить профиль (дефолт при отсутствии/ошибке)."""
        if not self.path.is_file():
            self._data = json.loads(json.dumps(DEFAULT_TASTE))
            return self._data
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Taste-profile повреждён (%s), дефолт: %s", self.path, exc)
            self._data = json.loads(json.dumps(DEFAULT_TASTE))
            return self._data
        merged = json.loads(json.dumps(DEFAULT_TASTE))
        if isinstance(raw, dict):
            _deep_update(merged, raw)
        self._data = merged
        return self._data

    def _save(self) -> None:
        self._data["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        tmp.replace(self.path)

    # ------------------------------------------------------------------ #
    #  Обучение из реплик
    # ------------------------------------------------------------------ #
    def observe(self, text: str, *, source: str = "user_input") -> Dict[str, Any]:
        """Извлечь и записать сигнал вкуса из реплики (жанр/настроение/артист).

        Не трактует произвольный текст как сигнал: требует медиа-триггер или
        явный жанр/настроение.
        """
        sig = extract_taste_signals(text)
        if not (sig["media_request"] or sig["genre"] or sig["mood"]):
            return {}
        with self._lock:
            data = self.load()
            changed = False
            if sig["genre"]:
                self._bump(data, "genres", sig["genre"], delta=0.15)
                changed = True
            if sig["mood"]:
                self._bump(data, "moods", sig["mood"], delta=0.15)
                changed = True
            if sig["artist_hint"]:
                self._bump(data, "artists", sig["artist_hint"], delta=0.2)
                changed = True
            if changed:
                self._save()
            return sig

    def _bump(self, data: Dict[str, Any], bucket: str, key: str, delta: float) -> None:
        key = str(key).strip().casefold()
        if not key:
            return
        cur = float((data.get(bucket) or {}).get(key, 0.0))
        data[bucket][key] = round(min(1.0, cur + delta), 3)

    # ------------------------------------------------------------------ #
    #  Обратная связь на предложение
    # ------------------------------------------------------------------ #
    def record_suggestion_outcome(self, *, genre: Optional[str] = None,
                                  artist: Optional[str] = None,
                                  outcome: str) -> float:
        """Оценить отклик пользователя на предложенный трек/плейлист.

        ``outcome``: accepted/rejected/ignored. Возвращает уверенность
        предпочтения (как delegation_confidence у PreferenceLearner).
        """
        result = str(outcome or "ignored").casefold()
        if result not in {"accepted", "useful", "rejected", "ignored", "failed"}:
            result = "ignored"
        bucket = ("accepted" if result in {"accepted", "useful"}
                  else ("rejected" if result in {"rejected", "failed"} else "ignored"))
        with self._lock:
            data = self.load()
            sig = data["signals"] or {}
            sig["count"] = int(sig.get("count", 0)) + 1
            sig[bucket] = int(sig.get(bucket, 0)) + 1
            data["signals"] = sig
            # Усиливаем/ослабим по жанру/артисту.
            key = genre or artist
            if key:
                if bucket == "accepted":
                    self._bump(data, "genres" if genre else "artists",
                               key, delta=0.25)
                elif bucket == "rejected":
                    self._decay(data, "genres" if genre else "artists", key)
            a = int(sig.get("accepted", 0))
            r = int(sig.get("rejected", 0))
            ig = int(sig.get("ignored", 0))
            confidence = (a + 1) / (a + r + 0.5 * ig + 2)
            confidence = round(max(0.0, min(1.0, confidence)), 3)
            self._save()
            if genre and bucket == "accepted" and self._store is not None:
                self._remember_fact(f"Пользователь любит жанр {genre}",
                                    confidence=0.8, key=f"taste:genre:{genre}")
            if artist and bucket == "rejected" and self._store is not None:
                self._remember_fact(f"Пользователю не зашёл исполнитель {artist}",
                                    confidence=0.7, key=f"taste:artist:{artist}")
            return confidence

    def _decay(self, data: Dict[str, Any], bucket: str, key: str) -> None:
        key = str(key).strip().casefold()
        if not key:
            return
        cur = float((data.get(bucket) or {}).get(key, 0.0))
        data[bucket][key] = round(max(0.0, cur - 0.3), 3)

    # ------------------------------------------------------------------ #
    #  Ранжирование (эталон «поставь музыку»)
    # ------------------------------------------------------------------ #
    def score(self, candidates: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Отсортировать кандидатов треков/плейлистов по вкусу.

        Candidate: {"id", "title", "genre"?, "artist"?, "mood"?, "energy"?}
        Returns: список кандидатов с добавленным ``_taste`` (0..1).
        """
        data = self.load()
        genres = data.get("genres") or {}
        artists = data.get("artists") or {}
        moods = data.get("moods") or {}
        neg = [str(x).casefold() for x in (data.get("negative_space") or [])]
        scored: List[Tuple[float, Dict[str, Any]]] = []
        for cand in candidates:
            g = str((cand.get("genre") or "")).casefold()
            a = str((cand.get("artist") or "")).casefold()
            m = str((cand.get("mood") or "")).casefold()
            score = 0.0
            if g:
                score += 0.5 * float(genres.get(g, 0.0))
            if a:
                score += 0.4 * float(artists.get(a, 0.0))
            if m:
                score += 0.4 * float(moods.get(m, 0.0))
            # Negative space: резкий штраф, учитываем в СОРТИРОВКЕ (не клампим
            # в 0 раньше времени, иначе «не любит» сравняется с «не знаю»).
            if g in neg or a in neg:
                score -= 1.0
            item = dict(cand)
            item["_taste"] = round(max(0.0, min(1.0, score)), 3)
            scored.append((score, item))
        # Сортируем по внутреннему (неклампированному) скору.
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored]

    # ------------------------------------------------------------------ #
    #  Контекст и факты
    # ------------------------------------------------------------------ #
    def context(self, *, max_chars: int = 400) -> str:
        """Человекочитаемая выжимка к профилю для промпта."""
        data = self.load()
        parts: List[str] = []
        genres = sorted(data.get("genres") or {}, key=lambda k: -data["genres"][k])
        if genres:
            parts.append("Вкус (жанры): " + ", ".join(
                f"{g}~{data['genres'][g]:.2f}" for g in genres[:5]))
        artists = sorted(data.get("artists") or {}, key=lambda k: -data["artists"][k])
        if artists:
            parts.append("Нравится: " + ", ".join(artists[:5]))
        moods = sorted(data.get("moods") or {}, key=lambda k: -data["moods"][k])
        if moods:
            parts.append("Настроения: " + ", ".join(moods[:3]))
        if data.get("negative_space"):
            parts.append("Не любит: " + ", ".join(data["negative_space"][:4]))
        text = ". ".join(parts).strip()
        return text[:max_chars]

    def _remember_fact(self, fact: str, *, confidence: float, key: str) -> None:
        try:
            self._store.remember(fact, source="taste_learning", confidence=confidence,
                                 importance=0.8, category="preference", key=key,
                                 ttl_days=365)
        except Exception as exc:  # noqa: BLE001
            log.debug("Taste: не удалось записать факт в память: %s", exc)


def _deep_update(base: Dict[str, Any], patch: Dict[str, Any]) -> None:
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_update(base[k], v)
        else:
            base[k] = v
