#include "Metrics.h"

namespace autopas {

long evalsToWithin(const std::vector<long> &evalsCurve, long optimalValue, double epsilon) {
  double limit = static_cast<double>(optimalValue) * (1.0 + epsilon);
  for (size_t i = 0; i < evalsCurve.size(); ++i) {
    if (static_cast<double>(evalsCurve[i]) <= limit) return static_cast<long>(i) + 1;
  }
  return -1L;
}

PhaseMetrics computeMetrics(const PhaseResult &result, const TuningPhaseTable &phase, const std::string &scenario,
                            const std::string &strategy, unsigned long seed) {
  PhaseMetrics metrics;

  metrics.scenario = scenario;
  metrics.tuningStrategy = strategy;
  metrics.seed = seed;

  metrics.phaseIndex = result.phaseIndex;
  metrics.evaluations = result.evaluations;
  metrics.tuningIterations = result.tuningIterations;
  metrics.searchSpaceSize = result.searchSpaceSize;

  metrics.chosenValue = result.chosenValue;
  metrics.optimalValue = result.optimalValue;
  metrics.selectionRatio =
      result.chosenValue > 0 ? static_cast<double>(result.optimalValue) / static_cast<double>(result.chosenValue) : 0.0;

  // find first element >= result.chosenValue
  auto it = std::ranges::lower_bound(phase.sortedValues, result.chosenValue);
  metrics.rankOfChosen = static_cast<size_t>(std::distance(phase.sortedValues.begin(), it));

  metrics.evalsToWithin1Pct = evalsToWithin(result.bestSoFarCurve, result.optimalValue, 0.01);
  metrics.evalsToWithin5Pct = evalsToWithin(result.bestSoFarCurve, result.optimalValue, 0.05);
  metrics.evalsToWithin10Pct = evalsToWithin(result.bestSoFarCurve, result.optimalValue, 0.1);

  metrics.tuningCost = result.tuningCost;
  metrics.simulationCost = result.simulationCost;
  metrics.totalCost = result.tuningCost + result.simulationCost;

  metrics.tuningOverheadNanoSeconds = result.tuningOverheadNanoSeconds;

  return metrics;
}

long dynamicOracleCost(const ScenarioData &scenario, const ReplayOptions &options) {
  long cost = 0;
  for (const auto phase : scenario.phases) {
    cost += options.tuningInterval * phase.bestValue;
  }
  return cost;
}

std::pair<Configuration, long> staticOracleCost(const ScenarioData &scenario, const ReplayOptions &options) {
  Configuration bestConfig;
  long bestCost = std::numeric_limits<long>::max();

  for (const auto config : scenario.searchSpace) {
    long cost = 0;
    bool usableConfig = true;
    for (const auto phase : scenario.phases) {
      auto valueInPhase = phase.valueOf(config);
      if (valueInPhase.has_value()) {
        usableConfig = false;
        break;
      }
      cost += options.tuningInterval * valueInPhase.value();
    }

    if (usableConfig && cost < bestCost) {
      bestConfig = config;
      bestCost = cost;
    }
  }

  return {bestConfig, bestCost};
}

}  // namespace autopas