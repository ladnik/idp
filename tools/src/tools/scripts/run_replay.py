from tools.models.config import config
from enum import StrEnum
import subprocess
from pathlib import Path
from tools.models.experiment import Scenario, tuning_interval_per_scenario
import sys
import yaml

import numpy as np
import pandas as pd
from tools.models.plot import band_plot


class TuningStrategy(StrEnum):
    RANDOM_SEARCH = "random-Search"
    SIMULATED_ANNEALING = "simulated-annealing"


SCENARIO_SUFFIXES = {
    "_equil": Scenario.EQUILIBRIUM,
    "_expl": Scenario.EXPLODING_LIQUID,
    "_hs": Scenario.HEATING_SPHERE,
}

# Number of configs a strategy can test in each phase (maxEvidence)
budgets = [3, 5, 8, 10, 15, 20, 30, 40, 50, 75, 100]

num_seeds = 30
start_seed = 1234


def load_scenario_yaml(
    measurements_path: Path, filename: str = "scenario.yaml"
) -> dict[str, str]:
    with open(measurements_path / filename) as f:
        return yaml.safe_load(f)


def generate_replay_data(
    measurements_path: Path,
    results_path: Path,
    tuning_interval: int,
    tuning_samples: int,
) -> None:
    """Generates replay data from full-search runs using the tuningBench application. Resulting files will be stored in 'analysis_path/<scenario>'."""

    tuning_data_file = next(measurements_path.glob(f"*tuningData*.csv"))
    tuning_log_file = next(measurements_path.glob(f"*tuningLog*.txt"))

    for tuning_strategy in TuningStrategy:
        for budget in budgets:
            # Generated result CSV
            resultfile = results_path / f"{tuning_strategy}_b{budget}.csv"
            # Console output of tuningBench
            logfile = results_path / f"{tuning_strategy}_b{budget}.log"

            replay_cmd = [
                config.tuningbench_bin,
                "--strategy",
                tuning_strategy,
                "--max-evidence",
                str(budget),
                "--tuning-interval",
                str(tuning_interval),
                "--tuning-samples",
                str(tuning_samples),
                "--noise",
                "resampled",
                "--tuning-data",
                tuning_data_file,
                "--seeds",
                str(num_seeds),
                "--seed",
                str(start_seed),
                "--out",
                resultfile,
                tuning_log_file,
            ]
            print(
                f"Replaying {tuning_data_file.name} with {tuning_strategy} and budget {budget}"
            )
            with logfile.open("w") as log:
                subprocess.run(replay_cmd, check=True, stdout=log)

def load_replay_data(results_path: Path) -> pd.DataFrame:
    frames = []
    for path in sorted(results_path.glob("*_b*.csv")):
        frame = pd.read_csv(path, comment="#")
        frame["budget"] = int(path.stem.rsplit("_b", 1)[1])
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def dynamic_oracle_cost(tuning_phases: pd.DataFrame, tuning_interval: int) -> float:
    optimal_sum = tuning_phases["optimalValue"].sum()
    return float(tuning_interval * optimal_sum)


def static_oracle_cost(analysis_path: Path) -> float:
    logfile = next(analysis_path.glob(f"*_b*.log"))
    for line in logfile.read_text().splitlines():
        if line.strip().startswith("static oracle:"):
            return float(line.split()[2])
    return float("nan")


def aggregate_phases(
    tuning_phases: pd.DataFrame, dynamic_oracle: float
) -> pd.DataFrame:
    """Aggregates the data in the dataframe s.t. only one row per unique (strategy, budget, seed) remains."""
    # mean = avg
    unique = tuning_phases.groupby(["tuningStrategy", "budget", "seed"]).agg(
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
    return unique.reset_index()


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: run_reply.py <measurements>")

    # scenario = Scenario(sys.argv[1])
    measurements = config.measurements_dir / sys.argv[1]
    out = config.analysis_dir / sys.argv[1]

    results = out / "results"
    figures = out / "figures"

    out.mkdir(exist_ok=True)
    results.mkdir(exist_ok=True)
    figures.mkdir(exist_ok=True)

    print("Loading scenario settings...")
    settings = load_scenario_yaml(measurements)

    tuning_interval = settings["tuning-interval"]
    tuning_samples = settings["tuning-samples"]
    iterations = settings["iterations"]

    scenario = SCENARIO_SUFFIXES.get(settings["output-suffix"])
    if scenario is None:
        print("Could not determine scenario.")
        sys.exit(1)

    replay = False if input("Generate replay data? [Y/n] ").lower() == "n" else True
    if(replay):
        print(f"Generating replay data for scenario {scenario}...")
        generate_replay_data(measurements, results, tuning_interval, tuning_samples)

    print("Loading and aggregating data...")
    tuning_phases_frame = load_replay_data(results)
    num_tuning_phases = tuning_phases_frame["phaseIndex"].nunique()

    dynamic_oracle = dynamic_oracle_cost(tuning_phases_frame, tuning_interval)
    static_oracle = static_oracle_cost(results)
    aggregated_data = aggregate_phases(tuning_phases_frame, dynamic_oracle)
    aggregated_data.to_csv(out / "summary.csv", index=False, float_format="%.4f")
    
    plot = False if input("Generate plots? [Y/n] ").lower() == "n" else True
    if(plot):
        print("Plotting results...")
        band_plot(aggregated_data, "meanSelectionRatio", "Exploding Liquid", "Mean Selection Ratio", "Budget", figures / "mean_sel.png", 1)
    
    print("Done!")

if __name__ == "__main__":
    main()
