

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
    3. This is done in a loop for every character in the string, and then if there are not an even number of char's that
have been encoded into hexadecimal we can then add them in, for example: (i.e., the string "Sebastian" results in the
hash: b114e, which is 5 characters but there should be a total of 000 more zero's at the end to make it be a 32-bit
result)

    If we want to brute force this, we can just do all of these steps in reverse and loop until we find a valid hash:

    1. Start with an empty set of hexadecimal values at 0000 0000 (32 bits)
    2. Increment the rightmost char by 1, to 0000 0001, then we can try converting
       this from a hex value to a char
    3. Then we want to reverse the hashing algorithm of "doing an XOR and shifting the character value back"
    4.
*/

#include <iostream>
#include <string>

void convertToString(std::string hexValue) {}

int tryHashing(int hex) {
    int shiftBack { hex };

    return 0;
}

int findCollision() { return 0; }

int main() {
    std::cout << "Exercise 1: xor32Hash Solution" << "\n";

    return 0;
}
