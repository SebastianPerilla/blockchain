import sys

def xor32_hash(s: str) -> str:
    h = 0
    for i, c in enumerate(s):
        shift = (i % 4) * 8
        h ^= (ord(c) << shift)
    return f"{h & 0xFFFFFFFF:08x}"  # Lower 32 bits as hex

def usage():
    print("Usage: python hash0.py <input>")
    print("Produces a 32-bit digest of <input>. The output is in hex.")
    print()
    print("Example:")
    print("$ python hash0.py bitcoin")
    print("631a000d")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        usage()
        exit()
    else:
        print(xor32_hash(sys.argv[1]))
