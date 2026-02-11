#include "sha256.h"
#include <iostream>
#include <iterator>
#include <random>
#include <sstream>
#include <unordered_map>
#include <vector>

/*
 * For this exercise compute three partial collisions using SHA256. Find three ASCII strings
 * starting with "bitcoin" (i.e. 'bitcoin0', 'bitcoin!0b1', 'bitcoinCASH', etc) that when hashed with SHA256,
 * produce a digest starting with the bytes '0xcafe', '0xfaded', '0xdecade', in this order.
 *
 * Expected output: a text file 'solutions/exercise06.txt' the three strings separated by commas (bitcoin0, bitcoin1,
 * bitcoin2).
 *
 *
 * Approach: We could technically try to find collisions in the example of exercise 3, where we can randomly try and the
 * probability that they collide (even partially will be increased dramatically.) Given this we can just brute force the
 * matches until the solution is found? (lets try this)
 *
 */

// Random Function
namespace rando {
    std::mt19937 gen { std::random_device {}() };

    uint32_t randomU32() {
        static std::uniform_int_distribution<uint32_t> dist(0, std::numeric_limits<uint32_t>::max());
        return dist(gen);
    }
} // namespace rando

std::string numToHex(const uint32_t num) {
    std::stringstream stream;
    stream << std::hex << num;
    std::string hexResult { stream.str() };
    return hexResult;
}

int main() {
    std::cout << "Exercise 4: SHA256 Hashes\n";

    std::vector<std::string> startStrings { "cafe", "faded", "decade" };

    int count { 0 };
    while (true) {
        uint32_t randNum { rando::randomU32() };
        std::string hex { sha::sha256Hex("bitcoin" + numToHex(randNum)) };

        if (std::empty(startStrings)) {
            break;
        }

        if (hex.starts_with(startStrings.back())) {
            std::cout << "Hex: " << hex << " maps to: " << "bitcoin" + numToHex(randNum) << "\n";
            startStrings.pop_back();
        }
        ++count;
    }
    std::cout << "Sampled: " << count << " numbers in total.\n";
    std::cout << "bitcoin970578a3 maps to: " << sha::sha256Hex("bitcoin970578a3") << "\n";
    std::cout << "bitcoin970578a3 maps to: " << sha::sha256Hex("bitcoin103cd13f") << "\n";
    std::cout << "bitcoin970578a3 maps to: " << sha::sha256Hex("bitcoin802d07b0") << "\n";
    //
}
