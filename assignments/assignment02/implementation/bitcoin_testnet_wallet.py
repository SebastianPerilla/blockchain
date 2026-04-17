from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils


SECP256K1_ORDER = int(
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141", 16
)
BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
WORDLIST_PATH = Path(__file__).with_name("bip39_english.txt")
BLOCKSTREAM_TESTNET_API = "https://blockstream.info/testnet/api"


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def hash256(data: bytes) -> bytes:
    return sha256(sha256(data))


def ripemd160(data: bytes) -> bytes:
    return hashlib.new("ripemd160", data).digest()


def hash160(data: bytes) -> bytes:
    return ripemd160(sha256(data))


def hmac_sha512(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha512).digest()


def int_to_bytes(value: int, length: int) -> bytes:
    return value.to_bytes(length, "big")


def little_endian_uint32(value: int) -> bytes:
    return value.to_bytes(4, "little")


def little_endian_uint64(value: int) -> bytes:
    return value.to_bytes(8, "little")


def encode_varint(value: int) -> bytes:
    if value < 0xFD:
        return bytes([value])
    if value <= 0xFFFF:
        return b"\xfd" + value.to_bytes(2, "little")
    if value <= 0xFFFFFFFF:
        return b"\xfe" + value.to_bytes(4, "little")
    return b"\xff" + value.to_bytes(8, "little")


def base58_encode(data: bytes) -> str:
    zeros = len(data) - len(data.lstrip(b"\x00"))
    number = int.from_bytes(data, "big")
    encoded = ""
    while number:
        number, remainder = divmod(number, 58)
        encoded = BASE58_ALPHABET[remainder] + encoded
    return ("1" * zeros) + (encoded or "")


def base58check_encode(version: bytes, payload: bytes) -> str:
    body = version + payload
    checksum = hash256(body)[:4]
    return base58_encode(body + checksum)


