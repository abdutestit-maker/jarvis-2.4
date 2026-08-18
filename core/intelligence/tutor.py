"""Local teaching contracts and a deterministic tutoring scaffold."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable


class TutorMode(str, Enum):
    SOCRATIC = "socratic"
    DIRECT = "direct"
    HINT = "hint"
    CHECK = "check"


@dataclass
class TutorResult:
    topic: str
    mode: str
    explanation: str
    steps: list[str] = field(default_factory=list)
    hint: str = ""
    check_questions: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    needs_input: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TeachingSession:
    topic: str
    level: str = "adaptive"
    mode: TutorMode = TutorMode.SOCRATIC
    attempts: int = 0
    completed_checks: int = 0
    mistakes: list[str] = field(default_factory=list)
    last_result: TutorResult | None = None

    def record(self, result: TutorResult) -> None:
        self.attempts += 1
        self.last_result = result


class TutorEngine:
    """Builds bounded teaching scaffolds without adding an LLM model."""

    def __init__(self, *, generator: Callable[[str, str, TutorMode], str] | None = None) -> None:
        self.generator = generator

    def teach(self, topic: str, *, level: str = "adaptive", mode: TutorMode | str = TutorMode.SOCRATIC,
              source: str = "user", session: TeachingSession | None = None) -> TutorResult:
        selected = mode if isinstance(mode, TutorMode) else TutorMode(str(mode))
        clean_topic = " ".join(str(topic or "").split())[:240]
        explanation = self.generator(clean_topic, level, selected) if self.generator else self._fallback(clean_topic, selected)
        result = TutorResult(
            topic=clean_topic,
            mode=selected.value,
            explanation=explanation,
            steps=["выделить ключевое понятие", "связать его с примером", "проверить понимание"],
            hint="Сформулируйте своими словами, что изменилось бы в простом примере.",
            check_questions=[f"Как бы вы объяснили «{clean_topic}» одним предложением?"],
            assumptions=[f"уровень пользователя: {level}"],
            evidence=[{"source": source, "type": "request", "freshness": "fresh"}],
            confidence=0.72 if clean_topic else 0.0,
            needs_input=not bool(clean_topic),
        )
        if session is not None:
            session.record(result)
        return result

    def check(self, session: TeachingSession, answer: str) -> dict[str, Any]:
        text = " ".join(str(answer or "").split())
        passed = bool(text) and len(text) >= 8
        if passed:
            session.completed_checks += 1
        else:
            session.mistakes.append("ответ слишком короткий для проверки")
        return {"passed": passed, "feedback": "Проверка пройдена — теперь примените идею к новому примеру." if passed else "Дайте чуть более развёрнутый ответ, чтобы я проверил рассуждение.", "completed_checks": session.completed_checks}

    @staticmethod
    def _fallback(topic: str, mode: TutorMode) -> str:
        if not topic:
            return "Назовите тему или приложите задачу — разберём её по шагам."
        if mode is TutorMode.HINT:
            return f"Начните с определения «{topic}» и выпишите, что уже известно."
        if mode is TutorMode.CHECK:
            return f"Покажите своё решение по теме «{topic}» — я проверю каждый шаг."
        if mode is TutorMode.DIRECT:
            return f"Разберём «{topic}»: сначала определим понятие, затем применим его к короткому примеру."
        return f"Разберём «{topic}» простыми шагами: сначала смысл, затем пример, затем самостоятельная проверка."
