from __future__ import annotations

from pathlib import Path

from bitcoin_testnet_wallet import fetch_tx_status, fetch_utxos


ADDRESS = "myAKG9m2WUb7hVmNG9tLSXke6WRx2bFmPz"
FUNDING_TXID = None
SUBMISSION_FILE = Path("submissions/exercise02.txt")


def main() -> None:
    utxos = fetch_utxos(ADDRESS)
    if not utxos:
        raise SystemExit("No UTXOs found for the address.")

    selected = None
    if FUNDING_TXID:
        selected = next((utxo for utxo in utxos if utxo["txid"] == FUNDING_TXID), None)
        if selected is None:
            raise SystemExit("The funding txid was not found for this address.")
    else:
        selected = max(utxos, key=lambda utxo: utxo["value"])

    status = fetch_tx_status(selected["txid"])
    lines = [
        f"Public address: {ADDRESS}",
        f"Funding txid: {selected['txid']}",
        f"Amount received: {selected['value']} sats",
        f"Confirmed: {status['confirmed']}",
    ]

    submission_path = SUBMISSION_FILE
    submission_path.parent.mkdir(parents=True, exist_ok=True)
    submission_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print(f"Saved exercise 2 submission to {SUBMISSION_FILE}")


if __name__ == "__main__":
    main()
