from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TransformCall:
    name: str
    kwargs: dict[str, Any] = field(default_factory=dict)


@dataclass
class SeriesConfig:
    key: str
    topic: str
    field_path: str | None = None
    function_name: str | None = None
    kwargs: dict[str, Any] = field(default_factory=dict)
    transforms: list[TransformCall] = field(default_factory=list)
    label: str | None = None
    use_default_label: bool = True
    style: dict[str, Any] = field(default_factory=dict)
    scale: float = 1.0
    offset: float = 0.0

    def default_label(self) -> str:
        if self.field_path:
            return f"{self.topic}.{self.field_path}"
        return f"{self.topic}.{self.function_name}"


@dataclass
class PlotConfig:
    title: str | None
    series: list[SeriesConfig]
    title_loc: str = "center"
    x_label: str | None = "time [s]"
    x_label_loc: str = "center"
    y_label: str | None = None
    y_label_side: str = "left"
    y_label_loc: str = "center"


@dataclass
class AppConfig:
    bag: str
    storage_id: str = "sqlite3"
    time_mode: str = "relative"
    start: float | None = None
    end: float | None = None
    aliases: dict[str, str] = field(default_factory=dict)
    styles: dict[str, dict[str, Any]] = field(default_factory=dict)
    plots: list[PlotConfig] = field(default_factory=list)
    save: str | None = None
    show: bool = True
    dpi: int = 140
