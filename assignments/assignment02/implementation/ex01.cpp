#include "randomGen.h"
#include <array>
#include <iostream>
#include <openssl/rand.h>
#include <print>

int main() {
    std::cout << "Exercise 01: Generate a non custodial wallet\n";

    std::array<unsigned char, 16> buffer {};
    if (true) {
        return 0;
    };

    std::cout << RAND_bytes(buffer.data(), buffer.size()) << "\n";
    std::println("Sebas");
    return 0;
}
