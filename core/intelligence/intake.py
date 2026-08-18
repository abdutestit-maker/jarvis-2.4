"""Fast, local request understanding with a deliberate-path escape hatch."""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from .contracts import TaskContract


class IntentFamily(str, Enum):
    CONVERSATION = "conversation"
    EXPLAIN = "explain"
    TEACH = "teach"
    SOLVE = "solve"
    INSTALL = "install"
    CONFIGURE = "configure"
    OPERATE = "operate"
    RESEARCH = "research"
    CREATE = "create"
    MONITOR = "monitor"


_RULES: tuple[tuple[IntentFamily, tuple[str, ...], str], ...] = (
    (IntentFamily.INSTALL, ("установи", "установить", "поставь программу", "install", "setup"), "setup"),
    (IntentFamily.CONFIGURE, ("настрой", "настроить", "как в инструкции", "configure"), "setup"),
    (IntentFamily.TEACH, ("научи", "домашн", "дз", "урок", "подготовь меня"), "tutor"),
    (IntentFamily.SOLVE, ("реши", "вычисли", "задач", "solve", "ответ"), "tutor"),
    (IntentFamily.EXPLAIN, ("объясни", "что такое", "почему", "как работает", "explain"), "tutor"),
    (IntentFamily.RESEARCH, ("найди информацию", "найди книгу", "поищи", "исследуй", "изучи", "сравни", "проверь документацию", "research", "search", "find"), "research"),
    (IntentFamily.MONITOR, ("следи", "наблюдай", "отслеживай", "monitor"), "monitor"),
    (IntentFamily.OPERATE, ("открой", "запусти", "закрой", "поставь музыку", "который час", "громче", "тише", "напомни", "open", "launch", "play"), "conversation"),
    (IntentFamily.CREATE, ("создай", "сделай файл", "напиши", "сгенерируй", "create"), "operator"),
)


class UniversalIntake:
    """No-model classifier used before heavier planning."""

    def __init__(self, *, max_input_chars: int = 4000) -> None:
        self.max_input_chars = max(100, int(max_input_chars))

    def classify(self, text: str, *, attachments: Iterable[str | Path] | None = None,
                 constraints: Iterable[str] | None = None) -> TaskContract:
        raw = " ".join(str(text or "").split())[: self.max_input_chars]
        lowered = raw.casefold()
        family = IntentFamily.CONVERSATION
        mode = "conversation"
        confidence = 0.45 if raw else 0.0
        for candidate, markers, candidate_mode in _RULES:
            if any(marker.casefold() in lowered for marker in markers):
                family, mode, confidence = candidate, candidate_mode, 0.86
                break
        if family is IntentFamily.CONVERSATION and len(raw) > 220:
            mode = "deliberate"
            confidence = 0.55
        if family is IntentFamily.RESEARCH:
            mode = "research"
        inputs = [self._input_descriptor(item) for item in (attachments or [])]
        ambiguities: list[str] = []
        if family in {IntentFamily.INSTALL, IntentFamily.CONFIGURE} and not self._has_subject(raw):
            ambiguities.append("application is not explicit")
        if family in {IntentFamily.EXPLAIN, IntentFamily.TEACH, IntentFamily.SOLVE} and not self._has_subject(raw):
            ambiguities.append("topic or task is not explicit")
        risk = "medium" if family in {IntentFamily.INSTALL, IntentFamily.CONFIGURE, IntentFamily.CREATE} else "low"
        return TaskContract(
            intent_family=family.value,
            subject=self._subject(raw, family),
            desired_outcome=raw,
            inputs=inputs,
            constraints=[str(value) for value in (constraints or []) if str(value).strip()],
            ambiguities=ambiguities,
            risk=risk,
            mode=mode,
            confidence=confidence,
        )

    @staticmethod
    def _has_subject(text: str) -> bool:
        return len(re.sub(r"[^\wА-Яа-яЁё]+", "", text, flags=re.UNICODE)) >= 6

    @staticmethod
    def _subject(text: str, family: IntentFamily) -> str:
        value = text
        for prefix in ("объясни", "расскажи", "установи", "установить", "настрой", "реши", "найди", "создай"):
            if value.casefold().startswith(prefix):
                value = value[len(prefix):].strip(" :,-—")
                break
        return value[:240] or family.value

    @staticmethod
    def _input_descriptor(value: str | Path) -> dict[str, Any]:
        path = Path(value)
        suffix = path.suffix.casefold()
        kind = "file"
        if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
            kind = "image"
        elif suffix in {".mp4", ".mkv", ".mov", ".webm", ".avi"}:
            kind = "video"
        elif suffix in {".pdf", ".docx", ".xlsx", ".pptx"}:
            kind = "document"
        return {"path": str(path), "kind": kind, "suffix": suffix, "exists": path.is_file()}

    @staticmethod
    def is_fast_contract(contract: TaskContract) -> bool:
        return contract.mode == "conversation" and contract.intent_family in {"conversation", "operate"}
