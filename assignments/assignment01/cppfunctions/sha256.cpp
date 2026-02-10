#include "sha256.h"
#include <iomanip>
#include <openssl/sha.h>
#include <sstream>
#include <string>

namespace sha {
    std::string sha256Hex(const std::string &input) {
        unsigned char hash[SHA256_DIGEST_LENGTH];

        SHA256(reinterpret_cast<const unsigned char *>(input.data()), input.size(), hash);

        std::ostringstream oss;
        oss << std::hex << std::setfill('0');
        for (unsigned char c : hash) {
            oss << std::setw(2) << static_cast<int>(c);
        }
        return oss.str();
    }
} // namespace sha
