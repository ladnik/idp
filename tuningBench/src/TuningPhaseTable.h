#pragma once

#include <limits>
#include <optional>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>

#include "autopas/tuning/Configuration.h"
#include "autopas/tuning/tuningStrategy/LiveInfo.h"

namespace autopas {

/*
    Recorded measurements for one configuration in one tuning phase.
*/
struct SampleSet {
  long reduced;
  std::vector<long> rawSamples;
  size_t iteration;
};

/*
    Recorded measurements in one tuning phase.
*/
struct TuningPhaseTable {
  size_t phaseIndex;
  std::optional<LiveInfo> liveInfo;
  std::unordered_map<Configuration, SampleSet, ConfigHash> measurements;

  Configuration bestConfig;
  long bestValue;
  /// Reduced values, sorted in ascending order
  std::vector<long> sortedValues;

  /// Computes bestConfig, bestValue and sortedValues from measurements.
  void finalize();

  /// Reduced value of a configuration or std::nullopt if it was not measured in this phase
  [[nodiscard]] std::optional<long> valueOf(const Configuration &config) const;

  /// Samples of a configuration or nullptr if it was not measured in this phase
  [[nodiscard]] const SampleSet *samplesOf(const Configuration &config) const;
};

/*
    Recorded measurements in one experiment run.
*/
struct ScenarioData {
  std::string sourceFile;
  std::vector<TuningPhaseTable> phases;
  std::set<Configuration> searchSpace;
};

enum class NoiseMode { Reduced, Resampled };

struct ReplayOptions {
  size_t tuningInterval{100};
  size_t tuningSamples{3};
  size_t dropFirstSamples{0};  // number of leading samples to drop on resampling (0 possibly includes warmup)
  double earlyStoppingFactor{std::numeric_limits<double>::infinity()};
  NoiseMode noiseMode{NoiseMode::Reduced};
  bool persistAcrossPhases{false};
};

/*
    Results of a replayed phase.
*/
struct PhaseResult {
  size_t phaseIndex;
  size_t evaluations;
  size_t tuningIterations;
  size_t searchSpaceSize;
  Configuration chosenConfiguration;
  long chosenValueObserved;  // value observed by strategy (influenced by resampling noise)
  long chosenValueRecorded;  // value recorded for chosen config (reduced value logged)
  long optimalValue;
  long tuningCost;
  long simulationCost;
  long tuningOverheadNanoSeconds;
  std::vector<long> bestSoFarCurve;
};

}  // namespace autopas
