#include "TuningPhaseTable.h"

#include <algorithm>
#include <stdexcept>

namespace autopas {

void TuningPhaseTable::finalize() {
  if (measurements.empty()) {
    throw std::logic_error("TuningPhaseTable::finalize(): phase has no measurements");
  }

  const auto best = std::ranges::min_element(
      measurements, [](const auto &lhs, const auto &rhs) { return lhs.second.reduced < rhs.second.reduced; });
  bestConfig = best->first;
  bestValue = best->second.reduced;

  sortedValues.clear();
  sortedValues.reserve(measurements.size());
  for (const auto &[config, samples] : measurements) {
    sortedValues.push_back(samples.reduced);
  }
  std::ranges::sort(sortedValues);
}

std::optional<long> TuningPhaseTable::valueOf(const Configuration &config) const {
  const auto it = measurements.find(config);
  if (it == measurements.end()) {
    return std::nullopt;
  }
  return it->second.reduced;
}

}  // namespace autopas
