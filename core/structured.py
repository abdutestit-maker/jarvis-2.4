"""Structured Output — надёжный разбор решений модели (§13).

Агентные решения J.A.R.V.I.S. принимает в виде структурированного JSON:

    {
      "goal": "...",
      "intent": "...",
      "plan": [...],
      "selected_tool": "...",
      "arguments": {...},
      "risk": "low",
      "verification": "..."
    }

Локальная 4B-модель регулярно нарушает формат: заворачивает JSON в
markdown, добавляет пояснения, ставит одинарные кавычки, забывает
закрывающую скобку, пишет `True` вместо `true`.

ЗАПРЕЩЕНО (§13) просто падать на плохом JSON. Порядок действий:

    RAW -> EXTRACT -> REPAIR -> PARSE -> VALIDATE -> (retry с моделью)

Модуль детерминированный, без обращения к LLM: он чинит то, что можно
починить механически, и честно возвращает ошибку, если нельзя — тогда
вызывающий (agent) делает повторный запрос к модели с текстом ошибки.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from core.utils.logger import get_logger

__all__ = [
    "ParseResult",
    "extract_json",
    "parse_structured",
    "validate_tool_call",
    "ToolCallDecision",
    "PLAN_SCHEMA_HINT",
]

log = get_logger(__name__)


@dataclass
class ParseResult:
    """Итог разбора структурированного ответа модели."""

    ok: bool
    data: Optional[Dict[str, Any]] = None
    error: str = ""
    repaired: bool = False
    raw: str = ""

    def __bool__(self) -> bool:
        return self.ok


# --------------------------------------------------------------------------- #
#  Извлечение JSON из «грязного» текста модели
# --------------------------------------------------------------------------- #

_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.DOTALL)


def _balanced_object(text: str) -> Optional[str]:
    """Находит первый сбалансированный {...} с учётом строк и экранирования."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    escape = False
    quote = ""
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                in_str = False
            continue
        if ch in ('"', "'"):
            in_str = True
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    # Не закрыли скобки — вернём хвост, репейр попробует дозакрыть.
    return text[start:] if depth > 0 else None


def extract_json(raw: str) -> Optional[str]:
    """Достаёт кандидата JSON-объекта из произвольного ответа модели."""
    if not raw:
        return None
    text = raw.strip()

    # 1) markdown-забор ```json ... ```
    fence = _FENCE_RE.search(text)
    if fence:
        inner = fence.group(1).strip()
        candidate = _balanced_object(inner) or inner
        if candidate.strip().startswith("{"):
            return candidate

    # 2) первый сбалансированный объект в тексте
    return _balanced_object(text)


def _repair_json(candidate: str) -> str:
    """Механически чинит типичные болезни JSON от малых моделей."""
    s = candidate.strip()

    # Управляющие символы внутри строк -> пробел (llama любит \n в значениях).
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", s)

    # Python-литералы -> JSON.
    s = re.sub(r"\bTrue\b", "true", s)
    s = re.sub(r"\bFalse\b", "false", s)
    s = re.sub(r"\bNone\b", "null", s)

    # Комментарии // и /* */ (модель иногда «поясняет»).
    s = re.sub(r"//[^\n\"']*", "", s)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)

    # Одинарные кавычки у ключей/значений -> двойные (только если нет двойных).
    if '"' not in s and "'" in s:
        s = s.replace("'", '"')

    # Ключи без кавычек: {tool: "x"} -> {"tool": "x"}
    s = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)', r'\1"\2"\3', s)

    # Голые словесные значения: {"risk": low} -> {"risk": "low"}
    # (не трогаем true/false/null, числа, объекты, массивы и строки).
    def _quote_bare(match: "re.Match[str]") -> str:
        prefix, word, suffix = match.group(1), match.group(2), match.group(3)
        if word in ("true", "false", "null"):
            return match.group(0)
        return f'{prefix}"{word}"{suffix}'

    s = re.sub(r'(:\s*)([A-Za-z_][A-Za-z0-9_\-]*)(\s*[,}\]])', _quote_bare, s)

    # Висячие запятые перед закрывающей скобкой.
    s = re.sub(r",\s*([}\]])", r"\1", s)

    # Недостающие закрывающие скобки.
    opens = s.count("{") - s.count("}")
    if opens > 0:
        s += "}" * opens
    brackets = s.count("[") - s.count("]")
    if brackets > 0:
        s += "]" * brackets

    return s.strip()


