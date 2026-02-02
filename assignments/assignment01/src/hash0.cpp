#include <string>

std::string xor32Hash(std::string str) {
    int hash { 0 };
    for (int i { 0 }; i < str.size(); ++i) {
        int shift { (i % 4) * 8 };
        int c { static_cast<char>(str[i]) };
        hash ^= (c << shift);
    }
    return str;
}
