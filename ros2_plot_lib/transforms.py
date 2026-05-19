from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .fields import numeric_value, resolve_field


Transform = Callable[..., float]


@dataclass(frozen=True)
class TransformSpec:
    func: Transform
    input_name: str


def quat_roll(message: Any, field: str = "orientation") -> float:
    x, y, z, w = quat_components(message, field)
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    return math.atan2(sinr_cosp, cosr_cosp)


def quat_pitch(message: Any, field: str = "orientation") -> float:
    x, y, z, w = quat_components(message, field)
    sinp = 2.0 * (w * y - z * x)
    if abs(sinp) >= 1.0:
        return math.copysign(math.pi / 2.0, sinp)
    return math.asin(sinp)


def quat_yaw(message: Any, field: str = "orientation") -> float:
    x, y, z, w = quat_components(message, field)
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


def quat_components(message: Any, field: str) -> tuple[float, float, float, float]:
    quaternion = resolve_field(message, field)
    return (
        float(getattr(quaternion, "x")),
        float(getattr(quaternion, "y")),
        float(getattr(quaternion, "z")),
        float(getattr(quaternion, "w")),
    )


def scale(message: Any, field: str, factor: float) -> float:
    return numeric_value(resolve_field(message, field)) * factor


def offset(message: Any, field: str, amount: float) -> float:
    return numeric_value(resolve_field(message, field)) + amount


def scale_value(value: float, factor: float) -> float:
    return numeric_value(value) * factor


def offset_value(value: float, amount: float) -> float:
    return numeric_value(value) + amount


def abs_value(value: float) -> float:
    return abs(numeric_value(value))


def rad_to_deg(value: float) -> float:
    return math.degrees(numeric_value(value))


DEFAULT_TRANSFORMS: dict[str, TransformSpec] = {
    "quat_roll": TransformSpec(quat_roll, "message"),
    "quat_pitch": TransformSpec(quat_pitch, "message"),
    "quat_yaw": TransformSpec(quat_yaw, "message"),
    "scale": TransformSpec(scale, "message"),
    "offset": TransformSpec(offset, "message"),
    "scale_value": TransformSpec(scale_value, "value"),
    "offset_value": TransformSpec(offset_value, "value"),
    "abs": TransformSpec(abs_value, "value"),
    "rad_to_deg": TransformSpec(rad_to_deg, "value"),
}


def get_transform(name: str) -> TransformSpec:
    try:
        return DEFAULT_TRANSFORMS[name]
    except KeyError as exc:
        available = ", ".join(sorted(DEFAULT_TRANSFORMS))
        raise SystemExit(f"Unknown function `{name}`. Available functions: {available}.") from exc
