#include "LogParser.h"

#include <fstream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>

#include "autopas/tuning/tuningStrategy/TuningLogEntry.h"

namespace autopas {

ScenarioData parseLogFile(const std::string &filename) {
  std::ifstream logfileStream(filename);

  if (!logfileStream) throw std::runtime_error("Could not open logfile: " + filename);

  bool evidenceAdded = false;
  size_t currPhaseIndex = 0;
  TuningPhaseTable currTuningPhase{.phaseIndex = currPhaseIndex};
  ScenarioData scenarioData{.sourceFile = filename};
  std::optional<LiveInfo> pendingLiveInfo{};

  std::string line;
  while (std::getline(logfileStream, line)) {
    std::stringstream stream{line};
    std::string type;
    std::getline(stream, type, ' ');

    if (type == "evidence") {
      const auto [reduced, iteration, config] = tuningLogEntry::readEvidence(stream);

      currTuningPhase.measurements.emplace(config, SampleSet{.reduced = reduced, .iteration = iteration});
      scenarioData.searchSpace.emplace(config);

      evidenceAdded = true;
    } else if (type == "liveInfo") {
      pendingLiveInfo = tuningLogEntry::readLiveInfo(stream);
    } else if (type == "reset") {
      if (evidenceAdded) {
        currTuningPhase.finalize();
        scenarioData.phases.push_back(std::move(currTuningPhase));
        ++currPhaseIndex;
        evidenceAdded = false;
      }

      currTuningPhase = TuningPhaseTable{.phaseIndex = currPhaseIndex, .liveInfo = pendingLiveInfo};
      pendingLiveInfo.reset();
    }
  }

  if (evidenceAdded) {
    currTuningPhase.finalize();
    scenarioData.phases.push_back(std::move(currTuningPhase));
  }

  return scenarioData;
}

// https://stackoverflow.com/a/46931770
std::vector<std::string> split(const std::string &s, char delim) {
  std::vector<std::string> result;
  std::stringstream ss(s);
  std::string item;

  while (getline(ss, item, delim)) {
    result.push_back(item);
  }

  return result;
}

void addRawSamples(ScenarioData &scenario, const std::string &filename) {
  // CSV columns:
  // Date,Iteration,Interaction Type,Container,CellSizeFactor,Traversal,Load Estimator,Data Layout,
  // Newton 3,VectorizationPattern,rebuildSample 0 to n,traverseInteractionSample 0 to n,
  // Reduced,Smoothed,Mean Rebuild Frequency

  std::ifstream tuningDataStream(filename);

  if (!tuningDataStream) throw std::runtime_error("Could not open tuning data file: " + filename);

  std::map<std::string, Configuration> configStringMap;
  for (const auto &config : scenario.searchSpace) {
    configStringMap.emplace(config.getCSVLine(), config);
  }

  std::string line;
  std::getline(tuningDataStream, line);

  auto header = split(line, ',');
  size_t firstIterationSampleCol =
      std::distance(header.begin(), std::ranges::find(header, "traverseInteractionSample 0"));
  size_t firstRebuildSampleCol = std::distance(header.begin(), std::ranges::find(header, "rebuildSample 0"));
  size_t rebuildFreqCol = std::distance(header.begin(), std::ranges::find(header, "Mean Rebuild Frequency"));

  if (firstIterationSampleCol >= header.size() || firstRebuildSampleCol >= header.size())
    throw std::runtime_error("Invalid tuning data file.");

  std::string searchString = "traverseInteractionSample ";
  size_t pos = line.rfind(searchString);
  if (pos >= line.size()) throw std::runtime_error("Invalid tuning data file.");

  auto numSamplesSubstr = line.substr(pos + searchString.size(), line.find(",", pos) - pos);
  size_t numSamples = std::stoul(numSamplesSubstr) + 1;

  while (std::getline(tuningDataStream, line)) {
    auto row = split(line, ',');

    size_t iteration = std::stoul(row.at(1));

    std::string configString = "";
    for (size_t i = 2; i < 10; i++) {
      configString.append(row.at(i) + ",");
    }
    configString.pop_back();
    Configuration config = configStringMap.at(configString);

    for (auto &phase : scenario.phases) {
      auto it = phase.measurements.find(config);
      if (it != phase.measurements.end() and it->second.iteration == iteration) {
        auto &samples = it->second.rawSamples;
        auto &rebuildSamples = it->second.rebuildSamples;
        for (size_t i = 0; i < numSamples; i++) {
          long sample = std::stol(row.at(firstIterationSampleCol + i));
          long rebuild = std::stol(row.at(firstRebuildSampleCol + i));
          if (sample >= 0) samples.push_back(sample);
          if (rebuild >= 0) rebuildSamples.push_back(rebuild);
        }
        it->second.rebuildFrequency = std::stod(row.at(rebuildFreqCol));
        break;
      }
    }
  }
}

}  // namespace autopas
