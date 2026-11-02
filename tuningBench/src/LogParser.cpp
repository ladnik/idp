#include "LogParser.h"

#include "autopas/tuning/tuningStrategy/TuningLogEntry.h"

#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>

namespace autopas {

ScenarioData parseLogFile(const std::string &filename)
{
    std::ifstream logfileStream(filename);

    if (!logfileStream)
        throw std::runtime_error("Could not open logfile: " + filename);

    bool evidenceAdded = false;
    size_t currPhaseIndex = 0;
    TuningPhaseTable currTuningPhase{.phaseIndex = currPhaseIndex};
    ScenarioData scenarioData{.sourceFile = filename};
    std::optional<LiveInfo> pendingLiveInfo{};

    std::string line;
    while (std::getline(logfileStream, line))
    {
        std::stringstream stream{line};
        std::string type;
        std::getline(stream, type, ' ');

        if (type == "evidence")
        {
            const auto [reduced, iteration, config] = tuningLogEntry::readEvidence(stream);

            currTuningPhase.measurements.emplace(config, SampleSet{.reduced = reduced, .iteration = iteration});

            evidenceAdded = true;
        }
        else if (type == "liveInfo")
        {
            pendingLiveInfo = tuningLogEntry::readLiveInfo(stream);
        }
        else if (type == "reset")
        {
            if (evidenceAdded)
            {
                currTuningPhase.finalize();
                scenarioData.phases.push_back(std::move(currTuningPhase));
                ++currPhaseIndex;
                evidenceAdded = false;
            }

            currTuningPhase = TuningPhaseTable{.phaseIndex = currPhaseIndex, .liveInfo = pendingLiveInfo};
            pendingLiveInfo.reset();
        }
    }

    if (evidenceAdded)
    {
        currTuningPhase.finalize();
        scenarioData.phases.push_back(std::move(currTuningPhase));
    }

    return scenarioData;
}

}  // namespace autopas
