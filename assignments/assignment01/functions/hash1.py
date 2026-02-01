import sys

def simple_hash(s: str) -> str:
    hash_val = 0
    for char in s:
        hash_val = ((hash_val << 5) - hash_val + ord(char)) & 0xFFFFFFFF
    return f"{hash_val:08x}"

def usage():
    print("Usage: python hash1.py <input>")
    print("Produces a 32-bit digest of <input>. The output is in hex.")
    print()
    print("Example:")
    print("$ python hash1.py bitcoin")
    print("f9e0dd1e")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        usage()
        exit()
    else:
        print(simple_hash(sys.argv[1]))
