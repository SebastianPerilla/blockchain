"""
Exercise 2 — Part B: Web3 Event Ticket Booking System
Backend: Ethereum smart contract (Hardhat local node)
Frontend: Streamlit  — same layout as the Web2 version
"""
import json
import os

import streamlit as st
from web3 import Web3
from web3.exceptions import ContractLogicError

# ── Paths ──────────────────────────────────────────────────────────────────────
_HERE      = os.path.dirname(os.path.abspath(__file__))
_ROOT      = os.path.dirname(_HERE)                         # exercise-2/
_ARTIFACT  = os.path.join(
    _ROOT, "artifacts", "contracts", "TicketManager.sol", "TicketManager.json"
)
_ADDR_FILE = os.path.join(_HERE, "contract_address.txt")

# ── Hardhat default test accounts (mnemonic: test test … junk) ────────────────
ACCOUNTS = [
    {
        "label":   "Account 0 (Admin)",
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
    {
        "label":   "Account 4 — Dave",
        "address": "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65",
        "key":     "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926b",
    },
]

NODE_URL = "http://127.0.0.1:8545"


# ── Web3 / contract helpers ────────────────────────────────────────────────────

@st.cache_resource
def get_w3() -> Web3:
    return Web3(Web3.HTTPProvider(NODE_URL))


def load_abi() -> list | None:
    if not os.path.exists(_ARTIFACT):
        return None
    with open(_ARTIFACT) as f:
        return json.load(f)["abi"]


def load_address() -> str | None:
    if not os.path.exists(_ADDR_FILE):
        return None
    with open(_ADDR_FILE) as f:
        addr = f.read().strip()
    return addr if addr else None


def get_contract(w3: Web3, abi: list, address: str):
    return w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)


def send_tx(w3: Web3, account: dict, fn, value_wei: int = 0):
    """Build, sign, and send a contract function transaction."""
    nonce = w3.eth.get_transaction_count(account["address"])
    tx = fn.build_transaction({
        "from":     account["address"],
        "value":    value_wei,
        "gas":      500_000,
        "gasPrice": w3.eth.gas_price,
        "nonce":    nonce,
        "chainId":  w3.eth.chain_id,
    })
    signed   = w3.eth.account.sign_transaction(tx, account["key"])
    tx_hash  = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt  = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
    return receipt


# ── On-chain data fetchers ─────────────────────────────────────────────────────

def fetch_events(contract) -> list[dict]:
    count = contract.functions.nextEventId().call() - 1
    result = []
    for i in range(1, count + 1):
        ev = contract.functions.events(i).call()
        # (id, name, date, venue, price, totalTickets, ticketsSold, active)
        result.append({
            "id":           ev[0],
            "name":         ev[1],
            "date":         ev[2],
            "venue":        ev[3],
            "price":        ev[4],
            "totalTickets": ev[5],
            "ticketsSold":  ev[6],
            "active":       ev[7],
        })
    return result


def fetch_user_tickets(contract, address: str) -> list[dict]:
    ids = contract.functions.getUserTickets(address).call()
    result = []
    for tid in ids:
        t = contract.functions.getTicket(int(tid)).call()
        # (id, eventId, owner, forResale, resalePrice)
        ev = contract.functions.events(t[1]).call()
        result.append({
            "id":         t[0],
            "eventId":    t[1],
            "owner":      t[2],
            "forResale":  t[3],
            "resalePrice": t[4],
            "eventName":  ev[1],
            "eventDate":  ev[2],
            "eventVenue": ev[3],
        })
    return result


def fetch_resale_tickets(contract) -> list[dict]:
    count = contract.functions.nextTicketId().call() - 1
    result = []
    for tid in range(1, count + 1):
        t = contract.functions.getTicket(tid).call()
        if t[3]:  # forResale
            ev = contract.functions.events(t[1]).call()
            result.append({
                "id":         t[0],
                "eventId":    t[1],
                "owner":      t[2],
                "forResale":  t[3],
                "resalePrice": t[4],
                "eventName":  ev[1],
                "eventDate":  ev[2],
                "eventVenue": ev[3],
            })
    return result


# ── Reusable UI helpers ────────────────────────────────────────────────────────

def _badge(text: str, colour: str) -> str:
    return (
        f'<span style="background:{colour};color:white;padding:2px 8px;'
        f'border-radius:4px;font-size:0.78em;">{text}</span>'
    )


def _eth(wei: int) -> str:
    return f"{Web3.from_wei(wei, 'ether'):.4f} ETH"


def _revert_msg(err: Exception) -> str:
    msg = str(err)
    # extract Solidity revert reason when present
    if "execution reverted" in msg:
        try:
            start = msg.index("execution reverted:") + len("execution reverted:")
            return msg[start:].split('"')[0].strip()
        except ValueError:
            return "Transaction reverted."
    return msg


