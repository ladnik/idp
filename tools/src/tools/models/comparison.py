from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from tools.models.config import config
from tools.models.replay import ReplayJob, ReplaySettings
from tools.models.scenario import Scenario, ScenarioReference
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
from tools.plotting.plot import (
    chosen_value_vs_tuning_phase,
    column_vs_budget,
    plot_for_each_scenario,
    rank_of_chosen_bar_plot,
    selection_ratio_heatmap,
)

# Callable plotting function on list of scenarios and output path. Return value None.
PlotFn = Callable[[list[Scenario], Path], None]


@dataclass(frozen=True)
class Comparison:
    """Represents a comparison of different Variants on a given list of Scenarios and which plots to produce."""

    label: str
    scenario_references: list[ScenarioReference]
    variants: list[Variant]
    plots: dict[str, PlotFn]

    @property
    def output(self) -> Path:
        return config.analysis_dir / self.label

    def replay_jobs(self, settings: ReplaySettings) -> list[ReplayJob]:
        jobs = []
        for scenario in self.scenario_references:
            replay_input = scenario.replay_input
            for variant in self.variants:
                for budget in variant.budgets:
                    filename_stem = variant.filename_stem(
                        budget, replay_input.search_space_size
                    )
                    outfile = scenario.results_dir / f"{filename_stem}.csv"
                    cmd = variant.build_cmd(
                        budget,
                        replay_input,
                        settings,
                        outfile.with_suffix(".csv.progress"),
                    )
                    jobs.append(ReplayJob(cmd, outfile))
        return jobs

    def load(self) -> list[Scenario]:
        return [
            Scenario.load(scenario_reference, self.variants)
            for scenario_reference in self.scenario_references
        ]


# Comparisons defined below

# ---------------------------------- SCENARIOS ----------------------------------
SCREF_EQUILIBRIUM = ScenarioReference(
    "equilibrium", "Equilibrium", config.measurements_dir / "equilibrium-cluster"
)

SCREF_EXPLODING_LIQUID = ScenarioReference(
    "exploding-liquid",
    "Exploding Liquid",
    config.measurements_dir / "exploding-liquid-cluster",
)

SCREF_HEATING_SPHERE = ScenarioReference(
    "heating-sphere",
    "Heating Sphere",
    config.measurements_dir / "heating-sphere-cluster",
)

ALL_SCENARIOS = [SCREF_EQUILIBRIUM, SCREF_EXPLODING_LIQUID, SCREF_HEATING_SPHERE]

# ---------------------------------- STRATEGIES ----------------------------------
ALL_STRATEGIES = [VAR_SA_DEFAULT, VAR_SA_HIGH_INITTEMP, VAR_RS, VAR_FS, VAR_PT_DEFAULT]
ALL_STRATEGIES_RBT = [
    VAR_SA_DEFAULT_RBT,
    VAR_SA_HIGH_INITTEMP_RBT,
    VAR_RS_RBT,
    VAR_FS_RBT,
    VAR_PT_DEFAULT_RBT,
]

# ALL_STRATEGIES + ALL_STRATEGIES_RBT but nicely paired so that after var, always var+rbt comes next
ALL_STRATEGIES_RBT_PAIRS = [
    variant
    for pair in zip(ALL_STRATEGIES, ALL_STRATEGIES_RBT, strict=True)
    for variant in pair
]

# ---------------------------------- PLOTS ----------------------------------

p_mean_selection_ratio = partial(
    column_vs_budget,
    column="meanSelectionRatio",
    ylabel="Mean Selection Ratio",
    references={"Dynamic Oracle": 1.0},
)
p_cost_vs_dyn_oracle = partial(
    column_vs_budget,
    column="costVsDynOracle",
    ylabel="Total Cost / Dynamic Oracle",
    references={"Dynamic Oracle": 1.0},
)
p_cost_vs_stat_oracle = partial(
    column_vs_budget,
    column="costVsDynOracle",
    ylabel="Total Cost / Static Oracle",
    references={"Static Oracle": 1.0},
)
p_rank_of_chosen = partial(rank_of_chosen_bar_plot)
p_chosen_vs_phase = partial(chosen_value_vs_tuning_phase)
p_heatmap_selection_ratio = partial(plot_for_each_scenario, selection_ratio_heatmap)


def construct_plots_dict(variants: list[Variant]) -> dict[str, PlotFn]:
    return {
        "mean-selection-ratio": partial(p_mean_selection_ratio, variants=variants),
        "cost-vs-dyn-oracle": partial(p_cost_vs_dyn_oracle, variants=variants),
        "cost-vs-stat-oracle": partial(p_cost_vs_stat_oracle, variants=variants),
        "chosen-vs-phase-b50": partial(p_chosen_vs_phase, variants=variants, budget=50),
        "heatmap-selection-ratio": partial(
            p_heatmap_selection_ratio, variants=variants
        ),
        "rank-of-chosen": partial(p_rank_of_chosen, variants=variants),
    }


# ---------------------------------- COMPARISONS ----------------------------------

ALL_COMPARISONS = {
    "all-strategy-comparison": Comparison(
        "all-strategy-comparison",
        ALL_SCENARIOS,
        ALL_STRATEGIES_RBT_PAIRS,
        construct_plots_dict(ALL_STRATEGIES_RBT_PAIRS),
    ),
    "rs-sa-comparison": Comparison(
        "rs-sa-comparison",
        ALL_SCENARIOS,
        [VAR_RS, VAR_SA_DEFAULT],
        construct_plots_dict([VAR_RS, VAR_SA_DEFAULT]),
    ),
}
