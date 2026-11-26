from dataclasses import dataclass, replace
from pathlib import Path

from tools.models.config import config
from tools.models.replay import NoiseMode, ReplayInput, ReplaySettings

FULL_BUDGET = -1
RBT_STRAT_STR = "rule-based-tuning"


@dataclass(frozen=True)
class Variant:
    """Represents a tuning strategy variant with fixed arguments."""

    label: str
    strategies: tuple[str, ...]
    args: tuple[str, ...] = ()
    budgets: tuple[int, ...] = (0,)

    def resolve_budget(self, budget: int, search_space: int) -> int:
        if budget not in self.budgets:
            raise ValueError(f"{self.label}: Budget {budget} not in {self.budgets}")
        return search_space if budget == FULL_BUDGET else budget

    def filename_stem(self, budget: int, search_space: int) -> str:
        return f"{self.label}_b{self.resolve_budget(budget, search_space)}"

    def build_cmd(
        self,
        budget: int,
        replay_input: ReplayInput,
        replay_settings: ReplaySettings,
        outfile: Path,
    ) -> list[str]:
        """Builds the command used to generate replay data for this variant at a single given budget."""

        budget = self.resolve_budget(budget, replay_input.search_space_size)

        cmd = [
            str(config.tuningbench_bin),
            "--strategy",
            ",".join(self.strategies),
            *self.args,
            "--tuning-interval",
            str(replay_input.tuning_interval),
            "--tuning-samples",
            str(replay_input.tuning_samples),
            "--seeds",
            str(replay_settings.seeds),
            "--seed",
            str(replay_settings.start_seed),
            "--noise",
            replay_settings.noise_mode,
            "--out",
            str(outfile),
        ]

        if budget > 0:
            cmd += ["--max-evidence", str(budget)]

        if RBT_STRAT_STR in self.strategies:
            cmd += ["--rbt-rule-file", str(config.rule_file)]

        if replay_settings.noise_mode == NoiseMode.RESAMPLED:
            cmd += ["--tuning-data", str(replay_input.tuning_data)]

        if replay_settings.drop_first_n_samples:
            cmd += ["--drop-first-samples", str(replay_settings.drop_first_n_samples)]

        cmd.append(str(replay_input.tuning_log))

        return cmd


def with_rbt_strategy(variant: Variant) -> Variant:
    return replace(
        variant,
        label=f"Rule-Based-Tuning, {variant.label}",
        strategies=(RBT_STRAT_STR, *variant.strategies),
    )


def generate_options(**options: object) -> tuple[str, ...]:
    """Generates tuningBench option flags for flag name and value.
    Example: generate_options(sa_initial_temperature=0.2) returns ("--sa-initial-temperature", "0.2")
    """

    return tuple(
        pair
        for option_name, value in options.items()
        for pair in (f"--{option_name.replace('_', '-')}", str(value))
    )


# Variants defined below

BUDGETS = (3, 5, 8, 10, 15, 20, 30, 40, 50, 75, 100)


def sa_variant_constructor(
    label: str,
    budgets: tuple[int, ...] = BUDGETS,
    t_init: float = 0.2,
    t_end: float = 0.01,
    excl_factor: float = 3.0,
    level_variance: float = 0.75,
) -> Variant:
    return Variant(
        label,
        ("simulated-annealing",),
        generate_options(
            sa_initial_temperature=t_init,
            sa_end_temperature=t_end,
            sa_exclusion_factor=excl_factor,
            sa_level_variance=level_variance,
        ),
        budgets,
    )


def pt_variant_constructor(
    label: str,
    budgets: tuple[int, ...] = (FULL_BUDGET,),
    max_phases_wo_test: int = 5,
    relative_opt_range: float = 1.2,
    extrapolation: str = "linear-regression",
) -> Variant:
    return Variant(
        label,
        ("predictive-tuning",),
        generate_options(
            pt_max_phases_wo_test=max_phases_wo_test,
            pt_relative_opt_range=relative_opt_range,
            pt_extrapolation=extrapolation,
        ),
        budgets,
    )


VAR_SA_DEFAULT = sa_variant_constructor("Simulated-Annealing")
VAR_SA_DEFAULT_RBT = with_rbt_strategy(VAR_SA_DEFAULT)
VAR_SA_HIGH_INITTEMP = sa_variant_constructor(
    "Simulated-Annealing-High-Inittemp", t_init=1.0
)
VAR_SA_HIGH_INITTEMP_RBT = with_rbt_strategy(VAR_SA_HIGH_INITTEMP)

VAR_FS = Variant(
    "Full-Search", ("random-Search",), budgets=(FULL_BUDGET,)
)  # replaying RS at full search space budget should basically be full search TODO: verify?
VAR_FS_RBT = with_rbt_strategy(VAR_FS)
VAR_RS = Variant("Random-Search", ("random-Search",), budgets=BUDGETS)
VAR_RS_RBT = with_rbt_strategy(VAR_RS)

VAR_PT_DEFAULT = pt_variant_constructor("Predictive-Tuning")
VAR_PT_DEFAULT_RBT = with_rbt_strategy(VAR_PT_DEFAULT)
