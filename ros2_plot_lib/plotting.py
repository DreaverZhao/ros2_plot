from __future__ import annotations

from .models import AppConfig


def render(config: AppConfig, data: dict[str, tuple[list[float], list[float]]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: install matplotlib, for example `python3 -m pip install matplotlib`."
        ) from exc

    fig, axes = plt.subplots(
        len(config.plots),
        1,
        sharex=True,
        squeeze=False,
        figsize=(10, max(3, 3 * len(config.plots))),
    )

    for axis, plot in zip(axes[:, 0], config.plots):
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
        if plot.title:
            axis.set_title(plot.title, loc=plot.title_loc)
        if plot.y_label:
            axis.yaxis.set_label_position(plot.y_label_side)
            axis.set_ylabel(plot.y_label, loc=plot.y_label_loc)
        axis.grid(True, alpha=0.25)
        if has_visible_labels:
            axis.legend()

    if config.plots[-1].x_label:
        axes[-1, 0].set_xlabel(config.plots[-1].x_label, loc=config.plots[-1].x_label_loc)
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
