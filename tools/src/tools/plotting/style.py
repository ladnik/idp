from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import MaxNLocator

from tools.models.variant import (
    VAR_FS,
    VAR_FS_RBT,
    VAR_PT_DEFAULT,
    VAR_PT_DEFAULT_RBT,
    VAR_RS,
    VAR_RS_RBT,
    VAR_SA_DEFAULT,
    VAR_SA_DEFAULT_RBT,
    VAR_SA_HIGH_INITTEMP,
    VAR_SA_HIGH_INITTEMP_RBT,
    Variant,
)

ReferenceType = float | Callable[[pd.DataFrame], float | pd.Series] | None

mpl.use("Agg")
mpl.rcParams.update(
    {
        "pgf.texsystem": "pdflatex",
        "text.usetex": True,
        "font.family": "serif",
        "font.serif": [],
        "font.sans-serif": [],
        "font.monospace": [],
        "axes.labelsize": 20,
        "font.size": 16,
        "legend.fontsize": 16,
        "xtick.labelsize": 16,
        "ytick.labelsize": 16,
    }
)


STYLING_COLORS = {
    "label": "dimgray",
    "grid": "lightgray",
    "facecolor": "white",  # color of background
}


@dataclass(frozen=True)
class DataSeriesStyle:
    color: object
    line_style: str = "-"
    marker: str = "o"
    marker_size: int = 4
    line_width: int = 2
    hatching: str | None = None


SERIES_STYLES = {
    VAR_SA_DEFAULT: DataSeriesStyle("red"),
    VAR_SA_DEFAULT_RBT: DataSeriesStyle("red", line_style="--", hatching="/"),
    VAR_SA_HIGH_INITTEMP: DataSeriesStyle("salmon"),
    VAR_SA_HIGH_INITTEMP_RBT: DataSeriesStyle("salmon", line_style="--", hatching="/"),
    VAR_RS: DataSeriesStyle("gold"),
    VAR_RS_RBT: DataSeriesStyle("gold", line_style="--", hatching="/"),
    VAR_FS: DataSeriesStyle("indigo"),
    VAR_FS_RBT: DataSeriesStyle("indigo", line_style="--", hatching="/"),
    VAR_PT_DEFAULT: DataSeriesStyle("limegreen"),
    VAR_PT_DEFAULT_RBT: DataSeriesStyle("limegreen", line_style="--", hatching="/"),
}

REFERENCE_STYLES = {
    "Dynamic Oracle": DataSeriesStyle("gray"),
    "Static Oracle": DataSeriesStyle("gray", line_style="--"),
    "Optimum": DataSeriesStyle("black", line_style=":"),
}


PlotFn = Callable[[Any, Any], None]


def style(ax, title: str, ylabel: str, xlabel: str) -> None:
    """Sets axis colors, labels etc."""
    ax.set_facecolor(STYLING_COLORS["facecolor"])

    ax.set_title(title, loc="center", color=STYLING_COLORS["label"])
    ax.spines[["right", "top"]].set_visible(False)

    ax.set_xlabel(xlabel, color=STYLING_COLORS["label"])
    ax.set_ylabel(ylabel, color=STYLING_COLORS["label"])

    # ax.grid(axis="y", color=STYLING_COLORS["grid"])
    ax.tick_params(colors=STYLING_COLORS["label"])


