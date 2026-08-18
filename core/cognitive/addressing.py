"""Contextual fuzzy name recognition without a large alias dictionary."""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.cognitive.identity import AtlasIdentityCore
from core.security.atomic import atomic_json_write, load_json

_TOKEN = re.compile(r"[a-zа-яё]+", re.IGNORECASE)
_CALL_MARKERS = {"эй", "слушай", "hey"}
_COMMAND_PREFIX = re.compile(
    r"(?i)^(откро|глян|посмотр|покаж|сдела|продолж|скаж|провер|запуст|закро|"
    r"найд|помог|верн|попроб|ты$|как$|что$|где$)"
)
_ADJECTIVE_SUFFIX = re.compile(r"(?i)^атлас(н|ный|ная|ное|ные|ного|ной|ную|ным|ных)\w*$")


def _now(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    return current if current.tzinfo else current.replace(tzinfo=timezone.utc)


def _normalize(value: str) -> str:
    return "".join(_TOKEN.findall((value or "").casefold().replace("ё", "е")))


def _distance(left: str, right: str) -> int:
    """Small Damerau-Levenshtein implementation for address-sized strings."""
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    matrix = [[0] * (len(right) + 1) for _ in range(len(left) + 1)]
    for i in range(len(left) + 1):
        matrix[i][0] = i
    for j in range(len(right) + 1):
        matrix[0][j] = j
    for i in range(1, len(left) + 1):
        for j in range(1, len(right) + 1):
            cost = 0 if left[i - 1] == right[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j] + 1,
                matrix[i][j - 1] + 1,
                matrix[i - 1][j - 1] + cost,
            )
            if i > 1 and j > 1 and left[i - 1] == right[j - 2] and left[i - 2] == right[j - 1]:
                matrix[i][j] = min(matrix[i][j], matrix[i - 2][j - 2] + cost)
    return matrix[-1][-1]


def _similarity(candidate: str, root: str) -> float:
    if candidate.startswith(root) and len(candidate) - len(root) <= 3:
        return 0.96 - 0.02 * (len(candidate) - len(root))
    distance = _distance(candidate, root)
    return max(0.0, 1.0 - distance / max(len(candidate), len(root), 1))


def _phonetic(value: str) -> str:
    normalized = _normalize(value)
    translit = str.maketrans({
        "а": "a", "о": "a", "я": "a", "э": "a", "е": "a", "и": "a",
        "ы": "a", "у": "a", "ю": "a", "й": "i", "с": "s", "з": "s",
        "т": "t", "д": "t", "л": "l", "р": "r", "ш": "s", "ж": "s",
    })
    converted = normalized.translate(translit)
    return re.sub(r"[aeiou]+", "a", converted)


@dataclass(frozen=True)
class AddressMatch:
    addressed_to_atlas: bool
    confidence: float
    evidence: tuple[str, ...] = ()
    candidate: str = ""
    remaining_text: str = ""


class AddressFormStore:
    """Persists only repeatedly confirmed, name-like forms."""

    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "address_forms.json"
        self._lock = threading.RLock()

    def confirm(self, form: str, *, similarity: float,
                now: datetime | None = None) -> None:
        value = _normalize(form)
        if not (3 <= len(value) <= 20) or similarity < 0.6 or not value.isalpha():
            return
        with self._lock:
            data = self._load()
            entry = dict((data.get("forms") or {}).get(value) or {})
            entry["confirmed"] = int(entry.get("confirmed", 0)) + 1
            entry["last_confirmed"] = _now(now).isoformat()
            forms = dict(data.get("forms") or {})
            forms[value] = entry
            self._save({"version": 1, "forms": forms})

    def learned_forms(self) -> tuple[str, ...]:
        forms = self._load().get("forms") or {}
        return tuple(sorted(
            form for form, entry in forms.items()
            if isinstance(entry, dict) and int(entry.get("confirmed", 0)) >= 3
        ))

    def _load(self) -> dict:
        try:
            value = load_json(self.path, default={})
            return value if isinstance(value, dict) else {}
        except (OSError, TypeError, ValueError):
            return {}

    def _save(self, value: dict) -> None:
        atomic_json_write(self.path, value)


