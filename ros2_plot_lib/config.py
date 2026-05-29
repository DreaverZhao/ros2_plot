from __future__ import annotations

import argparse
import inspect
from pathlib import Path
from typing import Any

from .models import AppConfig, PlotConfig, SeriesConfig, TransformCall
from .transforms import get_transform


def load_config(path: Path) -> AppConfig:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("Missing dependency: install PyYAML, for example `python3 -m pip install PyYAML`.") from exc

    raw = yaml.safe_load(path.read_text()) or {}
    if not isinstance(raw, dict):
        raise SystemExit("Config root must be a YAML mapping.")

    aliases = raw.get("aliases") or {}
    styles = raw.get("styles") or {}
    time_cfg = raw.get("time") or {}
    output_cfg = raw.get("output") or {}
    plot_defaults = raw.get("plot_defaults") or {}
    if not isinstance(plot_defaults, dict):
        raise SystemExit("`plot_defaults` must be a mapping.")

    bag = raw.get("bag")
    if not bag:
        raise SystemExit("Config must include `bag`.")

    plots = [
        parse_plot(plot_raw, aliases, styles, index, plot_defaults)
        for index, plot_raw in enumerate(raw.get("plots") or [], start=1)
    ]
    if not plots:
        raise SystemExit("Config must include at least one plot in `plots`.")

    return AppConfig(
        bag=str(bag),
        storage_id=str(raw.get("storage_id", "sqlite3")),
        time_mode=str(time_cfg.get("mode", "relative")),
        start=optional_float(time_cfg.get("start")),
        end=optional_float(time_cfg.get("end")),
        aliases=dict(aliases),
        styles=dict(styles),
        plots=plots,
        save=optional_str(output_cfg.get("save")),
        show=bool(output_cfg.get("show", True)),
        dpi=int(output_cfg.get("dpi", 140)),
    )


def apply_overrides(config: AppConfig, args: argparse.Namespace) -> None:
    if args.bag:
        config.bag = args.bag
    if args.start is not None:
        config.start = args.start
    if args.end is not None:
        config.end = args.end
    if args.save:
        config.save = args.save
    if args.no_show:
        config.show = False


def parse_plot(
    raw: dict[str, Any],
    aliases: dict[str, str],
    styles: dict[str, dict[str, Any]],
    index: int,
    defaults: dict[str, Any] | None = None,
) -> PlotConfig:
    if not isinstance(raw, dict):
        raise SystemExit(f"Plot #{index} must be a mapping.")

    merged = dict(defaults or {})
    merged.update(raw)
    raw_series = raw.get("series", raw.get("topics"))
    if not raw_series:
        raise SystemExit(f"Plot #{index} must include `series`.")

    series = [
        parse_series(series_raw, aliases, styles, index, series_index)
        for series_index, series_raw in enumerate(raw_series, start=1)
    ]
    return PlotConfig(
        title=optional_label_text(merged, "title"),
        title_loc=parse_loc(
            merged.get("title_loc", "center"),
            {"left", "center", "right"},
            f"Plot #{index} `title_loc`",
        ),
        title_size=optional_positive_float(merged.get("title_size"), f"Plot #{index} `title_size`"),
        series=series,
        x_label=parse_axis_label(merged, "x_label", "time [s]"),
        x_label_loc=parse_loc(
            merged.get("x_label_loc", "center"),
            {"left", "center", "right"},
            f"Plot #{index} `x_label_loc`",
        ),
        x_label_size=optional_positive_float(merged.get("x_label_size"), f"Plot #{index} `x_label_size`"),
        y_label=optional_label_text(merged, "y_label"),
        y_label_side=parse_loc(
            merged.get("y_label_side", "left"),
            {"left", "right"},
            f"Plot #{index} `y_label_side`",
        ),
        y_label_loc=parse_loc(
            merged.get("y_label_loc", "center"),
            {"bottom", "center", "top"},
            f"Plot #{index} `y_label_loc`",
        ),
        y_label_size=optional_positive_float(merged.get("y_label_size"), f"Plot #{index} `y_label_size`"),
        tick_label_size=optional_positive_float(
            merged.get("tick_label_size"),
            f"Plot #{index} `tick_label_size`",
        ),
        text_font=optional_str(merged.get("text_font")),
        font_size=optional_positive_float(merged.get("font_size"), f"Plot #{index} `font_size`"),
        legend_font=optional_str(merged.get("legend_font")),
        legend_size=optional_positive_float(merged.get("legend_size"), f"Plot #{index} `legend_size`"),
        legend_loc=parse_legend_loc(merged.get("legend_loc"), f"Plot #{index} `legend_loc`"),
        grid_linewidth=positive_float(merged.get("grid_linewidth", 0.8), f"Plot #{index} `grid_linewidth`"),
        grid_alpha=parse_alpha(merged.get("grid_alpha", 0.25), f"Plot #{index} `grid_alpha`"),
    )


