from __future__ import annotations

from pathlib import Path

from bitcoin_testnet_wallet import (
    derive_receive_addresses,
    generate_mnemonic,
    load_wallet,
    save_wallet,
)


WALLET_FILE = Path("implementation/wallet_a.json")
SUBMISSION_FILE = Path("submissions/exercise01.txt")
NUMBER_OF_ADDRESSES = 5


def main() -> None:
    if WALLET_FILE.exists():
        wallet_data = load_wallet(WALLET_FILE)
        mnemonic = wallet_data["mnemonic"]
        addresses = wallet_data["addresses"]
    else:
        mnemonic = generate_mnemonic(128)
        addresses = derive_receive_addresses(mnemonic, count=NUMBER_OF_ADDRESSES)
        save_wallet(WALLET_FILE, mnemonic, addresses)

    submission_path = SUBMISSION_FILE
    submission_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["m/44'/1'/0'/0/i"]
    lines.extend(item["address"] for item in addresses[:5])
    submission_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Using wallet data from {WALLET_FILE}")
    print(f"Saved exercise 1 submission to {SUBMISSION_FILE}")
    for item in addresses:
        print(f"{item['path']}: {item['address']}")


if __name__ == "__main__":
    main()
