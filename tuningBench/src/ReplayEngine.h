#pragma once

#include <functional>
#include <memory>
#include <random>

#include "TuningPhaseTable.h"
#include "autopas/tuning/tuningStrategy/TuningStrategyInterface.h"

namespace autopas {

PhaseResult replayPhase(TuningStrategyInterface &strategy, const TuningPhaseTable &phase,
                        const std::set<Configuration> &searchSpace, EvidenceCollection &evidenceCollection,
                        const ReplayOptions &options, std::mt19937 &rng, unsigned long startIteration);

using StrategyFactory = std::function<std::unique_ptr<TuningStrategyInterface>(
    const std::set<Configuration> &searchSpace, unsigned long seed)>;

std::vector<PhaseResult> replayScenario(const StrategyFactory &makeStrategy, const ScenarioData &scenario,
                                        const ReplayOptions &options, unsigned long seed);

}  // namespace autopas
