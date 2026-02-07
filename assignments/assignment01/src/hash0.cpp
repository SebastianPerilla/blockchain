#include "hash0.h"
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

namespace hash0 {
    std::string xor32Hash(std::string str) {
        int32_t hash { 0 };

        for (size_t i { 0 }; i < str.size(); ++i) {
            int32_t shift = (i % 4) * 8;
            int32_t c { static_cast<unsigned char>(str[i]) };
            hash ^= (c << shift);
        }

        std::stringstream stream;
        stream << std::hex << std::setw(8) << std::setfill('0') << hash;
        std::string hexResult { stream.str() };

        return hexResult;

    } // Making this the 32 bit output
} // namespace hash0
