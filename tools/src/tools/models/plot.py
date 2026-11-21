from collections.abc import Callable

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MaxNLocator

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

DATA_COLORS = {
    "random-Search": "tab:blue",
    "simulated-annealing": "tab:red",
    "reference": "gray",
}
STYLING_COLORS = {
    "label": "#3b3a36",
    "light": "#8a897f",
    "grid": "#e4e3dd",
    "facecolor": "#fcfcfb",
}
STRATEGY_LABELS = {
    "random-Search": "Random Search",
    "simulated-annealing": "Simulated Annealing",
}


MAX_TICKS = 10


def style(ax, title: str, ylabel: str, xlabel: str) -> None:
    ax.set_facecolor(STYLING_COLORS["facecolor"])

    ax.set_title(title, loc="center", color=STYLING_COLORS["label"])
    ax.spines[["right", "top"]].set_visible(False)

    ax.set_xlabel(xlabel, color=STYLING_COLORS["label"])
    ax.set_ylabel(ylabel, color=STYLING_COLORS["label"])

    # ax.grid(axis="y", color=STYLING_COLORS["grid"])
    ax.tick_params(colors=STYLING_COLORS["label"])


def layout(ax, fig, outfile) -> None:
    ax.legend(frameon=False, labelcolor=STYLING_COLORS["label"], loc="best")
    fig.tight_layout()
    fig.savefig(outfile, dpi=300)
    plt.close(fig)


def xticks(ax, data, axis_value, xlog):
    ticks = sorted(data[axis_value].unique())
    if xlog:
        ax.set_xscale("log")
    ax.set_xticks(ticks)

    if len(ticks) <= MAX_TICKS:
        ax.set_xticklabels([str(b) for b in ticks])
    else:
        ax.xaxis.set_major_locator(MaxNLocator(nbins=MAX_TICKS, integer=True))
    ax.minorticks_off()


def draw_reference(ax, data, reference, reference_label) -> None:
    if reference is None:
        return
    val = reference(data) if callable(reference) else reference

    if isinstance(val, pd.Series):
        ax.plot(
            val.index,
            val,
            color=DATA_COLORS["reference"],
            linewidth=1,
            linestyle="--",
            label=reference_label,
        )
    else:
        ax.axhline(
            val,
            color=DATA_COLORS["reference"],
            linewidth=1,
            linestyle="--",
            label=reference_label,
        )


def line_plot(
    data,
    column_y,
    column_x,
    title,
    ylabel,
    xlabel,
    outfile,
    reference: ReferenceType = None,
    reference_label=None,
    xlog=False,
) -> None:
    """Generates a line plot of the given columns."""
    fig, ax = plt.subplots()

    for strategy, label in STRATEGY_LABELS.items():
        extract = data[data.tuningStrategy == strategy].groupby(column_x)[column_y]
        m = extract.median()

        color = DATA_COLORS[strategy]
        ax.plot(
            m.index,
            m,
            color=color,
            linewidth=2,
            marker="o",
            markersize=4,
            markeredgewidth=2,
            label=label,
        )

    draw_reference(ax, data, reference, reference_label)

    style(ax, title, ylabel, xlabel)
    xticks(ax, data, column_x, xlog)
    layout(ax, fig, outfile)


def band_plot(
    data,
    column_y,
    column_x,
    title,
    ylabel,
    xlabel,
    outfile,
    reference: ReferenceType = None,
    reference_label=None,
    xlog=False,
) -> None:
    """Generates a band plot of the given columns with band between first and third quantile."""
    fig, ax = plt.subplots()

    for strategy, label in STRATEGY_LABELS.items():
        # Plot median value over all runs with same (strategy, budget), but
        # also keep first/third quantile to show band of middle 50% of values
        extract = data[data.tuningStrategy == strategy].groupby(column_x)[column_y]
        m, q1, q3 = (
            extract.median(),
            extract.quantile(0.25),
            extract.quantile(0.75),
        )

        color = DATA_COLORS[strategy]
        ax.fill_between(m.index, q1, q3, color=color, alpha=0.2, linewidth=0)
        ax.plot(
            m.index,
            m,
            color=color,
            linewidth=2,
            marker="o",
            markersize=4,
            markeredgewidth=2,
            label=label,
        )

    draw_reference(ax, data, reference, reference_label)

    style(ax, title, ylabel, xlabel)
    xticks(ax, data, column_x, xlog)
    layout(ax, fig, outfile)
