import sys
import hashlib

def usage():
    print("Usage: python sha256.py <input>")
    print("Produces the sha-2 256-bit digest of <input>. The output is in hex.")
    print()
    print("Example:")
    print("$ python sha256.py bitcoin")
    print("6b88c087247aa2f07ee1c5956b8e1a9f4c7f892a70e324f1bb3d161e05ca107b")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        usage()
        exit()
    else:
        s = sys.argv[1]
        full_hash = hashlib.sha256(s.encode('utf-8')).hexdigest()
        print(f"{full_hash}")
