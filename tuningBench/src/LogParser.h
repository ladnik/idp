#pragma once

#include <string>

#include "TuningPhaseTable.h"

namespace autopas {

/// Parses a tuningLog file into phases. Throws std::runtime_error if the file cannot be opened.
ScenarioData parseLogFile(const std::string &filename);

}  // namespace autopas
