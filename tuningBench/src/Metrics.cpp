#include "Metrics.h"

#include <chrono>
#include <iomanip>
#include <thread>

#include "autopas/Version.h"

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

  metrics.chosenValueObserved = result.chosenValueObserved;
  metrics.chosenValueRecorded = result.chosenValueRecorded;
  metrics.optimalValue = result.optimalValue;

  // metric based on recorded value, not observed
  metrics.selectionRatio = result.chosenValueRecorded > 0 ? static_cast<double>(result.optimalValue) /
                                                                static_cast<double>(result.chosenValueRecorded)
                                                          : 0.0;
  metrics.observationBias = result.chosenValueRecorded > 0 ? static_cast<double>(result.chosenValueObserved) /
                                                                 static_cast<double>(result.chosenValueRecorded)
                                                           : 0.0;

  // sortedValues uses recorded values
  auto it = std::ranges::lower_bound(phase.sortedValues, result.chosenValueRecorded);
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
      if (!valueInPhase.has_value()) {
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

void writeCsvMetadata(std::ostream &out) {
  auto now = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());

  out << "# date: " << std::put_time(std::localtime(&now), "%Y-%m-%d %H:%M:%S") << '\n';
  out << "# compiler: " <<
#ifdef __VERSION__
      __VERSION__
#else
      "unknown"
#endif
      << '\n';
  out << "# hardwareConcurrency: " << std::thread::hardware_concurrency() << '\n';
  out << "# autoPasVersion: " << AutoPas_VERSION_MAJOR << '.' << AutoPas_VERSION_MINOR << '.' << AutoPas_VERSION_PATCH
      << '-' << AutoPas_VERSION_SUFFIX << (AutoPas_VERSION_IS_DIRTY ? "-dirty" : "") << '\n';
}

void writeCsvHeader(std::ostream &out) {
  out << "scenario,tuningStrategy,seed,phaseIndex,evaluations,tuningIterations,searchSpaceSize,chosenValueObserved,"
      << "chosenValueRecorded,optimalValue,selectionRatio,observationBias,rankOfChosen,evalsToWithin1Pct,"
      << "evalsToWithin5Pct,evalsToWithin10Pct,tuningCost,simulationCost,totalCost,tuningOverheadNanoSeconds\n";
}

void writeCsvRow(std::ostream &out, const PhaseMetrics &metrics) {
  out << '"' << metrics.scenario << '"' << ',' << metrics.tuningStrategy << ',' << metrics.seed << ','
      << metrics.phaseIndex << ',' << metrics.evaluations << ',' << metrics.tuningIterations << ','
      << metrics.searchSpaceSize << ',' << metrics.chosenValueObserved << ',' << metrics.chosenValueRecorded << ','
      << metrics.optimalValue << ',' << std::fixed << std::setprecision(6) << metrics.selectionRatio << ','
      << metrics.observationBias << ',' << metrics.rankOfChosen << ',' << metrics.evalsToWithin1Pct << ','
      << metrics.evalsToWithin5Pct << ',' << metrics.evalsToWithin10Pct << ',' << metrics.tuningCost << ','
      << metrics.simulationCost << ',' << metrics.totalCost << ',' << metrics.tuningOverheadNanoSeconds << '\n';
}

}  // namespace autopas
