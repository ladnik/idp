from __future__ import annotations

import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import yaml

from tools.models.config import config


class NoiseMode(StrEnum):
    RESAMPLED = "resampled"
    REDUCED = "reduced"


@dataclass(frozen=True)
class ReplaySettings:
    """Replay settings to use with tuningBench."""

    seeds: int = 30
    start_seed: int = 1234
    noise_mode: NoiseMode = NoiseMode.RESAMPLED
    drop_first_n_samples: int = 0


def gather_single_file(directory: Path, pattern: str) -> Path:
    """Find file matching a given pattern, raises RuntimeError if multiple or none are found."""
    matches = list(directory.glob(pattern))
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one file matching '{pattern}' in {directory}, but found {len(matches)} matches."
        )
    return matches[0]


def search_space_size(tuning_log: Path) -> int:
    """Number of configurations in search space reported by tuningBench."""
    output = subprocess.run(
        [str(config.tuningbench_bin), "--dump", str(tuning_log)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    match = re.search(r"(\d+) unique configurations", output)

    if match is None:
        raise RuntimeError(f"Could not read search space size of {tuning_log}.")

    return int(match.group(1))


@dataclass(frozen=True)
class ReplayInput:
    """Input files and settings full-search run of a scenario."""

    tuning_log: Path
    tuning_data: Path
    tuning_interval: int
    tuning_samples: int
    search_space_size: int

    @classmethod
    def from_measurements(cls, measurements_dir: Path) -> ReplayInput:
        with open(measurements_dir / "scenario.yaml") as f:
            scenario_settings = yaml.safe_load(f)

        tuning_log = gather_single_file(measurements_dir, "*tuningLog*.txt")
        tuning_data = gather_single_file(measurements_dir, "*tuningData*.csv")

        return cls(
            tuning_log=tuning_log,
            tuning_data=tuning_data,
            tuning_interval=int(scenario_settings["tuning-interval"]),
            tuning_samples=int(scenario_settings["tuning-samples"]),
            search_space_size=search_space_size(tuning_log),
        )


@dataclass
class ReplayJob:
    """Represents one replay job using tuningBench."""

    cmd: list[str]
    outfile: Path

    @property
    def progressfile(self) -> Path:
        return self.outfile.with_suffix(".csv.progress")

    @property
    def logfile(self) -> Path:
        return self.outfile.with_suffix(".log")

    @property
    def cmdfile(self) -> Path:
        return self.outfile.with_suffix(".cmd")

    def result_up_to_date(self) -> bool:
        return (
            self.outfile.exists()
            and self.cmdfile.exists()
            and self.cmdfile.read_text() == " ".join(self.cmd)
        )


def run_replay(replay_job: ReplayJob) -> str | None:
    """Runs one replay job. Returns message if error occurred."""

    replay_job.outfile.parent.mkdir(parents=True, exist_ok=True)

    with replay_job.logfile.open("w") as log:
        returncode = subprocess.run(replay_job.cmd, stdout=log).returncode
    if returncode:
        return f"{replay_job.outfile.name}: Exit code {returncode}. Refer to {replay_job.logfile}."

    replay_job.progressfile.rename(replay_job.outfile)
    replay_job.cmdfile.write_text(" ".join(replay_job.cmd))
    return None


def replay_all(
    replay_jobs: list[ReplayJob], num_threads: int, force_rerun: bool, dry_run: bool
) -> list[str]:
    """Runs all jobs that have not yet written results or are outdated. Returns list of error messages. Dry run prints commands that will be run."""

    jobs_todo = [
        job for job in replay_jobs if force_rerun or not job.result_up_to_date()
    ]

    print(f"{len(jobs_todo)}/{len(replay_jobs)} replays to run.")

    if dry_run:
        print("\n".join(" ".join(job.cmd) for job in jobs_todo))
        return []

    # run jobs in parallel as there may be a large number of them
    with ThreadPoolExecutor(num_threads) as thread_pool:
        return [msg for msg in thread_pool.map(run_replay, jobs_todo) if msg]
