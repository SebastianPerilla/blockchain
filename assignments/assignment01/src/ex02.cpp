#include "ex02.h"
#include "hash0.h"
#include <bitset>
#include <fstream>
#include <iostream>

/*
        0         p         `         `
    0011 0000 0111 0000 0110 0000 0110 0000
        +         '          4        1
    0010 1011 0010 0111 0011 0100 0011 0001
    0000 1011 0101 0111 0101 0100 0101 0001
    0001 1011 0101 0111 0101 0100 0101 0001

    14'+n`p0
*/
namespace ex02 {

    int ex02() {
        std::ofstream ex2File("./submissions/exercise02.txt");

        ex2File << "14'+``p0";

        std::cout << "Exercise 2: Find the exact hash of 0x1b575451\n";
        std::cout << "Binary Representation: \n" << std::bitset<32>(0x1b575451) << "\n";
        std::cout << "Solution\n";
        std::cout << hash0::xor32Hash("14'+``p0") << "\n";
        std::cout << "0001 1011 0101 0111 0101 0100 0101 0001" << "\n";

        return 0;
    }
} // namespace ex02
