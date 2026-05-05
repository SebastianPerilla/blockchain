"""
EventTicket dApp – Streamlit Frontend (ERC-721 upgrade)
=========================================================
Connects to a local Hardhat node (or Sepolia) and lets users interact
with the EventTicket ERC-721 smart contract.

How to run
----------
1.  npx hardhat node                                        # terminal 1
2.  npx hardhat run scripts/deploy.ts --network localhost   # deploy
3.  streamlit run app/app.py                                # terminal 2

What changed vs the Assignment-3 TicketManager app
----------------------------------------------------
• Ownership comes from ERC-721: ownerOf(tokenId) is the source of truth.
  The old contract kept a _userTickets mapping; now we call
  tokenOfOwnerByIndex() from ERC721Enumerable to enumerate a wallet's NFTs.

• Transfers use ERC-721: any ticket can be transferred with the standard
  safeTransferFrom().  The old contract had a custom transferTicket().

• On-chain metadata: tokenURI() returns a base64-encoded JSON object for
  every ticket.  The app decodes and displays it.

• Resale uses approve-pattern: listForResale() internally approves the
  contract address; buyResaleTicket() executes the transfer.

• The smart contract code is significantly shorter: all ownership bookkeeping
  (who holds what token) is handled by OZ ERC-721, not by hand-rolled mappings.
"""

import base64
import json
import os
import pathlib

import streamlit as st
from web3 import Web3
from web3.exceptions import ContractLogicError

# ─── Config ──────────────────────────────────────────────────────────────────

_HERE     = pathlib.Path(__file__).parent
_ROOT     = _HERE.parent
ARTIFACT  = _ROOT / "artifacts" / "contracts" / "EventTicket.sol" / "EventTicket.json"
ADDR_FILE = _HERE / "deployment.json"

NODE_URL = os.getenv("SEPOLIA_RPC_URL", "http://127.0.0.1:8545")

# Hardhat default test accounts for local development
ACCOUNTS = [
    {
        "label":   "Account 0 (Admin / Deployer)",
        "address": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
        "key":     "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    },
    {
        "label":   "Account 1 — Alice",
        "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        "key":     "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
    },
    {
        "label":   "Account 2 — Bob",
        "address": "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
        "key":     "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
    },
    {
        "label":   "Account 3 — Carol",
        "address": "0x90F79bf6EB2c4f870365E785982E1f101E93b906",
        "key":     "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",
    },
]

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _eth(wei: int) -> str:
    return f"{Web3.from_wei(wei, 'ether'):.4f} ETH"


def _revert_msg(err: Exception) -> str:
    msg = str(err)
    if "execution reverted" in msg:
        try:
            start = msg.index("execution reverted:") + len("execution reverted:")
            return msg[start:].split('"')[0].strip()
        except ValueError:
            return "Transaction reverted."
    return msg


def decode_token_uri(uri: str) -> dict:
    """Decode a base64 data URI and return the JSON metadata."""
    prefix = "data:application/json;base64,"
    if uri.startswith(prefix):
        raw = base64.b64decode(uri[len(prefix):]).decode("utf-8")
        return json.loads(raw)
    return {}


@st.cache_resource
def get_w3() -> Web3:
    return Web3(Web3.HTTPProvider(NODE_URL))


def load_abi() -> list | None:
    if not ARTIFACT.exists():
        return None
    return json.loads(ARTIFACT.read_text())["abi"]


def load_address() -> str | None:
    if not ADDR_FILE.exists():
        return None
    data = json.loads(ADDR_FILE.read_text())
    addr = data.get("address", "")
    return addr if addr and addr != "FILL_IN_AFTER_DEPLOY" else None


def get_contract(w3: Web3, abi: list, address: str):
    return w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)


def send_tx(w3: Web3, account: dict, fn, value_wei: int = 0):
    """Build, sign and send a transaction; auto-detect EIP-1559 vs legacy gas."""
    nonce  = w3.eth.get_transaction_count(account["address"])
    params = {
        "from":    account["address"],
        "value":   value_wei,
        "gas":     500_000,
        "nonce":   nonce,
        "chainId": w3.eth.chain_id,
    }
    latest = w3.eth.get_block("latest")
    if "baseFeePerGas" in latest:
        tip = w3.to_wei(2, "gwei")
        params["maxFeePerGas"]         = latest["baseFeePerGas"] * 2 + tip
        params["maxPriorityFeePerGas"] = tip
    else:
        params["gasPrice"] = w3.eth.gas_price

    tx      = fn.build_transaction(params)
    signed  = w3.eth.account.sign_transaction(tx, account["key"])
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    return w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

# ─── On-chain data fetchers ───────────────────────────────────────────────────

