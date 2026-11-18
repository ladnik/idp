import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pandas as pd

mpl.use("Agg")
mpl.rcParams.update(
    {
        "pgf.texsystem": "pdflatex",
        "text.usetex": True,
        "font.family": "serif",
        "font.serif": [],
        "font.sans-serif": [],
        "font.monospace": [],
        "axes.labelsize": 24,
        "font.size": 18,
        "legend.fontsize": 18,
        "xtick.labelsize": 18,
        "ytick.labelsize": 18,
    }
)

DATA_COLORS = {"random-Search": "tab:blue", "simulated-annealing": "tab:red"}
STYLING_COLORS = {
    "label": "#3b3a36",
    "light": "#8a897f",
    "grid": "#e4e3dd",
    "facecolor": "#fcfcfb",
}


def style_plot(ax, title: str, ylabel: str, xlabel: str) -> None:
    ax.set_facecolor(STYLING_COLORS["facecolor"])

    ax.set_title(title, loc="center", color=STYLING_COLORS["label"])

    ax.set_xlabel(xlabel, color=STYLING_COLORS["light"])
    ax.set_ylabel(ylabel, color=STYLING_COLORS["light"])

    ax.grid(axis="y", color=STYLING_COLORS["grid"])
    ax.tick_params(colors=STYLING_COLORS["light"])


def band_plot(
    data, column_to_plot, title, ylabel, xlabel, outfile, reference_value=None
) -> None:
    fig, ax = plt.subplots()

    for strategy, color in DATA_COLORS.items():
        # Plot median value over all runs with same (strategy, budget), but
        # also keep first/third quantile to show band of middle 50% of values
        extract = data[data.tuningStrategy == strategy].groupby("budget")[
            column_to_plot
        ]
        m, q1, q3 = (
            extract.median(),
            extract.quantile(0.25),
            extract.quantile(0.75),
        )
        ax.fill_between(m.index, q1, q3, color=color, alpha=0.2, linewidth=0)
        ax.plot(
            m.index,
            m,
            color=color,
            linewidth=2,
            marker="o",
            markersize=4,
            markeredgewidth=2,
            label=strategy,
        )

    if reference_value is not None:
        ax.axhline(
            reference_value, color=STYLING_COLORS["light"], linewidth=1, linestyle="--"
        )

    style_plot(ax, title, ylabel, xlabel)
    
    budgets = sorted(data["budget"].unique())
    ax.set_xticks(budgets)
    ax.set_xticklabels([str(b) for b in budgets])
    ax.minorticks_off()

    ax.legend(frameon=False, labelcolor=STYLING_COLORS["label"], loc="best")
    fig.tight_layout()
    fig.savefig(outfile, dpi=300)
    plt.close(fig)
