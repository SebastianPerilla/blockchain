#include <iostream>
#include <sstream>
#include <string>

std::string simpleHash(std::string str) {
    int hashVal { 0 };
    for (auto &x : str) {
        hashVal = ((hashVal << 5) - hashVal + static_cast<char>(x));
    }
    // Turn int into a hex decimal representation
    std::stringstream stream;
    stream << std::hex << hashVal;
    std::string hexResult { stream.str() };
    return hexResult;
}

int main() {
    std::cout << simpleHash("sebas");
    return 0;
}
