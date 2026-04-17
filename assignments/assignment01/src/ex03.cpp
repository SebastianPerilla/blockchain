#include "ex03.h"
#include "hash1.h"
#include "randomGen.h"

#include <cstdint>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <unordered_map>

/*
    Calculate two different strings that will hash to the same value
    (i.e., perform collision attack).

    Both strings should be composed of ascii cahracters long and be 8 characters long (32 bits)

Approach: Given the hint of the birthday paradox that the group of 23 people have over a 50% chance that two of the
people there share the same birthday, is due to the fact that the number of possible pairs of people increase rapidly as
the group size grows meaning there are a lot more opportunities for shared birthdays.

Assuming this is the case, we could try to instead of finding two strings and checking if they create a collision, we
could try to brute for this by getting an arbitrary string and using part its output and just change some of the other
values that could result in a collision

so if we have an empty 32 bits to fill up it means that we could try to come from two ends, one from the leftmost
significant bit, and another on the rightmost and increment them little by little, until they for sure will meet in the
middle and will eventually meet at the same hash. However, assuming that we want to take advantage of the birthday
paradox we could try to generate a bunch of "random" initial values and tweak them? We could for example given they must
share some information, store the hashes of the attempted random values and then find the hashes by checking if they can
be inserted into the list of key value pairs (hash map), and if it cannot be inserted, and if it is not from the same
random value, then it MUST be a collision.
*/

namespace ex03 {
    bool check(const std::string str1, const std::string str2) {
        return hash1::simpleHash(str1) == hash1::simpleHash(str2);
    }

    std::string numToHex(const uint32_t num) {
        std::stringstream stream;
        stream << std::hex << num;
        std::string hexResult { stream.str() };
        return hexResult;
    }

    int ex03() {
        std::ofstream ex3File("./submissions/exercise03.txt");

        std::cout << "Exercise 3: Brute Force Two strings to the same hash\n";

        std::unordered_map<std::string, uint32_t> reverse;

        while (true) {
            uint32_t randNum { rando::randomU32() };
            std::string hex { hash1::simpleHash(numToHex(randNum)) };

            auto [it, inserted] = reverse.emplace(hex, randNum);

            if (!inserted && it->second != randNum) {
                std::cout << "Keys 0x" << numToHex(it->second) << " and 0x" << numToHex(randNum) << "\n= " << hex
                          << "\n";
                ex3File << numToHex(it->second) << ", " << numToHex(randNum);
                break;
            }
        }
        std::cout << "Sampled: " << reverse.size() << " numbers in total.\n";

        return 0;
    }
} // namespace ex03
