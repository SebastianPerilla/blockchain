#include "hash0.h"
#include "hash1.h"
#include "sha256.h"
#include <iostream>

int main() {
    // Exercise 1: Hash Collision
    std::cout << "Exercise 1: xor32Hash Solution" << "\n";
    std::cout << "Hash for Sebastian: " << hash0::xor32Hash("Sebastian") << "\n";
    std::cout << "Hash for cqotc`dtN: " << hash0::xor32Hash("cqotc`dtN") << "\n\n";

    // Exercise 2: Find the exact hash
    std::cout << "Exercise 2: Find the exact hash of 0x1b575451\n";
    std::cout << "Solution: 14'+``p0\n";
    std::cout << "Hash: " << hash0::xor32Hash("14'+``p0") << "\n\n";

    // Exercise 3: Brute Force
    std::cout << "Exercise 3: Brute Force two strings that share the same hash\n";
    std::cout << "Some of the strings found: \n" << "0xcb0fbecd\t" << "0xfdc1e00" << "\n";
    std::cout << "cb0fbecd hashes to:" << hash1::simpleHash("cb0fbecd") << "\n";
    std::cout << "fdc1e00 hashes to:" << hash1::simpleHash("fdc1e00") << "\n\n";

    // Exercise 4: SHA256 Find hashes starting with "0xcafe", "0xfaded", and "0xdecade"
    std::cout << "Exercise 4: SHA256 Find hashes starting with 0xcafe, 0xfaded, and 0xdecade\n";
    std::cout << "bitcoin970578a3 maps to: " << sha::sha256Hex("bitcoin970578a3") << "\n";
    std::cout << "bitcoin802d07b0 maps to: " << sha::sha256Hex("bitcoin802d07b0") << "\n";
    std::cout << "bitcoin103cd13f maps to: " << sha::sha256Hex("bitcoin103cd13f") << "\n\n";

    return 0;
}
