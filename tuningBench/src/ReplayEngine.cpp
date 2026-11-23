#include "ReplayEngine.h"

#include <limits>

#include "autopas/tuning/searchSpace/EvidenceCollection.h"

namespace autopas {

namespace {
long sampleValue(const SampleSet &samples, const ReplayOptions &options, std::mt19937 &rng) {
  // fallback if no raw samples available/reduced mode selected
  if (options.noiseMode == NoiseMode::Reduced or samples.rawSamples.empty()) {
    return samples.reduced;
  }

  size_t firstSampleIndex = options.dropFirstSamples < samples.rawSamples.size() ? options.dropFirstSamples : 0;

  std::uniform_int_distribution<size_t> distrPick(firstSampleIndex, samples.rawSamples.size() - 1);
  std::vector<long> drawnSamples;
  drawnSamples.reserve(options.tuningSamples);

  // draw from real recorded samples
  for (size_t i = 0; i < options.tuningSamples; ++i) {
    drawnSamples.push_back(samples.rawSamples[distrPick(rng)]);
  }

  long rebuild = static_cast<long>(*std::min_element(samples.rebuildSamples.begin(), samples.rebuildSamples.end()) /
                                   samples.rebuildFrequency);

  // AutoPas default is minimum
  return *std::min_element(drawnSamples.begin(), drawnSamples.end()) + rebuild;
}
}  // namespace

PhaseResult replayPhase(Strategies &strategies, const TuningPhaseTable &phase,
                        const std::set<Configuration> &searchSpace, EvidenceCollection &evidenceCollection,
                        const ReplayOptions &options, std::mt19937 &rng, unsigned long startIteration) {
  PhaseResult phaseResult{
      .phaseIndex = phase.phaseIndex, .evaluations = 0, .tuningIterations = 0, .searchSpaceSize = searchSpace.size()};

  // similar process as in the real AutoTuner.cpp
  std::vector<Configuration> configQueue;
  configQueue.reserve(searchSpace.size());
  std::copy(searchSpace.rbegin(), searchSpace.rend(), std::back_inserter(configQueue));

  for (const auto &strategy : strategies) {
    if (strategy->needsLiveInfo() && phase.liveInfo.has_value()) {
      strategy->receiveLiveInfo(phase.liveInfo.value());
    }
  }

  size_t iteration = startIteration;
  long bestValueSoFar = std::numeric_limits<long>::max();
  auto before = std::chrono::steady_clock::now();
  for (const auto &strategy : strategies) {
    const auto backupQueue = configQueue;
    if (!strategy->reset(iteration, phase.phaseIndex, configQueue, evidenceCollection) && configQueue.empty()) {
      configQueue = backupQueue;
    }
  }
  phaseResult.tuningOverheadNanoSeconds =
      std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now() - before).count();

  bool firstConfig = true;
  while (!configQueue.empty()) {
    before = std::chrono::steady_clock::now();
    if (!firstConfig) {
      // AutoTuner does not call optimizeSuggestions directly after reset
      for (const auto &strategy : strategies) {
        const auto backupQueue = configQueue;
        if (!strategy->optimizeSuggestions(configQueue, evidenceCollection) && configQueue.empty()) {
          configQueue = backupQueue;
        }
      }
    }
    firstConfig = false;

    phaseResult.tuningOverheadNanoSeconds +=
        std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now() - before).count();

    if (configQueue.empty()) break;  // strategy ended phase

    Configuration configToTest = configQueue.back();
    const SampleSet *configSamples = phase.samplesOf(configToTest);

    if (configSamples) {
      long value = sampleValue(*configSamples, options, rng);

      bool stoppedEarly =
          !evidenceCollection.empty(phase.phaseIndex) &&
          (static_cast<double>(value) / static_cast<double>(bestValueSoFar) > options.earlyStoppingFactor);

      Evidence evidence{.iteration = iteration,
                        .tuningPhase = phase.phaseIndex,
                        .effectiveValue = value,
                        .rebuildValue = 0,
                        .traversalValue = value};
      evidenceCollection.addEvidence(configToTest, evidence);

      before = std::chrono::steady_clock::now();
      for (const auto &strategy : strategies) {
        strategy->addEvidence(configToTest, evidence);
      }
      phaseResult.tuningOverheadNanoSeconds +=
          std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now() - before).count();

      size_t tuningIterations = (stoppedEarly ? 1 : options.tuningSamples);
      bestValueSoFar = std::min(bestValueSoFar, value);
      iteration += tuningIterations;

      phaseResult.evaluations += 1;  // counts number of tested configs
      phaseResult.tuningIterations += tuningIterations;
      phaseResult.tuningCost += value * static_cast<long>(tuningIterations);
      phaseResult.bestSoFarCurve.push_back(bestValueSoFar);
    }

    configQueue.pop_back();
  }

  if (evidenceCollection.empty(phase.phaseIndex))
    throw std::runtime_error("Tuning strategy emptied queue before any measurements were taken.");

  const auto [chosenConfiguration, chosenEvidence] = evidenceCollection.getLatestOptimalConfiguration();

  phaseResult.chosenConfiguration = chosenConfiguration;
  phaseResult.chosenValueObserved = chosenEvidence.effectiveValue;
  phaseResult.chosenValueRecorded = phase.valueOf(chosenConfiguration).value();
  phaseResult.optimalValue = phase.bestValue;

  return phaseResult;
}

std::vector<PhaseResult> replayScenario(const StrategyFactory &makeStrategies, const ScenarioData &scenario,
                                        const ReplayOptions &options, unsigned long seed) {
  Strategies strategies;
  if (options.persistAcrossPhases) strategies = makeStrategies(scenario.searchSpace, seed);

  std::vector<PhaseResult> results;
  EvidenceCollection evidenceCollection;

  for (auto &phase : scenario.phases) {
    if (!options.persistAcrossPhases) strategies = makeStrategies(scenario.searchSpace, seed + phase.phaseIndex);

    if (strategies.empty()) throw std::runtime_error("Could not construct tuning strategies.");

    std::mt19937 rng(seed + phase.phaseIndex);
    PhaseResult result = replayPhase(strategies, phase, scenario.searchSpace, evidenceCollection, options, rng,
                                     phase.phaseIndex * options.tuningInterval);

    // iterations remaining (computed with newly selected config)
    long iterationsRemaining =
        options.tuningInterval > result.tuningIterations ? options.tuningInterval - result.tuningIterations : 0;

    result.simulationCost = iterationsRemaining * result.chosenValueRecorded;
    results.push_back(result);
  }

  return results;
}
}  // namespace autopas
