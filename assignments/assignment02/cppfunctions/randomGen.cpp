#include "randomGen.h"
#include <random>

namespace rando {

    std::mt19937 gen { std::random_device {}() };

    uint32_t randomU32() {
        static std::uniform_int_distribution<uint32_t> dist(0, std::numeric_limits<uint32_t>::max());
        return dist(gen);
    }
} // namespace rando
