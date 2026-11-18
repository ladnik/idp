import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

TOOLS = Path(__file__).resolve().parents[3]
IS_HPC = os.getenv("IS_HPC", "").lower() in ["1", "true"]

load_dotenv(TOOLS / (".env.hpc" if IS_HPC else ".env"))


@dataclass
class Config:
    """
    Class containing global configuration settings
    """

    # Path to AutoPas md-flexible executable
    mdflexible_bin: Path = Path(TOOLS / os.environ["MDFLEXIBLE_BIN"]).resolve()
    # Path to parsing/replay executable
    tuningbench_bin: Path = Path(TOOLS / os.environ["TUNINGBENCH_BIN"]).resolve()
    # Path to AutoPas ground truth measurements
    measurements_dir: Path = Path(TOOLS / os.environ["MEASUREMENTS_DIR"]).resolve()
    # Path to the templates of the different scenarios, should follow the scheme "<scenario>/template.jinja"
    experiments_dir: Path = Path(TOOLS / os.environ["EXPERIMENTS_DIR"]).resolve()
    # Path to output figures etc. to
    analysis_dir: Path = Path(TOOLS / os.environ["ANALYSIS_DIR"]).resolve()
    # SLURM job template
    slurm_template: Path = Path(TOOLS / os.environ["SLURM_TEMPLATE"])


config = Config()