def layout(
    columns: list,
    plot_functions: PlotFn | list[PlotFn],
    outfile,
    title: Callable[[Any], str] = str,
    xlabel: str = "",
    ylabel: str | list[str] = "",
    size: tuple[float, float] = (7, 5),
    legend_columns: int = 6,
    sharex: bool = True,
    sharey: bool = True,
    suptitle: str | None = None,
    colorbar_label: str | None = None,
) -> None:
    """Lays out and stores a grid of plots with given columns and one row per PlotFn. Single legend is shared on the bottom."""

    rows = plot_functions if isinstance(plot_functions, list) else [plot_functions]

    # if single label, repeat for all rows
    ylabels = ylabel if isinstance(ylabel, list) else [ylabel] * len(rows)

    fig, axes = plt.subplots(
        len(rows),
        len(columns),
        sharex="col" if sharex else False,  # only share x axis along column
        sharey="row" if sharey else False,  # only share y axis along row
        figsize=(size[0] * len(columns), size[1] * len(rows)),
        squeeze=False,
        layout="constrained",
    )

    if suptitle:
        fig.suptitle(suptitle, color=STYLING_COLORS["label"])

    if colorbar_label and len(axes.flat) > 0 and len(axes.flat[0].images) > 0:
        fig.colorbar(axes.flat[0].images[0], ax=axes, label=colorbar_label)

    for r_idx, row in enumerate(rows):
        for c_idx, col in enumerate(columns):
            ax = axes[r_idx, c_idx]
            row(ax, col)

            style(
                ax,
                title(col) if r_idx == 0 else "",
                ylabels[r_idx] if c_idx == 0 else "",
                xlabel if r_idx == len(rows) - 1 else "",
            )

    handles = {
        label: handle
        for ax in axes.flat
        for handle, label in zip(*ax.get_legend_handles_labels(), strict=False)
    }
    if handles:
        fig.legend(
            handles.values(),
            handles.keys(),
            loc="outside lower center",
            ncol=min(len(handles), legend_columns),
            frameon=False,
            labelcolor=STYLING_COLORS["label"],
        )

    fig.savefig(outfile, dpi=300)
    plt.close(fig)


def draw_reference(ax, references: Mapping[str, float | pd.Series]) -> None:
    for label, val in references.items():
        reference_style = REFERENCE_STYLES[label]

        if isinstance(val, pd.Series):
            ax.plot(
                val.index,
                val,
                label=label,
                color=reference_style.color,
                ls=reference_style.line_style,
            )
        else:
            ax.axhline(
                val,
                label=label,
                color=reference_style.color,
                ls=reference_style.line_style,
            )


def line_plot(
    ax,
    data: pd.DataFrame,
    column_y: str,
    column_x: str,
    variants: list[Variant],
    band_bounds: tuple[float, float] | None = (0.25, 0.75),
    aggregation_fn: str = "median",
) -> None:
    """Generates a line plot of the given columns on the given axis."""

    for variant in variants:
        series_style = SERIES_STYLES[variant]
        label = variant.label

        extract = data[data.label == label].groupby(column_x)[column_y]
        stat = extract.agg(aggregation_fn)

        # single, constant value
        if len(stat) == 1:
            ax.axhline(
                stat.iloc[0],
                color=series_style.color,
                ls=":" if series_style.line_style == "-" else "-.",
                lw=2,
                label=label,
            )
            continue
        # band plot
        if band_bounds is not None:
            ax.fill_between(
                stat.index,
                extract.quantile(band_bounds[0]),
                extract.quantile(band_bounds[1]),
                color=series_style.color,
                alpha=0.2,
                linewidth=0,
            )
        # main series line
        ax.plot(
            stat.index,
            stat,
            ls=series_style.line_style,
            marker=series_style.marker,
            markersize=series_style.marker_size,
            color=series_style.color,
            linewidth=series_style.line_width,
            label=label,
        )


def stacked_bar_plot(
    ax,
    table: pd.DataFrame,
    args: dict[str, dict] | None = None,
    show_totals: bool = False,
    label_rotation: int = 0,
) -> None:
    """Generates a stacked bar plot of the given table, where the rows are bars and the columns are the segments from bottom up."""
    bottom = np.zeros(len(table))

    for segment in table.columns:
        ax.bar(
            range(len(table)),
            table[segment],
            bottom=bottom,
            **(args or {}).get(segment, {}),
        )
        bottom += table[segment].to_numpy()

    ax.set_xlim(-1, len(table))  # margins

    if show_totals:
        for idx, total in enumerate(bottom):
            ax.text(
                idx,
                total * 1.01,
                f"{total:.2f}",
                ha="center",
                va="bottom",
                fontsize=11,
                color=STYLING_COLORS["label"],
            )

    ax.set_xticks(
        range(len(table)),
        [str(bar) for bar in table.index],
        rotation=label_rotation,
        ha="right" if label_rotation else "center",
    )


def heatmap_plot(ax, matrix: pd.DataFrame, args: dict | None = None):
    """Generates a heatmap plot of the given matrix."""
    heatmap = ax.imshow(
        matrix.to_numpy(), aspect="auto", origin="lower", **(args or {})
    )

    ax.set_xticks(range(len(matrix.columns)), [str(col) for col in matrix.columns])

    ax.yaxis.set_major_locator(MaxNLocator(nbins=10, integer=True))
    ax.spines[["left", "bottom"]].set_visible(False)
    return heatmap
