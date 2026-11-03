#include <iostream>
#include <string>
#include <vector>

#include "LogParser.h"

namespace {

void dump(const autopas::ScenarioData &scenario) {
  std::cout << scenario.sourceFile << ": " << scenario.phases.size() << " tuning phases, "
            << scenario.searchSpace.size() << " unique configurations\n";

  for (const auto &phase : scenario.phases) {
    std::cout << " tuning phase " << phase.phaseIndex << ": " << phase.measurements.size()
              << " configs, liveInfo=" << (phase.liveInfo.has_value() ? "yes" : "no")
              << ", best=" << phase.bestConfig.toShortString() << " @ " << phase.bestValue << " ns\n";
  }
}

}  // namespace

int main(int argc, char **argv) {
  std::vector<std::string> files;
  bool dumpMode = false;

  // clean up before adding other options
  for (int i = 1; i < argc; ++i) {
    const std::string arg{argv[i]};
    if (arg == "--dump") {
      dumpMode = true;
    } else {
      files.push_back(arg);
    }
  }

  if (files.empty()) {
    std::cerr << "Usage: tuningBench --dump <tuningLog.txt> [tuningLog.txt ...]\n";
    return 1;
  }

  try {
    for (const auto &file : files) {
      autopas::ScenarioData scenario = autopas::parseLogFile(file);
      if (dumpMode) {
        dump(scenario);
      }
    }
  } catch (std::exception &e) {
    std::cerr << "An error occured: " << e.what() << '\n';
    return 1;
  }

  return 0;
}