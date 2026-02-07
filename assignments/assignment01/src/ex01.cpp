

/*
    Calculate two different strings that will hash to the same value. Both strings should be composed of ASCII
   characters and be 8 characters long

    Expected Output: "submissions/exercise01.txt" with both strings, separated by a comma

    We call this a collision attack, If its easy to find collisions for a hash function, it cant be trusted as a unique
   fingerprint of data, i.e., we cant use digests to identify or commit to data.

*/

/*

    Approach: Since we are brute forcing this, we could try to increase the char values within the string the string
until we find a valid match to the hash.

    If we think about this logically, it goes like this:
    1. The String "Sebastian" is provided
    2. Then we take that string, and shift each character by a certain amount in this case:
        shift  = (i % 4) * 8
    3. This is done in a loop for every character in the string, and then if
       there are not an even number of char's that have been encoded into hexadecimal
       we can then add them in, for example: (i.e., the string "Sebastian" results in the hash: b114e,
       which is 5 characters but there should be a total of 000 more zero's at the end to make it be a 32-bit result)

    If we want to brute force this, we can just do all of these steps in reverse and loop until we find a valid hash:

    1. Start with an empty set of hexadecimal values at 0000 0000 (32 bits)
    2. Increment the rightmost char by 1, to 0000 0001, then we can try converting
       this from a hex value to a char
    3. Then we want to reverse the hashing algorithm of "doing an XOR and shifting the character value back"
    4.

    However we can also just calculate by hand the results and show them hash correctly, for example we can look at the
hash for "Sebastian" which would result in the following:
        Sebastian
        cqotc`dtN
                                             N
               t         d         `         c
               t         o         q         c
    Bits = 0000 0000 0000 1011 0001 0001 0100 1110
                     0110 1111
                     0110 1111 o 0111 0001 q    0110 0011 c
                     0110 0100 d    0110 1110 `            0000 0000 c 0100 1110 N

    All we gotta do is add up these numbers, and then find another string of the same length that outputs the same total
result and it should hash to the same value: in this case this equals 494, if we then choose another set of letters such
as Sea`t S : 01010011 = 83 e : 01100101 = 101 a : 01100001 = 97 a : 01100001 = 97 t : 01110100 = 116
*/

#include <iostream>

// No Brute Forcing here, just two strings that hash to the same value
int main() {
    std::cout << "Exercise 1: xor32Hash Solution" << "\n";

    return 0;
}
