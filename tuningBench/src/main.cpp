#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

#include "LogParser.h"
#include "ReplayEngine.h"
#include "autopas/tuning/tuningStrategy/TuningStrategyFactory.h"

namespace {

void usage() {
  std::cerr << "Usage: tuningBench [options] <tuningLog.txt> [tuningLog.txt ...]\n"
            << "  --dump                  print parsed tuning phases and exit\n"
            << "  --strategy <name>       tuning strategy to replay (default: random-search)\n"
            << "  --seed <val>            seed for stochastic strategies (default: 1234)\n"
            << "  --tuning-interval <val> iterations between tuning phases (default: 100)\n"
            << "  --tuning-samples <val>  samples per configuration (default: 3)\n"
            << "  --max-evidence <val>    max budged for tuning strategies (default: size of search space)\n";
  std::exit(1);
}

void dump(const autopas::ScenarioData &scenario) {
  std::cout << scenario.sourceFile << ": " << scenario.phases.size() << " tuning phases, "
            << scenario.searchSpace.size() << " unique configurations\n";

  for (const auto &phase : scenario.phases) {
    std::cout << " tuning phase " << phase.phaseIndex << ": " << phase.measurements.size()
              << " configs, liveInfo=" << (phase.liveInfo.has_value() ? "yes" : "no")
              << ", best=" << phase.bestConfig.toShortString() << " @ " << phase.bestValue << " ns\n";
  }
}

void report(const autopas::ScenarioData &scenario, const std::vector<autopas::PhaseResult> &results,
            const std::string &strategyName, unsigned long seed) {
  std::cout << scenario.sourceFile << " [" << strategyName << ", seed=" << seed << "]\n";

  long totalCost = 0;
  for (const auto &result : results) {
    // fraction of optimum, 1 means best configuration was selected
    double selectionRatio =
        result.chosenValue > 0 ? static_cast<double>(result.optimalValue) / result.chosenValue : 0.0;

    // time spent tuning + time spent computing with selected config
    totalCost += result.tuningCost + result.simulationCost;

    std::cout << "  phase " << result.phaseIndex << ": " << result.evaluations << "/" << result.searchSpaceSize
              << " configs, " << result.tuningIterations << " iterations"
              << ", chosen=" << result.chosenValue << " ns, optimum=" << result.optimalValue << " ns"
              << ", selectionRatio=" << std::fixed << std::setprecision(4) << selectionRatio
              << ", cost=" << result.tuningCost << "+" << result.simulationCost << '\n';
  }
  std::cout << "  total cost: " << totalCost << " ns\n";
}

std::string nextArg(int argc, char **argv, int &i) {
  if (++i >= argc) usage();
  return std::string{argv[i]};
}

}  // namespace

int main(int argc, char **argv) {
  std::vector<std::string> files;
  bool dumpMode = false;
  std::string strategyName{"random-Search"};
  unsigned long seed = 1234;
  size_t maxEvidence = 0;
  autopas::ReplayOptions options{};

  for (int i = 1; i < argc; ++i) {
    const std::string arg{argv[i]};
    if (arg == "--dump") {
      dumpMode = true;
    } else if (arg == "--strategy") {
      strategyName = nextArg(argc, argv, i);
    } else if (arg == "--seed") {
      seed = std::stoul(nextArg(argc, argv, i));
    } else if (arg == "--tuning-interval") {
      options.tuningInterval = std::stoul(nextArg(argc, argv, i));
    } else if (arg == "--tuning-samples") {
      options.tuningSamples = std::stoul(nextArg(argc, argv, i));
    } else if (arg == "--max-evidence") {
      maxEvidence = std::stoul(nextArg(argc, argv, i));
    } else if (arg.rfind("--", 0) == 0) {
      std::cerr << "Unknown option: " << arg << '\n';
      usage();
    } else {
      files.push_back(arg);
    }
  }

  if (files.empty()) usage();

  try {
    auto parsedStrategies = autopas::TuningStrategyOption::parseOptions(strategyName);
    if (parsedStrategies.size() != 1) {
      std::cerr << "Could not parse strategy '" << strategyName << "'.\n";
      return 1;
    }

    auto chosenStrategy = *parsedStrategies.begin();

    for (const auto &file : files) {
      autopas::ScenarioData scenario = autopas::parseLogFile(file);

      // only dump all files in dumpMode, no replay
      if (dumpMode) {
        dump(scenario);
        continue;
      }

      size_t fullSearchBudget = scenario.searchSpace.size();
      size_t budget = maxEvidence > 0 ? maxEvidence : fullSearchBudget;

      autopas::StrategyFactory makeStrategy =
          [chosenStrategy, budget](const std::set<autopas::Configuration> &searchSpace, unsigned long phaseSeed) {
            autopas::TuningStrategyFactoryInfo info{.maxEvidence = static_cast<unsigned int>(budget),
                                                    .tuningStrategySeed = phaseSeed};
            return autopas::TuningStrategyFactory::generateTuningStrategy(searchSpace, chosenStrategy, info,
                                                                          autopas::InteractionTypeOption::pairwise);
          };

      auto results = autopas::replayScenario(makeStrategy, scenario, options, seed);
      report(scenario, results, strategyName, seed);
    }
  } catch (std::exception &e) {
    std::cerr << "An error occured: " << e.what() << '\n';
    return 1;
  }

  return 0;
}
