#pragma once

#include <ostream>
#include <string>

#include "TuningPhaseTable.h"

namespace autopas {

// struct to hold phase metrics, slight duplication of PhaseResults. Possibly improve in future.
struct PhaseMetrics {
  std::string scenario;
  std::string tuningStrategy;
  unsigned long seed;

  size_t phaseIndex;
  size_t evaluations;  // number of configs actually sampled
  size_t tuningIterations;
  size_t searchSpaceSize;  // number of configs in search space

  long chosenValueObserved;
  long chosenValueRecorded;
  long optimalValue;
  double selectionRatio;   // optimalValue / chosenValueRecorded, 1 means best configuration was selected
  double observationBias;  // chosenValueObserved / chosenValueRecorded, 1 without noise, < 1 if lucky draw
  size_t rankOfChosen;

  // how many evaluations are needed to reach within x% of optimum, -1 if never reached
  long evalsToWithin1Pct;
  long evalsToWithin5Pct;
  long evalsToWithin10Pct;

  long tuningCost;
  long simulationCost;
  long totalCost;  // tuningCost + simulationCost
  long tuningOverheadNanoSeconds;
};

PhaseMetrics computeMetrics(const PhaseResult &result, const TuningPhaseTable &phase, const std::string &scenario,
                            const std::string &strategy, unsigned long seed);

// best configuration per phase with zero tuning cost (ideal strategy)
long dynamicOracleCost(const ScenarioData &scenario, const ReplayOptions &options);

// single configuration with the lowest total cost across all phases with zero tuning cost (static strategy)
std::pair<Configuration, long> staticOracleCost(const ScenarioData &scenario, const ReplayOptions &options);

// metadata of run as comment in csv output
void writeCsvMetadata(std::ostream &out);

void writeCsvHeader(std::ostream &out);

void writeCsvRow(std::ostream &out, const PhaseMetrics &metrics);

}  // namespace autopas