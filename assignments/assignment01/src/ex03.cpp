#include "hash1.h"
#include <cstdint>
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
paradox we could try to generate a bunch of "random" initial values and tweak them? That doesnt mean there are more
pairs tho....... we could try increasing the bits from left to right as they are exponential then it means we can just
shift those very easily
*/

bool check(std::string str1, std::string str2) { return hash1::simpleHash(str1) == hash1::simpleHash(str2); }

std::string numToHex(uint32_t num) {
    std::stringstream stream;
    stream << std::hex << num;
    std::string hexResult { stream.str() };
    return hexResult;
}

int main() {
    std::cout << "Exercise 3: Brute Force Two strings to the same hash\n";
    std::cout << hash1::simpleHash("Ibhangry");
    // 4,294,967,295

    uint32_t string1 = UINT32_MAX; // start at max
    uint32_t string2 = 0;          // start at 0

    while (true) {
        std::string hex1Str = numToHex(string1);
        std::string hex2Str = numToHex(string2);

        if (check(hex1Str, hex2Str) && hex1Str != hex2Str) {
            std::cout << "Collision found!\n";
            std::cout << hex1Str << "\n" << hex2Str << "\n";
            break;
        }

        --string1;
        ++string2;
    }
    return 0;
}
