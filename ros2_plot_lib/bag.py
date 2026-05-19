from __future__ import annotations

import inspect
from typing import Any

from .fields import numeric_value, resolve_field
from .models import AppConfig, SeriesConfig, TransformCall
from .transforms import get_transform


NSEC_PER_SEC = 1_000_000_000.0


def read_bag(config: AppConfig) -> dict[str, tuple[list[float], list[float]]]:
    try:
        import rosbag2_py
        from rclpy.serialization import deserialize_message
        from rosidl_runtime_py.utilities import get_message
    except ImportError as exc:
        raise SystemExit(
            "Missing ROS 2 Python modules. Source your ROS 2 environment first, "
            "for example `source /opt/ros/<distro>/setup.bash`."
        ) from exc

    series_by_topic = requested_series(config)
    requested_topics = set(series_by_topic)
    data = {series.key: ([], []) for series_list in series_by_topic.values() for series in series_list}

    reader = rosbag2_py.SequentialReader()
    storage_options = rosbag2_py.StorageOptions(uri=config.bag, storage_id=config.storage_id)
    converter_options = rosbag2_py.ConverterOptions(
        input_serialization_format="cdr",
        output_serialization_format="cdr",
    )
    reader.open(storage_options, converter_options)

    topic_type_map = {topic.name: topic.type for topic in reader.get_all_topics_and_types()}
    missing_topics = sorted(requested_topics.difference(topic_type_map))
    if missing_topics:
        raise SystemExit("Topics not found in bag: " + ", ".join(missing_topics))

    message_types = {topic: get_message(topic_type_map[topic]) for topic in requested_topics}
    validate_series_against_topics(series_by_topic, message_types)

    bag_start_ns: int | None = None
    while reader.has_next():
        topic, raw_data, timestamp_ns = reader.read_next()
        if bag_start_ns is None:
            bag_start_ns = timestamp_ns

        topic_series = series_by_topic.get(topic)
        if not topic_series:
            continue

        x_value = time_value(timestamp_ns, bag_start_ns, config.time_mode)
        if config.start is not None and x_value < config.start:
            continue
        if config.end is not None and x_value > config.end:
            continue

        message = deserialize_message(raw_data, message_types[topic])
        field_cache: dict[str, float] = {}
        for series in topic_series:
            y_value = evaluate_series(message, series, field_cache)
            xs, ys = data[series.key]
            xs.append(x_value)
            ys.append(y_value)

    return data


def requested_series(config: AppConfig) -> dict[str, list[SeriesConfig]]:
    requested: dict[str, list[SeriesConfig]] = {}
    for plot in config.plots:
        for series in plot.series:
            requested.setdefault(series.topic, []).append(series)
    return requested


def evaluate_series(message: Any, series: SeriesConfig, field_cache: dict[str, float]) -> float:
    try:
        if series.field_path:
            value = resolve_numeric_field(message, series.field_path, field_cache)
        else:
            transform = get_transform(series.function_name or "")
            value = numeric_value(transform.func(message, **series.kwargs))

        for transform_call in series.transforms:
            value = apply_transform(value, transform_call)
        return value
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
        raise SystemExit(f"Could not read series `{series.default_label()}`: {exc}") from exc


def resolve_numeric_field(message: Any, field_path: str, field_cache: dict[str, float]) -> float:
    cached_value = field_cache.get(field_path)
    if cached_value is not None:
        return cached_value

    value = numeric_value(resolve_field(message, field_path))
    field_cache[field_path] = value
    return value


def validate_series_against_topics(
    series_by_topic: dict[str, list[SeriesConfig]],
    message_types: dict[str, Any],
) -> None:
    for topic, series_list in series_by_topic.items():
        sample_message = message_types[topic]()
        for series in series_list:
            validate_series_against_message(series, sample_message)


def validate_series_against_message(series: SeriesConfig, sample_message: Any) -> None:
    try:
        if series.field_path:
            value = resolve_numeric_field(sample_message, series.field_path, {})
        else:
            transform = get_transform(series.function_name or "")
            signature = inspect.signature(transform.func)
            signature.bind(sample_message, **series.kwargs)
            value = numeric_value(transform.func(sample_message, **series.kwargs))

        for transform_call in series.transforms:
            value = apply_transform(value, transform_call)
        numeric_value(value)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
        raise SystemExit(
            f"Warning: series `{series.default_label()}` does not fit topic `{series.topic}`: {exc}"
        ) from exc


def apply_transform(value: float, transform_call: TransformCall) -> float:
    transform = get_transform(transform_call.name)
    signature = inspect.signature(transform.func)
    signature.bind(value, **transform_call.kwargs)
    return numeric_value(transform.func(value, **transform_call.kwargs))


def time_value(timestamp_ns: int, bag_start_ns: int, mode: str) -> float:
    if mode == "relative":
        return (timestamp_ns - bag_start_ns) / NSEC_PER_SEC
    if mode in {"bag", "unix"}:
        return timestamp_ns / NSEC_PER_SEC
    raise SystemExit("time.mode must be one of: relative, bag, unix.")