def parse_structured(raw: str,
                     required_keys: Optional[List[str]] = None) -> ParseResult:
    """Разбирает структурированный ответ модели с механическим ремонтом (§13).

    Args:
        raw: сырой текст модели.
        required_keys: ключи, без которых результат считается невалидным.

    Returns:
        ``ParseResult``. При неудаче ``error`` содержит текст, пригодный для
        повторного запроса к модели ("верни JSON с ключами ...").
    """
    if not (raw or "").strip():
        return ParseResult(False, error="модель вернула пустой ответ", raw=raw or "")

    candidate = extract_json(raw)
    if candidate is None:
        return ParseResult(False, error="в ответе нет JSON-объекта", raw=raw)

    data: Optional[Dict[str, Any]] = None
    repaired = False
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as first_exc:
        fixed = _repair_json(candidate)
        try:
            data = json.loads(fixed)
            repaired = True
            log.debug("JSON отремонтирован механически (%s)", first_exc.msg)
        except json.JSONDecodeError as exc:
            return ParseResult(
                False,
                error=f"JSON невалиден даже после ремонта: {exc.msg} (позиция {exc.pos})",
                raw=raw,
            )

    if not isinstance(data, dict):
        return ParseResult(False, error=f"ожидался объект, получен {type(data).__name__}", raw=raw)

    if required_keys:
        missing = [k for k in required_keys if k not in data]
        if missing:
            return ParseResult(
                False,
                data=data,
                error=f"в JSON отсутствуют обязательные ключи: {missing}",
                repaired=repaired,
                raw=raw,
            )

    return ParseResult(True, data=data, repaired=repaired, raw=raw)


# --------------------------------------------------------------------------- #
#  Решение о вызове инструмента
# --------------------------------------------------------------------------- #

@dataclass
class ToolCallDecision:
    """Валидированное решение модели о вызове инструмента (§13)."""

    tool: Optional[str]
    arguments: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    risk: str = "low"
    verification: str = ""
    answer: str = ""              # если модель решила ответить текстом, без tool
    plan: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def needs_tool(self) -> bool:
        return bool(self.tool)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "arguments": self.arguments,
            "reason": self.reason,
            "risk": self.risk,
            "verification": self.verification,
            "answer": self.answer,
            "plan": self.plan,
        }


#: Подсказка формата для промптов (§13).
PLAN_SCHEMA_HINT = (
    '{"tool": "имя_инструмента или null", '
    '"arguments": {...}, '
    '"reason": "почему", '
    '"risk": "low|medium|high", '
    '"verification": "как проверить успех", '
    '"answer": "текст ответа, если инструмент не нужен"}'
)


def validate_tool_call(
    data: Dict[str, Any],
    known_tools: List[str],
    schema_lookup: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
) -> tuple[Optional[ToolCallDecision], str]:
    """Валидирует решение модели против реального реестра инструментов.

    Args:
        data: разобранный JSON.
        known_tools: имена доступных инструментов (после tool retrieval).
        schema_lookup: функция name -> input_schema для проверки аргументов.

    Returns:
        ``(decision, error)``. При ошибке ``decision is None`` и ``error``
        содержит текст, который можно вернуть модели для исправления.
    """
    tool = data.get("tool") or data.get("selected_tool") or data.get("name")
    if isinstance(tool, str):
        tool = tool.strip() or None
        if tool and tool.lower() in ("null", "none", "нет", "no_tool"):
            tool = None
    elif tool is not None:
        return None, f"поле 'tool' должно быть строкой или null, получено {type(tool).__name__}"

    args = data.get("arguments")
    if args is None:
        args = data.get("args") or {}
    if not isinstance(args, dict):
        return None, "поле 'arguments' должно быть объектом"

    plan = data.get("plan") or []
    if not isinstance(plan, list):
        plan = []

    decision = ToolCallDecision(
        tool=tool,
        arguments=args,
        reason=str(data.get("reason") or data.get("intent") or ""),
        risk=str(data.get("risk") or "low").lower(),
        verification=str(data.get("verification") or ""),
        answer=str(data.get("answer") or data.get("response") or ""),
        plan=[p for p in plan if isinstance(p, dict)],
    )

    if decision.tool is None:
        return decision, ""

    if decision.tool not in known_tools:
        return None, (
            f"инструмент '{decision.tool}' недоступен. "
            f"Доступные: {', '.join(known_tools) if known_tools else '(нет)'}"
        )

    # Проверка обязательных аргументов по реальной схеме инструмента.
    if schema_lookup is not None:
        schema = schema_lookup(decision.tool)
        if schema:
            required = schema.get("required") or []
            missing = [r for r in required if r not in decision.arguments]
            if missing:
                props = ", ".join((schema.get("properties") or {}).keys())
                return None, (
                    f"для '{decision.tool}' не заданы обязательные аргументы {missing}. "
                    f"Доступные аргументы: {props}"
                )

    return decision, ""
