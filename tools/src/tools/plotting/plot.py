from collections.abc import Callable
from functools import partial
from pathlib import Path

import matplotlib as mpl
import numpy as np
import pandas as pd

from tools.models.scenario import Scenario
from tools.models.variant import Variant, with_rbt_strategy
from tools.plotting.style import (
    PlotFn,
    draw_reference,
    heatmap_plot,
    layout,
    line_plot,
    stacked_bar_plot,
)

# buckets and labels for rankOfChosen bar plots
RANK_BUCKETS = [-0.5, 0.5, 2.5, 9.5, np.inf]
RANK_LABELS = ["Optimum", "Rank 1-2", "Rank 3-9", "Other"]


def variant_rows(plot_fn: PlotFn, with_rbt: bool) -> list[PlotFn]:
    """Helper to add second row with rule based tuning variants."""
    if not with_rbt:
        return [plot_fn]
    return [plot_fn, lambda ax, variant: plot_fn(ax, with_rbt_strategy(variant))]


def plot_for_each_scenario(
    plot: Callable[..., None],
    scenarios: list[Scenario],
    outfile: Path,
    variants: list[Variant],
    **kwargs,
) -> None:
    """Calls a plot for all scenarios individually. Written to one file per scenario."""
    for scenario in scenarios:
        key = scenario.scenario_reference.scenario_key
        plot(
            scenario,
            outfile.with_stem(f"{outfile.stem}-{key}"),
            variants=variants,
            **kwargs,
        )


def column_vs_budget(
    scenarios: list[Scenario],
    outfile: Path,
    variants: list[Variant],
    column: str,
    ylabel: str,
    references: dict[str, float] | None = None,
    band_bounds: tuple[float, float] | None = (0.25, 0.75),
    legend_columns: int = 6,
) -> None:
    """Plots given column (aggregated) over all budgets."""

    def draw(ax, scenario: Scenario) -> None:
        line_plot(
            ax, scenario.aggregated_phases, column, "budget", variants, band_bounds
        )
        draw_reference(ax, references or {})

    layout(
        scenarios,
        draw,
        outfile,
        title=lambda scenario: scenario.scenario_reference.scenario_title,
        xlabel="Budget",
        ylabel=ylabel,
        sharey=False,
        legend_columns=legend_columns,
    )


def chosen_value_vs_tuning_phase(
    scenarios: list[Scenario], outfile: Path, variants: list[Variant], budget: int
) -> None:
    """Plots value of chosen configuration per tuning phase for a given budget."""

    def draw(ax, scenario: Scenario) -> None:
        phases = scenario.tuning_phases
        full_budget = scenario.scenario_reference.replay_input.search_space_size
        line_plot(
            ax,
            phases[phases.budget.isin([budget, full_budget])],
            "chosenValueRecorded",
            "phaseIndex",
            variants,
        )
        optimum = phases.drop_duplicates("phaseIndex").set_index("phaseIndex")
        draw_reference(ax, {"Optimum": optimum["optimalValue"].sort_index()})

    layout(
        scenarios,
        draw,
        outfile,
        title=lambda scenario: scenario.scenario_reference.scenario_title,
        xlabel="Tuning Phase",
        ylabel=f"Chosen Value @ Budget {budget}",
        sharey=False,
    )


def rank_of_chosen_bar_plot(
    scenarios: list[Scenario],
    outfile: Path,
    variants: list[Variant],
    with_rbt: bool = False,
) -> None:
    """Plots rank of chosen configuration over all budgets."""
    colors = dict(zip(RANK_LABELS, mpl.color_sequences["tab10"], strict=False))

    def draw(ax, variant: Variant, scenario: Scenario) -> None:
        phases = scenario.tuning_phases[scenario.tuning_phases.label == variant.label]
        buckets = pd.cut(phases["rankOfChosen"], RANK_BUCKETS, labels=RANK_LABELS)
        shares = pd.crosstab(phases["budget"], buckets, normalize="index").reindex(
            columns=RANK_LABELS, fill_value=0
        )
        stacked_bar_plot(
            ax,
            shares,
            {
                label: {"color": colors[label], "label": label, "width": 0.5}
                for label in RANK_LABELS
            },
        )

    rows = [
        row
        for scenario in scenarios
        for row in variant_rows(partial(draw, scenario=scenario), with_rbt)
    ]

    ylabels = [
        label
        for scenario in scenarios
        for label in (
            [
                scenario.scenario_reference.scenario_title,
                f"{scenario.scenario_reference.scenario_title} (+RBT)",
            ]
            if with_rbt
            else [scenario.scenario_reference.scenario_title]
        )
    ]

    layout(
        variants,
        rows,
        outfile,
        title=lambda variant: variant.label,
        xlabel="Budget",
        ylabel=ylabels,
        size=(5, 4),
    )


def selection_ratio_heatmap(
    scenario: Scenario,
    outfile: Path,
    variants: list[Variant],
    with_rbt: bool = False,
) -> None:
    """Plots heatmap of median selection ratio per tuning phase and budget."""

    def draw(ax, variant: Variant) -> None:
        phases = scenario.tuning_phases[scenario.tuning_phases.label == variant.label]
        matrix = phases.pivot_table(
            index="phaseIndex",
            columns="budget",
            values="selectionRatio",
            aggfunc="median",
        )
        heatmap_plot(ax, matrix, {"vmin": 0, "vmax": 1})

    layout(
        variants,
        variant_rows(draw, with_rbt),
        outfile,
        title=lambda variant: variant.label,
        xlabel="Budget",
        ylabel=["Tuning Phase", "Tuning Phase (+RBT)"] if with_rbt else "Tuning Phase",
        size=(5, 4),
        sharex=False,
        suptitle=scenario.scenario_reference.scenario_title,
        colorbar_label="Median Selection Ratio",
    )
