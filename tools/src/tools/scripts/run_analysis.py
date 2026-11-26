import argparse
import os
import sys

from tools.models.comparison import ALL_COMPARISONS
from tools.models.config import config
from tools.models.replay import NoiseMode, ReplaySettings, replay_all


def parse_cli_args():
    parser = argparse.ArgumentParser(
        description="A pipeline for running tuningBench replays of AutoPas tuning strategies and plotting the respective comparisons between them."
    )

    parser.add_argument(
        "--replay",
        action="store_true",
        help="Run replays for missing or outdated data.",
    )
    parser.add_argument(
        "--force-replay", action="store_true", help="Run replays even if up to date."
    )
    parser.add_argument(
        "--num-threads",
        type=int,
        default=os.cpu_count(),
        help="Number of replays to run in parallel.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Only print the replay commands to run."
    )
    # TODO: allow to specify ReplaySettings via CLI args

    parser.add_argument(
        "--plot", action="store_true", help="Generate plots for comparisons."
    )

    args = parser.parse_args()

    if not (args.replay or args.plot):
        parser.error("Specify an action to perform. Add --replay and/or --plot.")

    return args


def main():

    args = parse_cli_args()

    settings = ReplaySettings(noise_mode=NoiseMode.REDUCED)

    comparisons_to_run = ALL_COMPARISONS
    # comparisons_to_run = []

    for comparison_label in comparisons_to_run:
        comparison = ALL_COMPARISONS[comparison_label]
        print(f"Working on comparison '{comparison.label}':")

        if args.replay:
            errors = replay_all(
                comparison.replay_jobs(settings),
                args.num_threads,
                args.force_replay,
                args.dry_run,
            )
            print(f"Wrote replay data to '{config.analysis_dir}/replays/'.")
            if errors:
                sys.exit("\n".join(errors))

        if args.plot and not args.dry_run:
            scenarios = comparison.load()
            comparison.output.mkdir(parents=True, exist_ok=True)
            for idx, (name, plot) in enumerate(comparison.plots.items()):
                print(f"({idx}/{len(comparison.plots.items())}) Plotting '{name}'...")
                plot(scenarios, comparison.output / f"{name}.png")
            print(f"Wrote plots to '{comparison.output}'.")


if __name__ == "__main__":
    main()
