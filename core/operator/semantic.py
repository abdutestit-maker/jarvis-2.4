"""Pure semantic UI models shared by UIA discovery and learned selectors."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Iterator


def _normal(value: object) -> str:
    return " ".join(str(value or "").casefold().split())


_ROLE_TYPES = {
    "button": "button",
    "checkbox": "checkbox",
    "combobox": "combobox",
    "dialog": "window",
    "dropdown": "combobox",
    "input": "edit",
    "menu": "menuitem",
    "radio": "radiobutton",
    "tab": "tabitem",
    "toggle": "checkbox",
}


@dataclass(frozen=True)
class SemanticSelector:
    """Resilient selector; coordinates are intentionally not part of the API."""

    automation_id: str = ""
    control_type: str = ""
    name: str = ""
    role: str = ""
    class_name: str = ""
    hierarchy: tuple[str, ...] = ()

    @classmethod
    def from_value(cls, value: "SemanticSelector | dict[str, Any]") -> "SemanticSelector":
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            raise TypeError("selector must be SemanticSelector or dict")
        allowed = {key: value.get(key, ()) if key == "hierarchy" else value.get(key, "")
                   for key in cls.__dataclass_fields__}
        allowed["hierarchy"] = tuple(allowed["hierarchy"] or ())
        return cls(**allowed)


@dataclass
class SemanticControl:
    name: str
    control_type: str
    automation_id: str = ""
    class_name: str = ""
    enabled: bool = True
    visible: bool = True
    value: Any = None
    process_id: int | None = None
    native_handle: int | None = None
    hierarchy: tuple[str, ...] = ()
    children: list["SemanticControl"] = field(default_factory=list)

    @property
    def semantic_selector(self) -> dict[str, str]:
        result: dict[str, str] = {}
        if self.automation_id:
            result["automation_id"] = self.automation_id
        if self.control_type:
            result["control_type"] = self.control_type
        if self.name:
            result["name"] = self.name
        if self.class_name and not result:
            result["class_name"] = self.class_name
        return result

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["hierarchy"] = list(self.hierarchy)
        data["semantic_selector"] = self.semantic_selector
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SemanticControl":
        payload = {key: data.get(key) for key in cls.__dataclass_fields__ if key in data}
        payload["hierarchy"] = tuple(payload.get("hierarchy") or ())
        payload["children"] = [cls.from_dict(child) for child in data.get("children", [])]
        return cls(**payload)

    def walk(self) -> Iterator["SemanticControl"]:
        yield self
        for child in self.children:
            yield from child.walk()

    def find_best(self, selector: SemanticSelector | dict[str, Any]) -> "SemanticControl | None":
        query = SemanticSelector.from_value(selector)
        scored = [(self._score(item, query), index, item)
                  for index, item in enumerate(self.walk())]
        score, _index, item = max(scored, default=(0, 0, None), key=lambda row: (row[0], -row[1]))
        return item if score > 0 else None

    @staticmethod
    def _score(item: "SemanticControl", query: SemanticSelector) -> int:
        score = 0
        if query.automation_id and _normal(item.automation_id) == _normal(query.automation_id):
            score += 120
        wanted_type = query.control_type or _ROLE_TYPES.get(_normal(query.role), "")
        if wanted_type and _normal(item.control_type) == _normal(wanted_type):
            score += 40
        if query.name:
            expected, actual = _normal(query.name), _normal(item.name)
            if actual == expected:
                score += 70
            elif expected and (expected in actual or actual in expected):
                score += 35
        if query.class_name and _normal(item.class_name) == _normal(query.class_name):
            score += 20
        if query.hierarchy:
            actual_path = tuple(_normal(part) for part in item.hierarchy)
            expected_path = tuple(_normal(part) for part in query.hierarchy)
            if actual_path[-len(expected_path):] == expected_path:
                score += 25
        return score


def flatten_controls(tree: SemanticControl | Iterable[SemanticControl]) -> list[SemanticControl]:
    roots = [tree] if isinstance(tree, SemanticControl) else list(tree)
    return [item for root in roots for item in root.walk()]

