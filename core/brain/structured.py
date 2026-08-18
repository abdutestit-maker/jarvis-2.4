"""Typed JSON output validation; malformed text stays inert."""
from __future__ import annotations

import dataclasses
import json
from collections.abc import Callable
from typing import Any, TypeVar, get_args, get_origin


class StructuredOutputError(ValueError):
    pass


T = TypeVar("T")


def _matches(value: Any, annotation: Any) -> bool:
    if annotation is Any:
        return True
    origin = get_origin(annotation)
    if origin is None:
        if annotation is float:
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        return isinstance(value, annotation) if isinstance(annotation, type) else True
    if origin in (list, tuple):
        args = get_args(annotation)
        return isinstance(value, origin) and (not args or all(_matches(item, args[0]) for item in value))
    return True


class StructuredOutputValidator:
    def __init__(self, *, max_repairs: int = 2) -> None:
        self.max_repairs = max(0, min(3, int(max_repairs)))

    def validate(self, raw: str, schema: type[T], *,
                 repair: Callable[[str, str], str] | None = None) -> T:
        current = raw
        for attempt in range(self.max_repairs + 1):
            try:
                value = json.loads(current)
                return self._coerce(value, schema)
            except (json.JSONDecodeError, StructuredOutputError, TypeError, ValueError) as exc:
                if repair is None or attempt >= self.max_repairs:
                    raise StructuredOutputError(str(exc)) from exc
                current = repair(current, str(exc))
        raise StructuredOutputError("repair budget exhausted")

    @staticmethod
    def _coerce(value: Any, schema: type[T]) -> T:
        if schema is dict:
            if not isinstance(value, dict):
                raise StructuredOutputError("expected JSON object")
            return value  # type: ignore[return-value]
        if dataclasses.is_dataclass(schema):
            if not isinstance(value, dict):
                raise StructuredOutputError("expected JSON object")
            fields = {field.name: field for field in dataclasses.fields(schema)}
            missing = [name for name, field in fields.items()
                       if name not in value and field.default is dataclasses.MISSING
                       and field.default_factory is dataclasses.MISSING]
            unknown = sorted(set(value) - set(fields))
            if missing:
                raise StructuredOutputError(f"missing fields: {', '.join(missing)}")
            if unknown:
                raise StructuredOutputError(f"unknown fields: {', '.join(unknown)}")
            for name, item in value.items():
                if not _matches(item, fields[name].type):
                    raise StructuredOutputError(f"invalid type for {name}")
            return schema(**value)  # type: ignore[return-value]
        model_validate = getattr(schema, "model_validate", None)
        if callable(model_validate):
            return model_validate(value)
        if not isinstance(value, schema):
            raise StructuredOutputError(f"expected {schema.__name__}")
        return value


__all__ = ["StructuredOutputValidator", "StructuredOutputError"]

