#include "sha256.h"
#include <iostream>
#include <random>
#include <sstream>
#include <unordered_map>

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

bool check(std::string str1, std::string str2) { return sha::sha256Hex(str1) == sha::sha256Hex(str2); }

std::string numToHex(uint32_t num) {
    std::stringstream stream;
    stream << std::hex << num;
    std::string hexResult { stream.str() };
    return hexResult;
}

int main() {
    std::cout << "Exercise 3: Brute Force Two strings to the same hash\n";

    std::unordered_map<std::string, uint32_t> reverse;
    int count { 10 };
    while (true) {
        uint32_t randNum { rando::randomU32() };
        std::string hex { sha::sha256Hex(numToHex(randNum)) };

        std::cout << hex << "\n";

        if (count < 0) {
            break;
        }

        --count;

        // auto [it, inserted] = reverse.emplace(hex, randNum);
        //
        // if (!inserted && it->second != randNum) {
        //     std::cout << "Keys 0x" << numToHex(it->second) << " and 0x" << numToHex(randNum) << "\n= " << hex <<
        //     "\n"; break;
        // }
    }
    std::cout << "Sampled: " << reverse.size() << " numbers in total.\n";

    return 0;
}
