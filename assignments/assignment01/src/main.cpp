#include "hash0.cpp"
#include "hash0.h"
#include <iostream>

int main() {
    // Exercise 1: Hash Collision
    std::cout << "Exercise 1: xor32Hash Solution" << "\n";
    std::cout << "Hash for Sebastian: " << hash0::xor32Hash("Sebastian") << "\n";
    std::cout << "Hash for cqotc`dtN: " << hash0::xor32Hash("cqotc`dtN") << "\n";

    // Exercise 2: Find the exact hash
    std::cout << "Exercise 2: Find the exact hash of 0x1b575451\n";
    std::cout << "Solution: 14'+``p0\n";
    std::cout << "Hash: " << hash0::xor32Hash("14'+``p0") << "\n";

    // Exercise 3: Brute Force

    return 0;
}