def base58_decode(data: str) -> bytes:
    number = 0
    for char in data:
        number = number * 58 + BASE58_ALPHABET.index(char)
    full = number.to_bytes((number.bit_length() + 7) // 8, "big")
    zeros = len(data) - len(data.lstrip("1"))
    return (b"\x00" * zeros) + full


def base58check_decode(data: str) -> bytes:
    decoded = base58_decode(data)
    body, checksum = decoded[:-4], decoded[-4:]
    if hash256(body)[:4] != checksum:
        raise ValueError("Invalid Base58Check checksum")
    return body


def load_wordlist() -> list[str]:
    words = WORDLIST_PATH.read_text(encoding="utf-8").splitlines()
    if len(words) != 2048:
        raise ValueError(f"Expected 2048 BIP39 words, found {len(words)}")
    return words


def generate_mnemonic(strength_bits: int = 128) -> str:
    if strength_bits not in {128, 160, 192, 224, 256}:
        raise ValueError("BIP39 entropy must be 128, 160, 192, 224, or 256 bits")

    entropy = secrets.token_bytes(strength_bits // 8)
    checksum_length = strength_bits // 32
    checksum = bin(int.from_bytes(sha256(entropy), "big"))[2:].zfill(256)[:checksum_length]
    entropy_bits = bin(int.from_bytes(entropy, "big"))[2:].zfill(strength_bits)
    bitstream = entropy_bits + checksum
    words = load_wordlist()
    indices = [int(bitstream[i : i + 11], 2) for i in range(0, len(bitstream), 11)]
    return " ".join(words[index] for index in indices)


def mnemonic_to_seed(mnemonic: str, passphrase: str = "") -> bytes:
    salt = ("mnemonic" + passphrase).encode("utf-8")
    return hashlib.pbkdf2_hmac(
        "sha512",
        mnemonic.encode("utf-8"),
        salt,
        2048,
        dklen=64,
    )


def private_key_to_public_key(private_key: bytes) -> bytes:
    private_value = int.from_bytes(private_key, "big")
    signing_key = ec.derive_private_key(private_value, ec.SECP256K1())
    public_numbers = signing_key.public_key().public_numbers()
    prefix = b"\x02" if public_numbers.y % 2 == 0 else b"\x03"
    return prefix + int_to_bytes(public_numbers.x, 32)


def sign_digest(private_key: bytes, digest: bytes) -> bytes:
    private_value = int.from_bytes(private_key, "big")
    signing_key = ec.derive_private_key(private_value, ec.SECP256K1())
    der = signing_key.sign(digest, ec.ECDSA(utils.Prehashed(hashes.SHA256())))
    r, s = utils.decode_dss_signature(der)
    if s > SECP256K1_ORDER // 2:
        s = SECP256K1_ORDER - s
    return utils.encode_dss_signature(r, s)


def pubkey_hash_to_p2pkh_address(pubkey_hash: bytes, testnet: bool = True) -> str:
    version = b"\x6f" if testnet else b"\x00"
    return base58check_encode(version, pubkey_hash)


def public_key_to_p2pkh_address(public_key: bytes, testnet: bool = True) -> str:
    return pubkey_hash_to_p2pkh_address(hash160(public_key), testnet=testnet)


def address_to_pubkey_hash(address: str) -> bytes:
    decoded = base58check_decode(address)
    version, payload = decoded[:1], decoded[1:]
    if version not in {b"\x6f", b"\x00"}:
        raise ValueError("Unsupported address version")
    if len(payload) != 20:
        raise ValueError("Unexpected payload length")
    return payload


def p2pkh_script_pubkey(address: str) -> bytes:
    pubkey_hash = address_to_pubkey_hash(address)
    return b"\x76\xa9\x14" + pubkey_hash + b"\x88\xac"


@dataclass(frozen=True)
class BIP32Node:
    private_key: bytes
    chain_code: bytes
    depth: int
    index: int
    parent_fingerprint: bytes
    testnet: bool = True

    @classmethod
    def from_seed(cls, seed: bytes, testnet: bool = True) -> "BIP32Node":
        i = hmac_sha512(b"Bitcoin seed", seed)
        return cls(
            private_key=i[:32],
            chain_code=i[32:],
            depth=0,
            index=0,
            parent_fingerprint=b"\x00\x00\x00\x00",
            testnet=testnet,
        )

    @property
    def public_key(self) -> bytes:
        return private_key_to_public_key(self.private_key)

    @property
    def fingerprint(self) -> bytes:
        return hash160(self.public_key)[:4]

    @property
    def address(self) -> str:
        return public_key_to_p2pkh_address(self.public_key, testnet=self.testnet)

    def child(self, index: int, hardened: bool = False) -> "BIP32Node":
        if index < 0 or index >= 2**31:
            raise ValueError("Child index out of range")

        child_index = index + 2**31 if hardened else index
        if hardened:
            data = b"\x00" + self.private_key + int_to_bytes(child_index, 4)
        else:
            data = self.public_key + int_to_bytes(child_index, 4)

        i = hmac_sha512(self.chain_code, data)
        child_secret = (int.from_bytes(i[:32], "big") + int.from_bytes(self.private_key, "big")) % SECP256K1_ORDER
        if child_secret == 0:
            raise ValueError("Derived invalid child key")

        return BIP32Node(
            private_key=int_to_bytes(child_secret, 32),
            chain_code=i[32:],
            depth=self.depth + 1,
            index=child_index,
            parent_fingerprint=self.fingerprint,
            testnet=self.testnet,
        )

    def derive_path(self, path: str) -> "BIP32Node":
        if path in {"m", "M"}:
            return self
        current = self
        parts = path.split("/")
        if parts[0] not in {"m", "M"}:
            raise ValueError("Derivation path must start with m/")
        for part in parts[1:]:
            hardened = part.endswith("'")
            index_str = part[:-1] if hardened else part
            current = current.child(int(index_str), hardened=hardened)
        return current


def derive_receive_addresses(mnemonic: str, count: int, start_index: int = 0) -> list[dict[str, Any]]:
    seed = mnemonic_to_seed(mnemonic)
    root = BIP32Node.from_seed(seed, testnet=True)
    account = root.derive_path("m/44'/1'/0'/0")
    addresses = []
    for index in range(start_index, start_index + count):
        node = account.child(index)
        addresses.append(
            {
                "index": index,
                "path": f"m/44'/1'/0'/0/{index}",
                "address": node.address,
                "public_key": node.public_key.hex(),
                "private_key_hex": node.private_key.hex(),
            }
        )
    return addresses


def save_wallet(wallet_path: Path, mnemonic: str, addresses: list[dict[str, Any]]) -> None:
    wallet_path.parent.mkdir(parents=True, exist_ok=True)
    wallet_path.write_text(
        json.dumps(
            {
                "mnemonic": mnemonic,
                "derivation_path_template": "m/44'/1'/0'/0/i",
                "addresses": addresses,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def load_wallet(wallet_path: Path) -> dict[str, Any]:
    return json.loads(wallet_path.read_text(encoding="utf-8"))


def serialize_input(txin: dict[str, Any]) -> bytes:
    return (
        bytes.fromhex(txin["txid"])[::-1]
        + txin["vout"].to_bytes(4, "little")
        + encode_varint(len(txin["script_sig"]))
        + txin["script_sig"]
        + txin["sequence"].to_bytes(4, "little")
    )


def serialize_output(txout: dict[str, Any]) -> bytes:
    return (
        little_endian_uint64(txout["value"])
        + encode_varint(len(txout["script_pubkey"]))
        + txout["script_pubkey"]
    )


def serialize_transaction(txins: list[dict[str, Any]], txouts: list[dict[str, Any]], locktime: int = 0) -> bytes:
    raw = bytearray()
    raw.extend(little_endian_uint32(1))
    raw.extend(encode_varint(len(txins)))
    for txin in txins:
        raw.extend(serialize_input(txin))
    raw.extend(encode_varint(len(txouts)))
    for txout in txouts:
        raw.extend(serialize_output(txout))
    raw.extend(little_endian_uint32(locktime))
    return bytes(raw)


def legacy_sighash_preimage(
    txins: list[dict[str, Any]],
    txouts: list[dict[str, Any]],
    signing_index: int,
    script_code: bytes,
    sighash_type: int = 0x01,
) -> bytes:
    signing_txins = []
    for index, txin in enumerate(txins):
        signing_txins.append(
            {
                **txin,
                "script_sig": script_code if index == signing_index else b"",
            }
        )
    return serialize_transaction(signing_txins, txouts) + little_endian_uint32(sighash_type)


def create_signed_p2pkh_transaction(
    utxos: list[dict[str, Any]],
    sender_private_key_hex: str,
    sender_address: str,
    recipient_address: str,
    amount_sats: int,
    fee_sats: int,
    change_address: str | None = None,
) -> dict[str, Any]:
    total_needed = amount_sats + fee_sats
    selected: list[dict[str, Any]] = []
    selected_total = 0
    for utxo in sorted(utxos, key=lambda item: item["value"]):
        selected.append(utxo)
        selected_total += utxo["value"]
        if selected_total >= total_needed:
            break

    if selected_total < total_needed:
        raise ValueError("Not enough confirmed/unconfirmed funds to build the transaction")

    txins = [
        {
            "txid": utxo["txid"],
            "vout": utxo["vout"],
            "script_sig": b"",
            "sequence": 0xFFFFFFFF,
        }
        for utxo in selected
    ]

    txouts = [
        {
            "value": amount_sats,
            "script_pubkey": p2pkh_script_pubkey(recipient_address),
        }
    ]

    change_value = selected_total - total_needed
    if change_value > 0:
        txouts.append(
            {
                "value": change_value,
                "script_pubkey": p2pkh_script_pubkey(change_address or sender_address),
            }
        )

    private_key = bytes.fromhex(sender_private_key_hex)
    public_key = private_key_to_public_key(private_key)
    script_code = p2pkh_script_pubkey(sender_address)

    for index, _ in enumerate(txins):
        preimage = legacy_sighash_preimage(txins, txouts, index, script_code)
        digest = hash256(preimage)
        signature = sign_digest(private_key, digest) + b"\x01"
        script_sig = (
            encode_varint(len(signature))
            + signature
            + encode_varint(len(public_key))
            + public_key
        )
        txins[index]["script_sig"] = script_sig

    raw_tx = serialize_transaction(txins, txouts)
    return {
        "hex": raw_tx.hex(),
        "txid": hash256(raw_tx)[::-1].hex(),
        "selected_utxos": selected,
        "input_total": selected_total,
        "change": change_value,
    }


def blockstream_get(path: str) -> Any:
    response = requests.get(f"{BLOCKSTREAM_TESTNET_API}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


def blockstream_post(path: str, payload: str) -> str:
    response = requests.post(
        f"{BLOCKSTREAM_TESTNET_API}{path}",
        data=payload,
        headers={"Content-Type": "text/plain"},
        timeout=30,
    )
    response.raise_for_status()
    return response.text.strip()


def fetch_utxos(address: str) -> list[dict[str, Any]]:
    return blockstream_get(f"/address/{address}/utxo")


def fetch_tx_status(txid: str) -> dict[str, Any]:
    return blockstream_get(f"/tx/{txid}/status")


def broadcast_transaction(raw_tx_hex: str) -> str:
    return blockstream_post("/tx", raw_tx_hex)