def parse_series(
    raw: dict[str, Any],
    aliases: dict[str, str],
    styles: dict[str, dict[str, Any]],
    plot_index: int,
    series_index: int,
) -> SeriesConfig:
    if not isinstance(raw, dict):
        raise SystemExit(f"Plot #{plot_index} series #{series_index} must be a mapping.")

    topic_or_alias = raw.get("topic", raw.get("name"))
    if not topic_or_alias:
        raise SystemExit(f"Plot #{plot_index} series #{series_index} must include `topic`.")

    topic = aliases.get(str(topic_or_alias), str(topic_or_alias))
    field_path = optional_str(raw.get("field"))
    function_name = optional_str(raw.get("function"))
    if bool(field_path) == bool(function_name):
        raise SystemExit(
            f"Plot #{plot_index} series #{series_index} must include exactly one of `field` or `function`."
        )

    kwargs = parse_kwargs(raw.get("kwargs"), plot_index, series_index) if function_name else {}
    if function_name:
        validate_transform_signature(function_name, kwargs, plot_index, series_index, context="function")
        validate_transform_mode(function_name, "message", plot_index, series_index, context="function")
    transforms = parse_transform_calls(raw.get("transforms"), plot_index, series_index)
    label, use_default_label = parse_series_label(raw)

    return SeriesConfig(
        key=f"plot{plot_index}_series{series_index}",
        topic=topic,
        field_path=field_path,
        function_name=function_name,
        kwargs=kwargs,
        transforms=transforms,
        label=label,
        use_default_label=use_default_label,
        style=resolve_style(raw.get("style"), styles),
        scale=float(raw.get("scale", 1.0)),
        offset=float(raw.get("offset", 0.0)),
    )


def parse_kwargs(raw_kwargs: Any, plot_index: int, series_index: int) -> dict[str, Any]:
    if raw_kwargs is None:
        return {}
    if not isinstance(raw_kwargs, dict):
        raise SystemExit(f"Plot #{plot_index} series #{series_index} `kwargs` must be a mapping.")
    return {str(name): value for name, value in raw_kwargs.items()}


def validate_transform_signature(
    function_name: str,
    kwargs: dict[str, Any],
    plot_index: int,
    series_index: int,
    context: str,
) -> None:
    transform = get_transform(function_name)
    signature = inspect.signature(transform.func)
    try:
        signature.bind(object(), **kwargs)
    except TypeError as exc:
        raise SystemExit(
            f"Plot #{plot_index} series #{series_index} has an invalid {context} call for `{function_name}`: {exc}"
        ) from exc


def validate_transform_mode(
    function_name: str,
    expected_input: str,
    plot_index: int,
    series_index: int,
    context: str,
) -> None:
    transform = get_transform(function_name)
    if transform.input_name != expected_input:
        raise SystemExit(
            f"Plot #{plot_index} series #{series_index} `{context}` `{function_name}` expects "
            f"`{transform.input_name}` input, not `{expected_input}`."
        )


def parse_transform_calls(raw_transforms: Any, plot_index: int, series_index: int) -> list[TransformCall]:
    if raw_transforms is None:
        return []
    if not isinstance(raw_transforms, list):
        raise SystemExit(f"Plot #{plot_index} series #{series_index} `transforms` must be a list.")

    transforms: list[TransformCall] = []
    for transform_index, raw_transform in enumerate(raw_transforms, start=1):
        if not isinstance(raw_transform, dict):
            raise SystemExit(
                f"Plot #{plot_index} series #{series_index} transform #{transform_index} must be a mapping."
            )
        name = optional_str(raw_transform.get("name"))
        if not name:
            raise SystemExit(
                f"Plot #{plot_index} series #{series_index} transform #{transform_index} must include `name`."
            )
        kwargs = parse_kwargs(raw_transform.get("kwargs"), plot_index, series_index)
        validate_transform_signature(name, kwargs, plot_index, series_index, context="transform")
        validate_transform_mode(name, "value", plot_index, series_index, context="transform")
        transforms.append(TransformCall(name=name, kwargs=kwargs))
    return transforms


def parse_axis_label(raw: dict[str, Any], key: str, default: str | None) -> str | None:
    if key not in raw:
        return default
    return optional_label_text(raw, key)


def optional_label_text(raw: dict[str, Any], key: str) -> str | None:
    value = raw.get(key)
    if value is None or value is False:
        return None
    if not isinstance(value, str):
        raise SystemExit(f"`{key}` must be a string, null, or false.")
    text = value.strip()
    return text or None


def parse_series_label(raw: dict[str, Any]) -> tuple[str | None, bool]:
    if "label" not in raw:
        return None, True

    label = optional_label_text(raw, "label")
    return label, False


def parse_loc(value: Any, allowed: set[str], context: str) -> str:
    if not isinstance(value, str):
        raise SystemExit(f"{context} must be one of: {', '.join(sorted(allowed))}.")
    normalized = value.strip().lower()
    if normalized not in allowed:
        raise SystemExit(f"{context} must be one of: {', '.join(sorted(allowed))}.")
    return normalized


def resolve_style(raw_style: Any, styles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if raw_style is None:
        return {}
    if isinstance(raw_style, str):
        return dict(styles.get(raw_style, {}))
    if isinstance(raw_style, dict):
        style: dict[str, Any] = {}
        base_name = raw_style.get("use")
        if base_name:
            style.update(styles.get(str(base_name), {}))
        style.update({key: value for key, value in raw_style.items() if key != "use"})
        return style
    raise SystemExit("Series `style` must be either a style name or a mapping.")


def optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def optional_positive_float(value: Any, context: str) -> float | None:
    if value is None:
        return None
    return positive_float(value, context)


def positive_float(value: Any, context: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"{context} must be a positive number.") from exc
    if number <= 0:
        raise SystemExit(f"{context} must be a positive number.")
    return number


def parse_alpha(value: Any, context: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"{context} must be a number between 0 and 1.") from exc
    if number < 0 or number > 1:
        raise SystemExit(f"{context} must be a number between 0 and 1.")
    return number


def parse_legend_loc(value: Any, context: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise SystemExit(f"{context} must be a string.")
    normalized = value.strip().lower()
    allowed = {
        "best",
        "upper right",
        "upper left",
        "lower left",
        "lower right",
        "right",
        "center left",
        "center right",
        "lower center",
        "upper center",
        "center",
    }
    if normalized not in allowed:
        raise SystemExit(f"{context} must be one of: {', '.join(sorted(allowed))}.")
    return normalized
