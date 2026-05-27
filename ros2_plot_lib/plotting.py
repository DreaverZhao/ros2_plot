from __future__ import annotations

from .models import AppConfig


def render(config: AppConfig, data: dict[str, tuple[list[float], list[float]]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: install matplotlib, for example `python3 -m pip install matplotlib`."
        ) from exc

    for plot in config.plots:
        math_font = plot.legend_font or plot.text_font
        if math_font:
            configure_math_font(plt, math_font)
            break

    fig, axes = plt.subplots(
        len(config.plots),
        1,
        sharex=True,
        squeeze=False,
        figsize=(10, max(3, 3 * len(config.plots))),
    )

    for axis, plot in zip(axes[:, 0], config.plots):
        font_properties = resolve_font_properties(plot.text_font) if plot.text_font else None
        legend_font = plot.legend_font or plot.text_font
        legend_font_properties = resolve_font_properties(legend_font) if legend_font else None
        title_size = plot.title_size or plot.font_size
        x_label_size = plot.x_label_size or plot.font_size
        y_label_size = plot.y_label_size or plot.font_size
        tick_label_size = plot.tick_label_size or plot.font_size
        legend_size = plot.legend_size or plot.font_size

        has_visible_labels = False
        for series in plot.series:
            xs, ys = data[series.key]
            transformed = [value * series.scale + series.offset for value in ys]
            label = render_label(series)
            if label is None:
                axis.plot(xs, transformed, **series.style)
                continue

            has_visible_labels = True
            axis.plot(xs, transformed, label=label, **series.style)
        if font_properties:
            axis.title.set_fontproperties(font_properties)
            axis.xaxis.label.set_fontproperties(font_properties)
            axis.yaxis.label.set_fontproperties(font_properties)
            plt.setp(axis.get_xticklabels(), fontproperties=font_properties)
            plt.setp(axis.get_yticklabels(), fontproperties=font_properties)
        if plot.title:
            axis.set_title(plot.title, loc=plot.title_loc, fontsize=title_size)
        if plot.y_label:
            axis.yaxis.set_label_position(plot.y_label_side)
            axis.set_ylabel(plot.y_label, loc=plot.y_label_loc, fontsize=y_label_size)
        if plot.x_label and axis is axes[-1, 0]:
            axis.set_xlabel(plot.x_label, loc=plot.x_label_loc, fontsize=x_label_size)
        if tick_label_size is not None:
            axis.tick_params(axis="both", labelsize=tick_label_size)
        axis.grid(True, alpha=plot.grid_alpha, linewidth=plot.grid_linewidth)
        if has_visible_labels:
            if legend_font_properties:
                if legend_size is not None:
                    legend_font_properties.set_size(legend_size)
                axis.legend(prop=legend_font_properties)
            else:
                axis.legend(fontsize=legend_size)

    fig.tight_layout()

    if config.save:
        fig.savefig(config.save, dpi=config.dpi)
        print(f"Saved plot to {config.save}")
    if config.show:
        plt.show()


def render_label(series) -> str | None:
    if series.use_default_label:
        return series.label or series.default_label()
    return series.label


def resolve_font_properties(font_name: str):
    from matplotlib import font_manager

    try:
        resolved_path = font_manager.findfont(
            font_manager.FontProperties(family=[font_name]),
            fallback_to_default=False,
        )
    except Exception:
        resolved_path = None

    if resolved_path:
        font_properties = usable_font_properties(font_manager, resolved_path)
        if font_properties:
            return font_properties

    for font_path in find_system_font_paths(font_manager):
        if font_path != resolved_path and font_path_matches_name(font_manager, font_path, font_name):
            font_properties = usable_font_properties(font_manager, font_path)
            if font_properties:
                return font_properties

    print(f"Warning: could not render font `{font_name}`; using Matplotlib's default font.")
    return font_manager.FontProperties()


def configure_math_font(plt, font_name: str) -> None:
    if font_name.casefold() in {"times", "times new roman"}:
        # STIX matches Times typography and avoids fragile external-font math rendering.
        plt.rcParams["mathtext.fontset"] = "stix"


def find_system_font_paths(font_manager) -> list[str]:
    font_paths: list[str] = []
    for extension in ("ttf", "otf", "ttc"):
        font_paths.extend(font_manager.findSystemFonts(fontext=extension))
    return font_paths


def font_path_matches_name(font_manager, font_path: str, font_name: str) -> bool:
    try:
        candidate = font_manager.FontProperties(fname=font_path)
        return candidate.get_name() == font_name
    except Exception:
        return False


def usable_font_properties(font_manager, font_path: str):
    try:
        from matplotlib.ft2font import FT2Font

        face = FT2Font(font_path)
        for size in (10, 12, 14):
            face.set_size(size, 72)
    except Exception:
        return None
    return font_manager.FontProperties(fname=font_path)
