#include <bitset>
#include <iostream>
int main() {
    std::cout << (105 << 5) - 105 + 98 << "\n";
    std::cout << std::bitset<32>((105 << 5) - 105 + 98);
    return 0;
}
