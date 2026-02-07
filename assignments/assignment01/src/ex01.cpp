

/*
    Calculate two different strings that will hash to the same value. Both strings should be composed of ASCII
   characters and be 8 characters long

    Expected Output: "submissions/exercise01.txt" with both strings, separated by a comma

    We call this a collision attack, If its easy to find collisions for a hash function, it cant be trusted as a unique
   fingerprint of data, i.e., we cant use digests to identify or commit to data.

*/

/*
    1. The String "Sebastian" is provided
    2. Then we take that string, and shift each character by a certain amount in this case:
        shift  = (i % 4) * 8
    3. This is done in a loop for every character in the string, and then if
       there are not an even number of char's that have been encoded into hexadecimal
       we can then add them in, for example: (i.e., the string "Sebastian" results in the hash: b114e,
       which is 5 characters but there should be a total of 000 more zero's at the end to make it be a 32-bit result)


    We can just calculate by hand the results and show them hash correctly, for example we can look at the
hash for "Sebastian" which would result in the following:

        Sebastian = 0x 000b 114e
        cqotc`dtN = 0x 000b 114e

    This is because the shifts occur in a "wrapping" manner where they loop between shifting
    the bits by 0,8,16, and 24 before going back to looping ot 0. We can just see for example
    that by making the bits cancel out when they hit the appropriate shift length to equal the
    same hash as the original. For example:
    We know that the letters (in order), in Sebastian given this is 32 bits, both the first 'a' and
    second 'a' will xor eachother and cause the first byte to equal 0. As such as can put whatever ascii characters
    there and it will result in that byte equaling the desired result.

                                             N
               t         d         `         c
               t         o         q         c
    Bits = 0000 0000 0000 1011 0001 0001 0100 1110

    This is a collision *boom*
*/

#include "hash0.h"
#include <iostream>

// No Brute Forcing here, just two strings that hash to the same value
int main() {
    std::cout << "Exercise 1: xor32Hash Solution" << "\n";
    std::cout << "Hash for Sebastian: " << hash0::xor32Hash("Sebastian") << "\n";
    std::cout << "Hash for cqotc`dtN: " << hash0::xor32Hash("cqotc`dtN") << "\n";
    return 0;
}
