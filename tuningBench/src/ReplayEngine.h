#pragma once

#include <functional>
#include <memory>
#include <random>

#include "TuningPhaseTable.h"
#include "autopas/tuning/tuningStrategy/TuningStrategyInterface.h"

namespace autopas {

using Strategies = std::vector<std::unique_ptr<TuningStrategyInterface>>;
using StrategyFactory = std::function<Strategies(const std::set<Configuration> &, unsigned long)>;

PhaseResult replayPhase(Strategies &strategies, const TuningPhaseTable &phase,
                        const std::set<Configuration> &searchSpace, EvidenceCollection &evidenceCollection,
                        const ReplayOptions &options, std::mt19937 &rng, unsigned long startIteration);

std::vector<PhaseResult> replayScenario(const StrategyFactory &makeStrategy, const ScenarioData &scenario,
                                        const ReplayOptions &options, unsigned long seed);

}  // namespace autopas