def fetch_events(contract) -> list[dict]:
    count = contract.functions.eventCount().call()
    result = []
    for i in range(1, count + 1):
        ev = contract.functions.events(i).call()
        result.append({
            "id":           i,
            "name":         ev[0],
            "date":         ev[1],
            "venue":        ev[2],
            "price":        ev[3],
            "totalTickets": ev[4],
            "ticketsSold":  ev[5],
            "active":       ev[6],
        })
    return result


def fetch_my_tickets(contract, address: str) -> list[dict]:
    """Use ERC721Enumerable to enumerate all tokens owned by address."""
    balance = contract.functions.balanceOf(address).call()
    result  = []
    for i in range(balance):
        token_id = contract.functions.tokenOfOwnerByIndex(address, i).call()
        event_id, seat, _ = contract.functions.getTicketInfo(token_id).call()
        ev = contract.functions.events(event_id).call()
        resale = contract.functions.resalePrice(token_id).call()
        uri    = contract.functions.tokenURI(token_id).call()
        meta   = decode_token_uri(uri)
        result.append({
            "tokenId":    token_id,
            "eventId":    event_id,
            "seat":       seat,
            "eventName":  ev[0],
            "eventDate":  ev[1],
            "eventVenue": ev[2],
            "resale":     resale,
            "meta":       meta,
        })
    return result


def fetch_resale_tickets(contract) -> list[dict]:
    """Scan all minted tokens for active resale listings."""
    total   = contract.functions.totalSupply().call()
    result  = []
    for i in range(1, total + 1):
        price = contract.functions.resalePrice(i).call()
        if price > 0:
            event_id, seat, seller = contract.functions.getTicketInfo(i).call()
            ev = contract.functions.events(event_id).call()
            result.append({
                "tokenId":    i,
                "eventId":    event_id,
                "seat":       seat,
                "seller":     seller,
                "price":      price,
                "eventName":  ev[0],
                "eventDate":  ev[1],
                "eventVenue": ev[2],
            })
    return result

