#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

#include "LogParser.h"
#include "Metrics.h"
#include "ReplayEngine.h"
#include "autopas/tuning/tuningStrategy/TuningStrategyFactory.h"

namespace {

void usage() {
  std::cerr
      << "Usage: tuningBench [options] <tuningLog.txt> [tuningLog.txt ...]\n"
      << "  --dump                          print parsed tuning phases and exit\n"
      << "  --strategy <name,...>           tuning strategy to replay (default: random-search)\n"
      << "  --seed <val>                    seed for stochastic strategies (default: 1234)\n"
      << "  --tuning-interval <val>         iterations between tuning phases (default: 100)\n"
      << "  --tuning-samples <val>          samples per configuration (default: 3)\n"
      << "  --max-evidence <val>            max budget for tuning strategies (default: size of search space)\n"
      << "  --seeds <val>                   number of seeds to replay per scenario (default: 1)\n"
      << "  --out <file>                    write metrics to csv file (default: no output)\n"
      << "  --noise <mode>                  reduced or resampled (default: reduced)\n"
      << "  --tuning-data <file>            tuningData csv with raw samples, required for resampling\n"
      << "  --drop-first-samples <val>      leading samples to ignore when resampling (default: 0)\n"
      << "  --sa-initial-temperature <val>  simulated annealing: initial temperature (default: 0.2)\n"
      << "  --sa-end-temperature <val>      simulated annealing: end temperature (default: 0.01)\n"
      << "  --sa-exclusion-factor <val>     simulated annealing: exclusion factor (default: 3.0)\n"
      << "  --sa-level-variance <val>       simulated annealing: level change variance (default: 0.75)\n"
      << "  --pt-max-phases-wo-test <val>   predictive tuning: max phases without test (default: 5)\n"
      << "  --pt-relative-opt-range <val>   predictive tuning: relative optimum range (default: 1.2)\n"
      << "  --pt-extrapolation <val>        predictive tuning: extrapolation method (default: \"linear-regression\")\n"
      << "  --rbt-rule-file <path>          rule based tuning: tuning file (default: \"tuningRules.rule\")\n";
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
            const autopas::ReplayOptions &options, const std::string &strategyName, unsigned long seed) {
  std::cout << scenario.sourceFile << " [" << strategyName << ", seed=" << seed << "]\n";

  long totalCost = 0;
  for (const auto &result : results) {
    // fraction of optimum, 1 means best configuration was selected
    double selectionRatio =
        result.chosenValueRecorded > 0 ? static_cast<double>(result.optimalValue) / result.chosenValueRecorded : 0.0;

    // time spent tuning + time spent computing with selected config
    totalCost += result.tuningCost + result.simulationCost;

    std::cout << "  phase " << result.phaseIndex << ": " << result.evaluations << "/" << result.searchSpaceSize
              << " configs, " << result.tuningIterations << " iterations"
              << ", chosen=" << result.chosenValueObserved << " ns, optimum=" << result.optimalValue << " ns"
              << ", selectionRatio=" << std::fixed << std::setprecision(4) << selectionRatio
              << ", cost=" << result.tuningCost << "+" << result.simulationCost << '\n';
  }
  auto dynamicOracle = autopas::dynamicOracleCost(scenario, options);
  auto staticOracle = autopas::staticOracleCost(scenario, options).second;

  std::cout << "  total cost:     " << totalCost << " ns\n";
  std::cout << "  dynamic oracle: " << dynamicOracle << " ns  (" << std::fixed << std::setprecision(2)
            << static_cast<double>(totalCost) / dynamicOracle << "x)\n";
  std::cout << "  static oracle:  " << staticOracle << " ns  (" << std::fixed << std::setprecision(2)
            << static_cast<double>(totalCost) / staticOracle << "x)\n";
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
  size_t numSeeds = 1;
  std::string csvFilename;
  std::string tuningDataFilename;
  autopas::ReplayOptions options{};

  // Simulated Annealing specific parameters to pass on
  double initialTemperature = 0.2;
  double endTemperature = 0.01;
  double exclusionFactor = 3.0;
  double levelChangeVariance = 0.75;

  // Predictive Tuning specific parameters to pass on
  unsigned int maxPhasesWithoutTest = 5;
  double relativeOptimumRange = 1.2;
  std::string extrapolationMethod{"linear-regression"};

  // Rule-Based Tuning specific parameters to pass on
  std::string ruleFileName{"tuningRules.rule"};

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
    } else if (arg == "--seeds") {
      numSeeds = std::stoul(nextArg(argc, argv, i));
    } else if (arg == "--out") {
      csvFilename = nextArg(argc, argv, i);
    } else if (arg == "--noise") {
      auto mode = nextArg(argc, argv, i);
      if (mode == "reduced") {
        options.noiseMode = autopas::NoiseMode::Reduced;
      } else if (mode == "resampled") {
        options.noiseMode = autopas::NoiseMode::Resampled;
      } else {
        std::cerr << "Unknown mode: " << mode << '\n';
        usage();
      }
    } else if (arg == "--tuning-data") {
      tuningDataFilename = nextArg(argc, argv, i);
    } else if (arg == "--drop-first-samples") {
      options.dropFirstSamples = std::stoul(nextArg(argc, argv, i));
    } else if (arg == "--sa-initial-temperature") {
      initialTemperature = std::stod(nextArg(argc, argv, i));
    } else if (arg == "--sa-end-temperature") {
      endTemperature = std::stod(nextArg(argc, argv, i));
    } else if (arg == "--sa-exclusion-factor") {
      exclusionFactor = std::stod(nextArg(argc, argv, i));
    } else if (arg == "--sa-level-variance") {
      levelChangeVariance = std::stod(nextArg(argc, argv, i));
    } else if (arg == "--pt-max-phases-wo-test") {
      maxPhasesWithoutTest = std::stoul(nextArg(argc, argv, i));
    } else if (arg == "--pt-relative-opt-range") {
      relativeOptimumRange = std::stod(nextArg(argc, argv, i));
    } else if (arg == "--pt-extrapolation") {
      extrapolationMethod = nextArg(argc, argv, i);
    } else if (arg == "--rbt-rule-file") {
      ruleFileName = nextArg(argc, argv, i);
    } else if (arg.rfind("--", 0) == 0) {
      std::cerr << "Unknown option: " << arg << '\n';
      usage();
    } else {
      files.push_back(arg);
    }
  }

  if (files.empty()) usage();

  try {
    auto chosenStrategies =
        autopas::TuningStrategyOption::parseOptions<std::vector<autopas::TuningStrategyOption>>(strategyName);
    if (chosenStrategies.empty()) {
      std::cerr << "Could not parse strategy '" << strategyName << "'.\n";
      return 1;
    }

    std::ofstream csvFile;
    if (!csvFilename.empty()) {
      csvFile.open(csvFilename);
      if (!csvFile) throw std::runtime_error("Could not open csv file: " + csvFilename);

      autopas::writeCsvMetadata(csvFile);
      autopas::writeCsvHeader(csvFile);
    }

    for (const auto &file : files) {
      autopas::ScenarioData scenario = autopas::parseLogFile(file);

      if (!tuningDataFilename.empty()) {
        autopas::addRawSamples(scenario, tuningDataFilename);
      } else if (options.noiseMode == autopas::NoiseMode::Resampled) {
        throw std::runtime_error("--noise resampled requires option --tuning-data");
      }

      // only dump all files in dumpMode, no replay
      if (dumpMode) {
        dump(scenario);
        continue;
      }

      size_t fullSearchBudget = scenario.searchSpace.size();
      size_t budget = maxEvidence > 0 ? maxEvidence : fullSearchBudget;

      autopas::StrategyFactory makeStrategies = [chosenStrategies, budget, initialTemperature, endTemperature,
                                                 exclusionFactor, levelChangeVariance, maxPhasesWithoutTest,
                                                 relativeOptimumRange, extrapolationMethod,
                                                 ruleFileName](const std::set<autopas::Configuration> &searchSpace,
                                                               unsigned long phaseSeed) {
        autopas::TuningStrategyFactoryInfo info{.maxEvidence = static_cast<unsigned int>(budget),
                                                .tuningStrategySeed = phaseSeed};
        info.initialTemperature = initialTemperature;
        info.endTemperature = endTemperature;
        info.exclusionFactor = exclusionFactor;
        info.levelChangeVariance = levelChangeVariance;
        info.maxTuningPhasesWithoutTest = maxPhasesWithoutTest;
        info.relativeOptimumRange = relativeOptimumRange;
        info.extrapolationMethodOption = *autopas::ExtrapolationMethodOption::parseOptions(extrapolationMethod).begin();
        info.ruleFileName = ruleFileName;

        std::vector<std::unique_ptr<autopas::TuningStrategyInterface>> strategies;
        for (const auto &strategy : chosenStrategies) {
          strategies.push_back(autopas::TuningStrategyFactory::generateTuningStrategy(
              searchSpace, strategy, info, autopas::InteractionTypeOption::pairwise));
        }
        return strategies;
      };

      // repeat replay for each seed
      for (size_t s = 0; s < numSeeds; ++s) {
        unsigned long currentSeed = seed + s;
        auto results = autopas::replayScenario(makeStrategies, scenario, options, currentSeed);
        report(scenario, results, options, strategyName, currentSeed);

        if (csvFile.is_open()) {
          for (size_t p = 0; p < results.size(); ++p) {
            auto metrics =
                autopas::computeMetrics(results[p], scenario.phases[p], scenario.sourceFile, strategyName, currentSeed);
            autopas::writeCsvRow(csvFile, metrics);
          }
        }
      }
    }
  } catch (std::exception &e) {
    std::cerr << "An error occurred: " << e.what() << '\n';
    return 1;
  }

  return 0;
}
