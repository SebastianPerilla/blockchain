#include <iostream>
#include <sstream>
#include <string>

std::string xor32Hash(std::string str) {
    int32_t hash { 0 };

    for (size_t i { 0 }; i < str.size(); ++i) {
        int32_t shift = (i % 4) * 8;
        int32_t c { static_cast<char>(str[i]) };
        hash ^= (c << shift);
    }
    // Turn int into a hex decimal representation
    std::stringstream stream;
    stream << std::hex << hash;
    std::string hexResult { stream.str() };

    return hexResult;
} // Making this the 32 bit output

int main() {

    std::cout << xor32Hash("Jose") << "\n";
    return 0;
}
