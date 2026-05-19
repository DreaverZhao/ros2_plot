from __future__ import annotations

import argparse
from pathlib import Path

from .bag import read_bag
from .config import apply_overrides, load_config
from .plotting import render


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot ROS 2 bag topics from a YAML config.")
    parser.add_argument("config", help="YAML plot config")
    parser.add_argument("--bag", help="Override the bag path from the config")
    parser.add_argument("--start", type=float, help="Override the start time in seconds")
    parser.add_argument("--end", type=float, help="Override the end time in seconds")
    parser.add_argument("--save", help="Override output image path")
    parser.add_argument("--no-show", action="store_true", help="Do not open an interactive plot window")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = load_config(Path(args.config))
    apply_overrides(config, args)

    data = read_bag(config)
    render(config, data)
    return 0
