from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import pandas as pd

from tools.models.config import config
from tools.models.replay import ReplayInput
from tools.models.variant import Variant


def dynamic_oracle_cost(tuning_phases: pd.DataFrame, tuning_interval: int) -> float:
    optimal_sum = tuning_phases.drop_duplicates("phaseIndex")["optimalValue"].sum()
    return float(tuning_interval * optimal_sum)


def static_oracle_cost(logfile: Path) -> float:
    for line in logfile.read_text().splitlines():
        if line.strip().startswith("static oracle:"):
            return float(line.split()[2])
    return float("nan")


def aggregate_phases(
    tuning_phases: pd.DataFrame, dynamic_oracle: float, static_oracle: float
) -> pd.DataFrame:
    """Aggregates the data in the dataframe s.t. only one row per unique (label, budget, seed) remains."""
    # mean = avg
    unique = tuning_phases.groupby(["label", "budget", "seed"]).agg(
        totalCost=("totalCost", "sum"),
        tuningCost=("tuningCost", "sum"),
        simulationCost=("simulationCost", "sum"),
        meanSelectionRatio=("selectionRatio", "mean"),
        worstSelectionRatio=("selectionRatio", "min"),
        meanRankOfChosen=("rankOfChosen", "mean"),
        optimumChosenPct=(
            "rankOfChosen",
            lambda r: (r == 0).mean(),
        ),  # how many of the chosen configurations were the optimum in that phase
    )
    unique["costVsDynOracle"] = unique["totalCost"] / dynamic_oracle
    unique["costVsStatOracle"] = unique["totalCost"] / static_oracle
    unique["tuningVsDynOracle"] = unique.tuningCost / dynamic_oracle
    unique["simulationVsDynOracle"] = unique.simulationCost / dynamic_oracle
    return unique.reset_index()


@dataclass(frozen=True)
class ScenarioReference:
    """Represents a reference to a scenario."""

    scenario_key: str
    scenario_title: str
    measurements_dir: Path

    @property
    def results_dir(self) -> Path:
        return config.analysis_dir / "replays" / self.scenario_key

    @cached_property
    def replay_input(self) -> ReplayInput:
        # cached_property annotation makes this property be computed only once, then cached
        return ReplayInput.from_measurements(self.measurements_dir)


@dataclass(frozen=True)
class Scenario:
    """Represents the full-search run data of a single scenario."""

    scenario_reference: ScenarioReference

    tuning_phases: pd.DataFrame
    aggregated_phases: pd.DataFrame
    dynamic_oracle: float
    static_oracle: float

    @classmethod
    def load(
        cls,
        scenario_reference: ScenarioReference,
        variants: list[Variant],
    ) -> Scenario:
        """Loads replay data for a given scenario to keep for different plots."""
        replay_input = scenario_reference.replay_input
        search_space_size = replay_input.search_space_size

        resultfile_map = {
            (
                variant.label,
                variant.resolve_budget(budget, search_space_size),
            ): scenario_reference.results_dir
            / f"{variant.filename_stem(budget, search_space_size)}.csv"
            for variant in variants
            for budget in variant.budgets
        }

        missing_replays = [
            str(resultfile)
            for resultfile in resultfile_map.values()
            if not resultfile.exists()
        ]
        if len(missing_replays) > 0:
            raise FileNotFoundError(
                "Some replay results are missing. Run with option --replay). Missing files:\n"
                + "\n".join(missing_replays)
            )

        frames = []
        for (label, budget), path in resultfile_map.items():
            frame = pd.read_csv(path, comment="#")
            frame["label"] = label
            frame["budget"] = budget
            frames.append(frame)
        tuning_phases = pd.concat(frames, ignore_index=True)

        dynamic_oracle = dynamic_oracle_cost(
            tuning_phases, replay_input.tuning_interval
        )
        some_logfile = next(iter(resultfile_map.values())).with_suffix(".log")
        static_oracle = static_oracle_cost(some_logfile)

        return cls(
            scenario_reference=scenario_reference,
            tuning_phases=tuning_phases,
            aggregated_phases=aggregate_phases(
                tuning_phases, dynamic_oracle, static_oracle
            ),
            dynamic_oracle=dynamic_oracle,
            static_oracle=static_oracle,
        )
