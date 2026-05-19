from __future__ import annotations

import math
from typing import Any


def resolve_field(message: Any, field_path: str) -> Any:
    value = message
    for part in field_path.split("."):
        value = resolve_part(value, part)
    return value


def resolve_part(value: Any, part: str) -> Any:
    name, indexes = split_indexes(part)
    if name:
        if isinstance(value, dict):
            value = value[name]
        else:
            value = getattr(value, name)
    for index in indexes:
        value = value[index]
    return value


def split_indexes(part: str) -> tuple[str, list[int]]:
    name = part.split("[", 1)[0]
    indexes: list[int] = []
    rest = part[len(name):]
    while rest:
        if not rest.startswith("[") or "]" not in rest:
            raise ValueError(f"invalid indexed field part: {part}")
        index_text, rest = rest[1:].split("]", 1)
        indexes.append(int(index_text))
    return name, indexes


def numeric_value(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"value is not numeric: {value!r}")
    if not math.isfinite(float(value)):
        raise ValueError(f"value is not finite: {value!r}")
    return float(value)
