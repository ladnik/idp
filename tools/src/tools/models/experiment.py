from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from jinja2 import Template

from tools.models.config import config


class Scenario(StrEnum):
    EQUILIBRIUM = "equilibrium"
    EXPLODING_LIQUID = "exploding-liquid"
    HEATING_SPHERE = "heating-sphere"


@dataclass
class Experiment:
    """Represents the configuration of a parametrized scenario."""

    scenario: Scenario

    iterations: int
    tuning_interval: int
    tuning_samples: int

    rendered_experiment_file: Path | None = field(default=None, init=False)

    def render_experiment_file(self) -> None:
        template_dir = config.experiments_dir / str(self.scenario)
        with open(template_dir / "template.jinja") as f:
            template = Template(f.read())

            context = {
                "iterations": self.iterations,
                "tuning_interval": self.tuning_interval,
                "tuning_samples": self.tuning_samples,
            }

            rendered = template.render(**context)
            filename = f"{self.scenario}-it{self.iterations}-ti{self.tuning_interval}-ts{self.tuning_samples}.yaml"
            self.rendered_experiment_file = (template_dir / "gen" / filename).resolve()

            with open(self.rendered_experiment_file, "w") as f:
                f.write(rendered)

    def generate_run_cmd(self, use_mpi: bool):
        cmd = f"{'mpiexec -np $SLURM_NTASKS' if use_mpi else 'mpiexec -np 1'} $MD_FLEX_BINARY --yaml-filename {self.get_experiment_file()} > log.txt"
        return cmd

    def get_job_name(self):
        return self.scenario

    def get_experiment_file(self):
        if self.rendered_experiment_file is None:
            self.render_experiment_file()
        return self.rendered_experiment_file


tuning_samples = 10
tuning_phases = 50
simulation_steps_per_phase = 2500

# From full-search run
search_space_per_scenario = {
    Scenario.EQUILIBRIUM: 210,
    Scenario.EXPLODING_LIQUID: 159,
    Scenario.HEATING_SPHERE: 111,
}

# Only non-tuning iterations count
iterations_per_scenario = {
    scenario: tuning_phases * simulation_steps_per_phase for scenario in Scenario
}

# Intervals have to be strictly greater than search_space_size * tuning_samples due to the "pause-simulation-during-tuning" option.
tuning_interval_per_scenario = {
    scenario: search_space_per_scenario[scenario] * tuning_samples
    + simulation_steps_per_phase
    for scenario in Scenario
}

experiments = [
    Experiment(
        scenario,
        iterations_per_scenario[scenario],
        tuning_interval_per_scenario[scenario],
        tuning_samples,
    )
    for scenario in Scenario
]
