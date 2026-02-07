

#include <bitset>
#include <iostream>
int main() {
    int32_t c { static_cast<char>('S') };
    int16_t hash { 0 };
    int32_t shift = (1 % 4) * 8;

    hash ^= (c << shift);

    std::cout << "Shift: " << shift << "\n";
    std::cout << "Char value: " << c << "\n";
    std::cout << "Decimal Hash Value: " << hash << "\n";
    std::cout << "Bit Hash Value: " << std::bitset<16>(hash) << "\n";
    return 0;
}
