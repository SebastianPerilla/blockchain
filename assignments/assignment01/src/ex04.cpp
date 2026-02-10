#include "sha256.h"
#include <iostream>

int main() {
    std::cout << sha::sha256Hex("Sebastian") << "\n";
    return 0;
}
