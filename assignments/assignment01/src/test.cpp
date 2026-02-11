#include "sha256.h"
#include <iostream>
#include <random>
#include <sstream>
#include <unordered_map>
#include <vector>

void print() {
    std::cout << "Collision Found: \n";
    std::unordered_map<int32_t, std::string> seen { { 72, "Sebas" } };

    seen.insert({ 22, "Sebas" });
    seen.insert({ 42, "Sebas" });
    seen.insert({ 29, "Samuel" });

    std::unordered_map<std::string, int32_t> reverse;

    for (const auto &[key, value] : seen) {
        auto [it, inserted] = reverse.emplace(value, key);
        if (!inserted) {
            std::cout << "Keys " << it->second << " and " << key << " both map to \"" << value << "\"\n";
            break;
        }
    }
    std::cout << "Contents:\n";
    for (auto &p : seen) {
        std::cout << ' ' << p.first << " , " << p.second << '\n';
    }
}

// Random Function
namespace rando {
    std::mt19937 gen { std::random_device {}() };

    uint32_t randomU32() {
        static std::uniform_int_distribution<uint32_t> dist(0, std::numeric_limits<uint32_t>::max());
        return dist(gen);
    }
} // namespace rando

bool check(std::string str1, std::vector<std::string> stringVec) { return str1.compare(stringVec[-1]); }

std::string numToHex(const uint32_t num) {
    std::stringstream stream;
    stream << std::hex << num;
    std::string hexResult { stream.str() };
    return hexResult;
}

int main() {
    std::cout << "Hash 1: " << sha::sha256Hex("");
    std::cout << "Hash 2: " << sha::sha256Hex("");
    std::cout << "Hash 3: " << sha::sha256Hex("");

    return 0;
}
