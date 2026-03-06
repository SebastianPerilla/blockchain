from __future__ import annotations

import json
from pathlib import Path

from bitcoin_testnet_wallet import (
    broadcast_transaction,
    create_signed_p2pkh_transaction,
    fetch_tx_status,
    fetch_utxos,
    load_wallet,
)


WALLET_A_FILE = Path("implementation/wallet_a.json")
WALLET_B_FILE = Path("implementation/wallet_b.json")
SENDER_INDEX = 0
RECIPIENT_INDEX = 0
SENDER_ADDRESS = None
RECIPIENT_ADDRESS = None
AMOUNT_TO_SEND = 12000
FEE = 1000
BROADCAST_TRANSACTION = True
SUBMISSION_FILE = Path("submissions/exercise03.txt")
RAW_TX_FILE = Path("submissions/exercise03_rawtx.json")


def find_entry(wallet: dict, address: str | None, index: int | None) -> dict:
    if address:
        match = next((item for item in wallet["addresses"] if item["address"] == address), None)
        if match is None:
            raise SystemExit(f"Address {address} was not found in the wallet file.")
        return match
    if index is None:
        index = 0
    match = next((item for item in wallet["addresses"] if item["index"] == index), None)
    if match is None:
        raise SystemExit(f"Index {index} was not found in the wallet file.")
    return match


def main() -> None:
    wallet_a = load_wallet(WALLET_A_FILE)
    wallet_b = load_wallet(WALLET_B_FILE)

    sender = find_entry(wallet_a, SENDER_ADDRESS, SENDER_INDEX)
    recipient = find_entry(wallet_b, RECIPIENT_ADDRESS, RECIPIENT_INDEX)

    utxos = fetch_utxos(sender["address"])
    if not utxos:
        raise SystemExit(f"No UTXOs found for sender address {sender['address']}.")

    signed = create_signed_p2pkh_transaction(
        utxos=utxos,
        sender_private_key_hex=sender["private_key_hex"],
        sender_address=sender["address"],
        recipient_address=recipient["address"],
        amount_sats=AMOUNT_TO_SEND,
        fee_sats=FEE,
        change_address=sender["address"],
    )

    broadcast_txid = signed["txid"]
    if BROADCAST_TRANSACTION:
        broadcast_txid = broadcast_transaction(signed["hex"])
        _ = fetch_tx_status(broadcast_txid)

    submission_lines = [
        f'Sender public address: {sender["address"]}',
        f'Recipient public address: {recipient["address"]}',
        f"Amount sent (sats): {AMOUNT_TO_SEND}",
        f"Fee (sats): {FEE}",
        f"Broadcast txid: {broadcast_txid}",
    ]

    submission_path = SUBMISSION_FILE
    submission_path.parent.mkdir(parents=True, exist_ok=True)
    submission_path.write_text("\n".join(submission_lines) + "\n", encoding="utf-8")

    raw_tx_path = RAW_TX_FILE
    raw_tx_path.write_text(
        json.dumps(
            {
                "sender": sender["address"],
                "recipient": recipient["address"],
                "amount_sats": AMOUNT_TO_SEND,
                "fee_sats": FEE,
                "raw_tx_hex": signed["hex"],
                "predicted_txid": signed["txid"],
                "selected_utxos": signed["selected_utxos"],
                "change_sats": signed["change"],
                "broadcasted": BROADCAST_TRANSACTION,
                "broadcast_txid": broadcast_txid,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print("\n".join(submission_lines))
    print(f"Saved raw transaction details to {RAW_TX_FILE}")


if __name__ == "__main__":
    main()
