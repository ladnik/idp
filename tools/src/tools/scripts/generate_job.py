import sys

from jinja2 import Template

from tools.models.config import config
from tools.models.experiment import Experiment, experiments


def generate_slurm_file(mail: str, experiments: list[Experiment], mpi: bool = False):
    with open(config.slurm_template) as f:
        template = Template(f.read())

        context = {
            "slurm_job_name": "AP_RUN_FS",
            "partition": "cm4_tiny",
            "qos": "cm4_tiny",
            "num_nodes": 1,
            "num_tasks": 1 if not mpi else 6,
            "num_cpus": 38 if not mpi else 24,
            "mail": mail,
            "use_mpi": mpi,
            "binary": config.mdflexible_bin,
            "jobs": experiments,
        }

        rendered = template.render(**context)

        with open("full-search-job.slurm", "w") as f:
            f.write(rendered)


def main():
    """Generates the SLURM job file for the full-search runs on CoolMUC4"""

    if len(sys.argv) < 2:
        print("Please provide a mail address that should receive notifications.")
        sys.exit(1)

    mail = sys.argv[1]
    generate_slurm_file(mail, experiments)


if __name__ == "__main__":
    main()