# ── Main app ───────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(page_title="TicketChain Web3", page_icon="🔗", layout="wide")

    w3  = get_w3()
    abi = load_abi()
    addr = load_address()

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.title("🔗 TicketChain")
        st.markdown(_badge("WEB3 — Ethereum", "#047857"), unsafe_allow_html=True)
        st.divider()

        # Account selector
        acc_labels  = [a["label"] for a in ACCOUNTS]
        selected_lbl = st.selectbox("Select account", acc_labels)
        current_acc  = next(a for a in ACCOUNTS if a["label"] == selected_lbl)
        is_admin     = current_acc["address"] == ACCOUNTS[0]["address"]

        if is_admin:
            st.success("Logged in as **Admin** (Account 0)")
        else:
            st.info(f"**{current_acc['label']}**")

        # Node / contract status
        st.divider()
        connected = w3.is_connected()
        if connected:
            balance_wei = w3.eth.get_balance(current_acc["address"])
            st.caption(f"Node: {NODE_URL}")
            st.caption(f"Balance: {_eth(balance_wei)}")
        else:
            st.error("Cannot connect to Hardhat node.\nRun: `npx hardhat node`")

        if addr:
            st.caption(f"Contract: `{addr[:10]}…`")
        else:
            st.warning("Contract not deployed yet.")

    # ── Guard rails ───────────────────────────────────────────────────────────
    st.title("🔗 Event Ticket Booking")
    st.caption("Web3 version — data lives on-chain (Hardhat local network)")

    if not connected:
        st.error("Not connected to the Hardhat local node. Start it with `npx hardhat node`.")
        st.stop()

    if abi is None:
        st.error(
            "ABI not found. Please compile the contract first:\n"
            "```\nnpx hardhat compile\n```"
        )
        st.stop()

    if addr is None:
        st.warning("Contract not deployed yet.")
        if is_admin:
            if st.button("Deploy contract now"):
                with st.spinner("Deploying…"):
                    try:
                        Contract = w3.eth.contract(abi=abi, bytecode=_load_bytecode())
                        nonce = w3.eth.get_transaction_count(current_acc["address"])
                        tx = Contract.constructor().build_transaction({
                            "from":     current_acc["address"],
                            "gas":      3_000_000,
                            "gasPrice": w3.eth.gas_price,
                            "nonce":    nonce,
                            "chainId":  w3.eth.chain_id,
                        })
                        signed  = w3.eth.account.sign_transaction(tx, current_acc["key"])
                        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                        deployed_addr = receipt.contractAddress
                        with open(_ADDR_FILE, "w") as f:
                            f.write(deployed_addr)
                        st.success(f"Contract deployed at {deployed_addr}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Deployment failed: {e}")
        else:
            st.info("Ask the admin to deploy the contract first.")
        st.stop()

    contract = get_contract(w3, abi, addr)

    # ── Tabs ─────────────────────────────────────────────────────────────────
    if is_admin:
        t_events, t_resale, t_admin = st.tabs(
            ["Browse Events", "Resale Market", "Admin Panel"]
        )
    else:
        t_events, t_mine, t_resale = st.tabs(
            ["Browse Events", "My Tickets", "Resale Market"]
        )

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
                            f"Buy ticket — {_eth(ev['price'])}",
                            key=f"buy_{ev['id']}",
                        ):
                            with st.spinner("Sending transaction…"):
                                try:
                                    send_tx(
                                        w3, current_acc,
                                        contract.functions.buyTicket(ev["id"]),
                                        value_wei=ev["price"],
                                    )
                                    st.success("Ticket purchased!")
                                    st.rerun()
                                except (ContractLogicError, Exception) as e:
                                    st.error(_revert_msg(e))
                    else:
                        st.warning("Sold out")

    # ── My Tickets ────────────────────────────────────────────────────────────
    if not is_admin:
        with t_mine:
            st.header("My Tickets")
            my_tickets = fetch_user_tickets(contract, current_acc["address"])
            if not my_tickets:
                st.info("You don't own any tickets yet.")

            for tk in my_tickets:
                label = (
                    f"Ticket #{tk['id']} — {tk['eventName']}  "
                    + ("🔴 For Resale" if tk["forResale"] else "✅ Active")
                )
                with st.expander(label):
                    st.write(
                        f"**Event:** {tk['eventName']}  |  "
                        f"**Date:** {tk['eventDate']}  |  "
                        f"**Venue:** {tk['eventVenue']}"
                    )

                    if tk["forResale"]:
                        st.write(f"**Listed at:** {_eth(tk['resalePrice'])}")
                        if st.button("Cancel resale listing", key=f"cancel_{tk['id']}"):
                            with st.spinner("Sending transaction…"):
                                try:
                                    send_tx(
                                        w3, current_acc,
                                        contract.functions.cancelResaleListing(tk["id"]),
                                    )
                                    st.success("Listing cancelled.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(_revert_msg(e))
                    else:
                        col_t, col_r = st.columns(2)

                        with col_t:
                            st.subheader("Transfer")
                            other_accs = [
                                a for a in ACCOUNTS if a["address"] != current_acc["address"]
                            ]
                            to_lbl = st.selectbox(
                                "To account",
                                [a["label"] for a in other_accs],
                                key=f"to_{tk['id']}",
                            )
                            to_acc = next(a for a in other_accs if a["label"] == to_lbl)
                            if st.button("Transfer", key=f"tr_{tk['id']}"):
                                with st.spinner("Sending transaction…"):
                                    try:
                                        send_tx(
                                            w3, current_acc,
                                            contract.functions.transferTicket(
                                                tk["id"],
                                                Web3.to_checksum_address(to_acc["address"]),
                                            ),
                                        )
                                        st.success(f"Ticket transferred to {to_lbl}!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(_revert_msg(e))

                        with col_r:
                            st.subheader("Resale")
                            price_eth = st.number_input(
                                "Price (ETH)", min_value=0.0001, value=0.02,
                                step=0.005, format="%.4f", key=f"rp_{tk['id']}"
                            )
                            if st.button("List for resale", key=f"lr_{tk['id']}"):
                                with st.spinner("Sending transaction…"):
                                    try:
                                        send_tx(
                                            w3, current_acc,
                                            contract.functions.listForResale(
                                                tk["id"],
                                                Web3.to_wei(price_eth, "ether"),
                                            ),
                                        )
                                        st.success("Ticket listed for resale!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(_revert_msg(e))

    # ── Resale Market ─────────────────────────────────────────────────────────
    with t_resale:
        st.header("Resale Market")
        resale = fetch_resale_tickets(contract)
        if not resale:
            st.info("No tickets listed for resale on-chain.")
        for tk in resale:
            seller_label = next(
                (a["label"] for a in ACCOUNTS if a["address"].lower() == tk["owner"].lower()),
                tk["owner"],
            )
            with st.expander(
                f"Ticket #{tk['id']} — {tk['eventName']} — {_eth(tk['resalePrice'])}"
            ):
                st.write(
                    f"**Event:** {tk['eventName']}  |  "
                    f"**Date:** {tk['eventDate']}  |  "
                    f"**Venue:** {tk['eventVenue']}"
                )
                st.write(f"**Seller:** {seller_label}  |  **Price:** {_eth(tk['resalePrice'])}")

                if not is_admin and tk["owner"].lower() != current_acc["address"].lower():
                    if st.button(f"Buy for {_eth(tk['resalePrice'])}", key=f"br_{tk['id']}"):
                        with st.spinner("Sending transaction…"):
                            try:
                                send_tx(
                                    w3, current_acc,
                                    contract.functions.buyResaleTicket(tk["id"]),
                                    value_wei=tk["resalePrice"],
                                )
                                st.success("Resale ticket purchased!")
                                st.rerun()
                            except Exception as e:
                                st.error(_revert_msg(e))

    # ── Admin Panel ───────────────────────────────────────────────────────────
    if is_admin:
        with t_admin:
            st.header("Admin Panel")

            st.subheader("Create New Event")
            with st.form("create_event"):
                name  = st.text_input("Event name")
                date  = st.date_input("Date")
                venue = st.text_input("Venue")
                price_eth = st.number_input(
                    "Ticket price (ETH)", min_value=0.0001, value=0.01, step=0.005, format="%.4f"
                )
                total = st.number_input("Total tickets", min_value=1, value=100, step=10)

                if st.form_submit_button("Create event"):
                    if name and venue:
                        with st.spinner("Sending transaction…"):
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
                        f"**Venue:** {ev['venue']}  |  "
                        f"**Date:** {ev['date']}  |  "
                        f"**Price:** {_eth(ev['price'])}  |  "
                        f"**Sold:** {ev['ticketsSold']} / {ev['totalTickets']}"
                    )
                    if ev["active"]:
                        if st.button("Deactivate", key=f"deact_{ev['id']}"):
                            with st.spinner("Sending transaction…"):
                                try:
                                    send_tx(
                                        w3, current_acc,
                                        contract.functions.deactivateEvent(ev["id"]),
                                    )
                                    st.success("Event deactivated.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(_revert_msg(e))


def _load_bytecode() -> str:
    if not os.path.exists(_ARTIFACT):
        raise FileNotFoundError("Run `npx hardhat compile` first.")
    with open(_ARTIFACT) as f:
        return json.load(f)["bytecode"]


if __name__ == "__main__":
    main()