class AddressRecognizer:
    def __init__(self, store: AddressFormStore,
                 identity: AtlasIdentityCore | None = None,
                 *, conversation_window_seconds: int = 90) -> None:
        self.store = store
        self.identity = identity or AtlasIdentityCore()
        self.conversation_window = timedelta(seconds=max(5, conversation_window_seconds))
        self._last_confirmed: datetime | None = None

    def recognize(self, text: str, *, conversational_context: bool = False,
                  now: datetime | None = None) -> AddressMatch:
        utterance = (text or "").strip()
        tokens = list(_TOKEN.finditer(utterance.casefold().replace("ё", "е")))
        current = _now(now)
        if not tokens:
            return AddressMatch(False, 0.0)

        learned = set(self.store.learned_forms())
        legacy = {_normalize(alias) for alias in self.identity.compatibility_aliases}
        best: tuple[float, re.Match[str] | None, list[str], float] = (0.0, None, [], 0.0)
        for index, match in enumerate(tokens[:4]):
            candidate = _normalize(match.group(0))
            if _ADJECTIVE_SUFFIX.match(candidate):
                continue
            is_legacy = candidate in legacy
            root_scores = [_similarity(candidate, root) for root in self.identity.address_roots]
            string_score = max(root_scores)
            phonetic_score = max(
                (1.0 if _phonetic(candidate) == _phonetic(root) else 0.0)
                for root in self.identity.address_roots
            )
            if candidate in learned:
                string_score = max(string_score, 0.92)
            if is_legacy:
                string_score = 1.0
            if string_score < 0.55 and not is_legacy:
                continue

            evidence: list[str] = [f"string_similarity={string_score:.2f}"]
            score = 0.55 * string_score + 0.12 * phonetic_score
            if phonetic_score:
                evidence.append("phonetic_match")
            if is_legacy:
                score, evidence = 0.91, ["legacy_alias"]
            if candidate in learned:
                score += 0.12
                evidence.append("learned_confirmed_form")
            previous = tokens[index - 1].group(0) if index else ""
            after_marker = previous in _CALL_MARKERS
            if index == 0:
                score += 0.08
                evidence.append("sentence_initial")
            if after_marker:
                score += 0.16
                evidence.append("call_marker")
            punctuation_tail = utterance[match.end():].lstrip()
            has_address_punctuation = bool(punctuation_tail.startswith((",", "?", "!", ":")))
            if has_address_punctuation:
                score += 0.14
                evidence.append("address_punctuation")
            following = tokens[index + 1].group(0) if index + 1 < len(tokens) else ""
            command_follows = bool(following and _COMMAND_PREFIX.match(following))
            if command_follows:
                score += 0.13
                evidence.append("command_or_dialogue_follows")
            if len(tokens) == 1 and utterance.rstrip().endswith("?"):
                score += 0.16
                evidence.append("direct_question")
            # Exact noun use should not wake merely because it resembles the name.
            if not (after_marker or has_address_punctuation or command_follows or len(tokens) == 1):
                score -= 0.28
                evidence.append("noun_context_penalty")
            if index > 0 and not after_marker:
                score -= 0.18
                evidence.append("mid_sentence_penalty")
            if score > best[0]:
                best = (score, match, evidence, string_score)

        recent = (
            conversational_context and self._last_confirmed is not None
            and current - self._last_confirmed <= self.conversation_window
        )
        if best[1] is None and recent:
            return AddressMatch(True, 0.78, ("recent_address_state",), "", utterance)
        if best[1] is None:
            return AddressMatch(False, 0.0)

        score, match, evidence, _ = best
        if recent:
            score += 0.08
            evidence.append("recent_address_state")
        confidence = round(max(0.0, min(0.99, score)), 3)
        remaining = self._remove_address(utterance, match)
        return AddressMatch(
            confidence >= 0.7, confidence, tuple(evidence),
            _normalize(match.group(0)), remaining,
        )

    def confirm(self, match: AddressMatch, *, accepted: bool,
                now: datetime | None = None) -> None:
        if not accepted or not match.addressed_to_atlas:
            return
        self._last_confirmed = _now(now)
        if match.candidate:
            similarity = max(_similarity(match.candidate, root) for root in self.identity.address_roots)
            if (match.candidate not in self.identity.address_roots
                    and not self.identity.matches_legacy(match.candidate)):
                self.store.confirm(match.candidate, similarity=similarity, now=now)

    @staticmethod
    def _remove_address(utterance: str, match: re.Match[str]) -> str:
        before = utterance[:match.start()].strip()
        if _normalize(before) in _CALL_MARKERS:
            before = ""
        after = utterance[match.end():].lstrip(" ,:!?—-")
        return " ".join(part for part in (before, after) if part).strip()


__all__ = ["AddressFormStore", "AddressMatch", "AddressRecognizer"]