# ─── Main app ─────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(page_title="EventTicket NFT", page_icon="🎟️", layout="wide")

    w3   = get_w3()
    abi  = load_abi()
    addr = load_address()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.title("🎟️ EventTicket NFT")
        st.divider()

        use_custom = st.checkbox("Use custom private key (Sepolia / MetaMask)")
        if use_custom:
            custom_key = st.text_input("Private key", type="password", placeholder="0x…")
            if custom_key:
                try:
                    _acc = w3.eth.account.from_key(custom_key)
                    current_acc = {"label": "Custom wallet", "address": _acc.address, "key": custom_key}
                    is_admin = False  # unknown without checking on-chain
                except Exception:
                    st.error("Invalid private key.")
                    current_acc = ACCOUNTS[0]
                    is_admin = True
            else:
                current_acc = ACCOUNTS[0]
                is_admin = True
        else:
            acc_labels   = [a["label"] for a in ACCOUNTS]
            selected_lbl = st.selectbox("Select account", acc_labels)
            current_acc  = next(a for a in ACCOUNTS if a["label"] == selected_lbl)
            is_admin      = current_acc["address"] == ACCOUNTS[0]["address"]

        st.divider()
        connected = w3.is_connected()
        if connected:
            bal = w3.eth.get_balance(current_acc["address"])
            st.caption(f"Address: `{current_acc['address'][:12]}…`")
            st.caption(f"Balance: {_eth(bal)}")
            if addr:
                st.caption(f"Contract: `{addr[:12]}…`")
        else:
            st.error("Cannot connect to node.\nRun: `npx hardhat node`")

    st.title("🎟️ Event Ticket Booking (ERC-721 NFT)")
    st.caption("Tickets are ERC-721 NFTs — ownership lives on-chain.")

    if not connected:
        st.error("Not connected to node.")
        st.stop()

    if abi is None:
        st.error("ABI not found. Run `npx hardhat compile` first.")
        st.stop()

    if addr is None:
        st.warning("Contract not deployed yet. Run `npm run deploy:local`.")
        st.stop()

    contract  = get_contract(w3, abi, addr)

    # Check on-chain if connected wallet is owner (for custom wallets too)
    try:
        on_chain_owner = contract.functions.owner().call()
        is_admin = current_acc["address"].lower() == on_chain_owner.lower()
    except Exception:
        pass

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_names = ["Browse Events", "My Tickets", "Resale Market"]
    if is_admin:
        tab_names.append("Admin Panel")
    tabs = st.tabs(tab_names)

    t_events  = tabs[0]
    t_mine    = tabs[1]
    t_resale  = tabs[2]
    t_admin   = tabs[3] if is_admin else None

    # ── Browse Events ─────────────────────────────────────────────────────────
    with t_events:
        st.header("Available Events")
        events = [e for e in fetch_events(contract) if e["active"]]
        if not events:
            st.info("No active events on-chain yet.")
        for ev in events:
            avail = ev["totalTickets"] - ev["ticketsSold"]
            with st.expander(f"**{ev['name']}** — {ev['date']}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**Venue:** {ev['venue']}")
                    st.write(f"**Date:** {ev['date']}")
                    st.write(f"**Price:** {_eth(ev['price'])}")
                with c2:
                    st.write(f"**Available:** {avail} / {ev['totalTickets']}")
                    if ev["totalTickets"] > 0:
                        st.progress(ev["ticketsSold"] / ev["totalTickets"])

                if not is_admin:
                    if avail > 0:
                        if st.button(
                            f"Buy NFT ticket — {_eth(ev['price'])}",
                            key=f"buy_{ev['id']}",
                        ):
                            with st.spinner("Minting NFT ticket…"):
                                try:
                                    receipt = send_tx(
                                        w3, current_acc,
                                        contract.functions.buyTicket(ev["id"]),
                                        value_wei=ev["price"],
                                    )
                                    if receipt.status == 1:
                                        st.success("NFT ticket minted to your wallet!")
                                        st.rerun()
                                    else:
                                        st.error("Transaction failed.")
                                except (ContractLogicError, Exception) as e:
                                    st.error(_revert_msg(e))
                    else:
                        st.warning("Sold out")

    # ── My Tickets ────────────────────────────────────────────────────────────
    with t_mine:
        st.header("My NFT Tickets")
        st.caption(
            "Your tickets are ERC-721 tokens.  Ownership is read from the "
            "contract via `tokenOfOwnerByIndex` — no separate off-chain index needed."
        )

        try:
            my_tickets = fetch_my_tickets(contract, current_acc["address"])
        except Exception as e:
            st.error(f"Could not load tickets: {e}")
            my_tickets = []

        if not my_tickets:
            st.info("You don't own any NFT tickets yet.")

        for tk in my_tickets:
            listed = tk["resale"] > 0
            label  = (
                f"🎟️ Token #{tk['tokenId']} — {tk['eventName']}  "
                + ("🔴 Listed for Resale" if listed else f"Seat #{tk['seat']}")
            )
            with st.expander(label):
                meta_attrs = {
                    a["trait_type"]: a["value"]
                    for a in tk["meta"].get("attributes", [])
                }
                st.write(
                    f"**Event:** {tk['eventName']}  |  "
                    f"**Date:** {tk['eventDate']}  |  "
                    f"**Venue:** {tk['eventVenue']}  |  "
                    f"**Seat:** {tk['seat']}"
                )
                st.caption(f"Token ID: {tk['tokenId']}  |  On-chain metadata ✓")

                if listed:
                    st.write(f"**Listed at:** {_eth(tk['resale'])}")
                    if st.button("Cancel resale listing", key=f"cancel_{tk['tokenId']}"):
                        with st.spinner("Cancelling…"):
                            try:
                                receipt = send_tx(
                                    w3, current_acc,
                                    contract.functions.cancelResaleListing(tk["tokenId"]),
                                )
                                if receipt.status == 1:
                                    st.success("Listing cancelled. Approval revoked.")
                                    st.rerun()
                            except Exception as e:
                                st.error(_revert_msg(e))
                else:
                    col_t, col_r = st.columns(2)

                    with col_t:
                        st.subheader("Direct Transfer (gift)")
                        st.caption(
                            "Uses standard ERC-721 `safeTransferFrom`. "
                            "No payment required."
                        )
                        other_accs = [
                            a for a in ACCOUNTS
                            if a["address"].lower() != current_acc["address"].lower()
                        ]
                        if other_accs:
                            to_lbl = st.selectbox(
                                "To account",
                                [a["label"] for a in other_accs],
                                key=f"to_{tk['tokenId']}",
                            )
                            to_acc = next(a for a in other_accs if a["label"] == to_lbl)
                            to_addr = to_acc["address"]
                        else:
                            to_addr = st.text_input(
                                "Recipient address", key=f"to_addr_{tk['tokenId']}"
                            )

                        if st.button("Transfer", key=f"tr_{tk['tokenId']}"):
                            with st.spinner("Transferring NFT…"):
                                try:
                                    receipt = send_tx(
                                        w3, current_acc,
                                        contract.functions.safeTransferFrom(
                                            current_acc["address"],
                                            Web3.to_checksum_address(to_addr),
                                            tk["tokenId"],
                                        ),
                                    )
                                    if receipt.status == 1:
                                        st.success("NFT transferred!")
                                        st.rerun()
                                except Exception as e:
                                    st.error(_revert_msg(e))

                    with col_r:
                        st.subheader("List for Resale")
                        st.caption(
                            "Approves this contract to transfer on sale. "
                            "Buyer pays you directly in ETH."
                        )
                        price_eth = st.number_input(
                            "Resale price (ETH)",
                            min_value=0.0001, value=0.02,
                            step=0.005, format="%.4f",
                            key=f"rp_{tk['tokenId']}",
                        )
                        if st.button("List for resale", key=f"lr_{tk['tokenId']}"):
                            with st.spinner("Listing on resale market…"):
                                try:
                                    receipt = send_tx(
                                        w3, current_acc,
                                        contract.functions.listForResale(
                                            tk["tokenId"],
                                            Web3.to_wei(price_eth, "ether"),
                                        ),
                                    )
                                    if receipt.status == 1:
                                        st.success("Ticket listed for resale!")
                                        st.rerun()
                                except Exception as e:
                                    st.error(_revert_msg(e))

    # ── Resale Market ─────────────────────────────────────────────────────────
    with t_resale:
        st.header("Resale Market")
        st.caption(
            "Resale listings are enforced on-chain. "
            "ETH goes directly to the seller; no intermediary."
        )
        try:
            resale = fetch_resale_tickets(contract)
        except Exception as e:
            st.error(f"Could not load resale listings: {e}")
            resale = []

        if not resale:
            st.info("No tickets listed for resale on-chain.")
        for tk in resale:
            seller_label = next(
                (a["label"] for a in ACCOUNTS
                 if a["address"].lower() == tk["seller"].lower()),
                tk["seller"][:10] + "…",
            )
            with st.expander(
                f"Token #{tk['tokenId']} — {tk['eventName']} — Seat {tk['seat']} — {_eth(tk['price'])}"
            ):
                st.write(
                    f"**Event:** {tk['eventName']}  |  "
                    f"**Date:** {tk['eventDate']}  |  "
                    f"**Venue:** {tk['eventVenue']}"
                )
                st.write(f"**Seller:** {seller_label}  |  **Price:** {_eth(tk['price'])}")

                if tk["seller"].lower() != current_acc["address"].lower():
                    if st.button(
                        f"Buy for {_eth(tk['price'])}",
                        key=f"br_{tk['tokenId']}",
                    ):
                        with st.spinner("Purchasing resale ticket…"):
                            try:
                                receipt = send_tx(
                                    w3, current_acc,
                                    contract.functions.buyResaleTicket(tk["tokenId"]),
                                    value_wei=tk["price"],
                                )
                                if receipt.status == 1:
                                    st.success("NFT ticket purchased from resale!")
                                    st.rerun()
                            except Exception as e:
                                st.error(_revert_msg(e))

    # ── Admin Panel ───────────────────────────────────────────────────────────
    if is_admin and t_admin is not None:
        with t_admin:
            st.header("Admin Panel")

            st.subheader("Create New Event")
            with st.form("create_event"):
                name  = st.text_input("Event name")
                date  = st.date_input("Date")
                venue = st.text_input("Venue")
                price_eth = st.number_input(
                    "Ticket price (ETH)", min_value=0.0001, value=0.01,
                    step=0.005, format="%.4f"
                )
                total = st.number_input("Total tickets", min_value=1, value=100, step=10)

                if st.form_submit_button("Create event (mint supply)"):
                    if name and venue:
                        with st.spinner("Creating event on-chain…"):
                            try:
                                send_tx(
                                    w3, current_acc,
                                    contract.functions.createEvent(
                                        name,
                                        str(date),
                                        venue,
                                        Web3.to_wei(price_eth, "ether"),
                                        int(total),
                                    ),
                                )
                                st.success(f"Event '{name}' created on-chain!")
                                st.rerun()
                            except Exception as e:
                                st.error(_revert_msg(e))
                    else:
                        st.warning("Name and venue are required.")

            st.divider()
            st.subheader("Manage Events")
            for ev in fetch_events(contract):
                status = "Active" if ev["active"] else "Inactive"
                with st.expander(f"{ev['name']} — {status}"):
                    st.write(
                        f"**Venue:** {ev['venue']}  |  **Date:** {ev['date']}  |  "
                        f"**Price:** {_eth(ev['price'])}  |  "
                        f"**Sold:** {ev['ticketsSold']} / {ev['totalTickets']}"
                    )
                    if ev["active"]:
                        if st.button("Deactivate", key=f"deact_{ev['id']}"):
                            with st.spinner("Deactivating…"):
                                try:
                                    send_tx(
                                        w3, current_acc,
                                        contract.functions.deactivateEvent(ev["id"]),
                                    )
                                    st.success("Event deactivated.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(_revert_msg(e))


if __name__ == "__main__":
    main()
