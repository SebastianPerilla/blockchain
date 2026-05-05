"""
LoyaltyToken dApp – Streamlit Frontend
========================================
Connects to a local Hardhat node (or Sepolia) and lets users interact
with the LoyaltyToken ERC-20 contract.

How to run
----------
1.  npx hardhat node                                        # terminal 1
2.  npx hardhat run scripts/deploy.ts --network localhost   # deploy
3.  streamlit run app/app.py                                # terminal 2

For Sepolia, set SEPOLIA_RPC_URL and PRIVATE_KEY in .env then:
    npx hardhat run scripts/deploy.ts --network sepolia

Design notes
------------
• Token amounts are stored on-chain in wei (18 decimals).  The UI converts
  to whole "points" for display but sends wei to the contract.
• All state-changing calls (mint, transfer, burn) are signed by the
  connected wallet's private key and broadcast as raw transactions.
• Event fetching uses get_logs (stateless) so the app works with both
  local Hardhat and hosted RPC providers like Infura/Alchemy.
• The admin mint panel will simply revert on-chain if the connected wallet
  is not the contract owner — no separate auth in the frontend.
"""

import json
import os
import pathlib

import streamlit as st
from web3 import Web3

# ─── Config ──────────────────────────────────────────────────────────────────

ABI_PATH        = pathlib.Path(__file__).parent / "abi.json"
DEPLOYMENT_PATH = pathlib.Path(__file__).parent / "deployment.json"
ABI             = json.loads(ABI_PATH.read_text())

ETHERSCAN_BASE = "https://sepolia.etherscan.io"

def _default_rpc() -> str:
    return os.getenv("SEPOLIA_RPC_URL", "http://127.0.0.1:8545")

def _default_address() -> str:
    if DEPLOYMENT_PATH.exists():
        data = json.loads(DEPLOYMENT_PATH.read_text())
        addr = data.get("address", "")
        if addr and addr != "FILL_IN_AFTER_DEPLOY":
            return addr
    return ""

st.set_page_config(
    page_title="LoyaltyToken dApp",
    page_icon="🪙",
    layout="wide",
)

# ─── Session state ────────────────────────────────────────────────────────────

def init_state():
    defaults = {
        "connected": False,
        "w3":        None,
        "contract":  None,
        "account":   None,
        "is_sepolia": False,
        "tx_log":    [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ─── Sidebar – connection ─────────────────────────────────────────────────────

with st.sidebar:
    st.title("Connection")
    rpc_url          = st.text_input("RPC URL", value=_default_rpc())
    contract_address = st.text_input(
        "Contract address", value=_default_address(), placeholder="0x…"
    )
    private_key = st.text_input(
        "Wallet private key",
        type="password",
        placeholder="0x…",
    )

    if st.button("Connect", use_container_width=True):
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url))

            if not w3.is_connected():
                st.error("Cannot reach the RPC endpoint.")
            elif not contract_address:
                st.error("Please paste the deployed contract address.")
            elif not private_key:
                st.error("Please provide a private key.")
            else:
                account  = w3.eth.account.from_key(private_key)
                contract = w3.eth.contract(
                    address=Web3.to_checksum_address(contract_address),
                    abi=ABI,
                )
                chain_id   = w3.eth.chain_id
                is_sepolia = (chain_id == 11155111)
                st.session_state.update(
                    connected=True,
                    w3=w3,
                    contract=contract,
                    account=account,
                    is_sepolia=is_sepolia,
                )
                network_label = "Sepolia" if is_sepolia else f"chain {chain_id}"
                st.success(f"Connected as {account.address[:10]}… ({network_label})")
        except Exception as exc:
            st.error(f"Connection error: {exc}")

    if st.session_state.connected:
        acc = st.session_state.account
        w3  = st.session_state.w3
        bal = w3.eth.get_balance(acc.address)
        st.markdown("---")
        st.markdown(f"**Address:** `{acc.address}`")
        st.markdown(f"**ETH Balance:** {w3.from_wei(bal, 'ether'):.6f} ETH")

# ─── Utility ─────────────────────────────────────────────────────────────────

def send_tx(fn, value_wei: int = 0):
    """Sign and broadcast; auto-selects EIP-1559 or legacy gas."""
    w3      = st.session_state.w3
    account = st.session_state.account
    nonce   = w3.eth.get_transaction_count(account.address)

    tx_params: dict = {
        "from":  account.address,
        "nonce": nonce,
        "value": value_wei,
        "gas":   200_000,
    }
    latest = w3.eth.get_block("latest")
    if "baseFeePerGas" in latest:
        tip = w3.to_wei(2, "gwei")
        tx_params["maxFeePerGas"]         = latest["baseFeePerGas"] * 2 + tip
        tx_params["maxPriorityFeePerGas"] = tip
    else:
        tx_params["gasPrice"] = w3.eth.gas_price

    tx      = fn.build_transaction(tx_params)
    signed  = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    return receipt


def pts(w3_instance, amount_wei: int) -> str:
    """Format a token amount as whole points (18 decimals)."""
    return f"{amount_wei / 10**18:,.2f} LPT"


def tx_link(tx_hash: str, is_sepolia: bool) -> str:
    if is_sepolia:
        return f"[View on Etherscan]({ETHERSCAN_BASE}/tx/{tx_hash})"
    return f"`{tx_hash[:20]}…`"


def log(msg: str):
    st.session_state.tx_log.insert(0, msg)

# ─── Main UI ─────────────────────────────────────────────────────────────────

st.title("🪙 LoyaltyToken (LPT) dApp")

if not st.session_state.connected:
    st.info("Fill in the sidebar and click **Connect** to get started.")
    st.stop()

w3         = st.session_state.w3
contract   = st.session_state.contract
account    = st.session_state.account
is_sepolia = st.session_state.is_sepolia

tab_wallet, tab_admin, tab_events = st.tabs(
    ["💳 My Wallet", "🔧 Admin – Mint", "📋 Event Log"]
)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 – MY WALLET
# ─────────────────────────────────────────────────────────────────────────────

with tab_wallet:
    st.subheader("Token Balance")

    if st.button("Refresh balance"):
        pass  # triggers rerun

    try:
        raw_balance = contract.functions.balanceOf(account.address).call()
        st.metric("Your LPT balance", pts(w3, raw_balance))
    except Exception as exc:
        st.error(f"Could not fetch balance: {exc}")
        st.stop()

    st.markdown("---")
    st.subheader("Transfer Tokens")
    st.caption("Send LPT points to another wallet address.")

    recipient = st.text_input("Recipient address", placeholder="0x…")
    amount    = st.number_input("Amount (whole points)", min_value=1, value=10, step=1)

    if st.button("Transfer"):
        if not recipient:
            st.warning("Enter a recipient address.")
        else:
            try:
                recipient_cs = Web3.to_checksum_address(recipient)
            except Exception:
                st.error("Invalid address format.")
                st.stop()

            amount_wei = w3.to_wei(amount, "ether")
            with st.spinner(f"Transferring {amount} LPT to {recipient[:10]}…"):
                try:
                    receipt = send_tx(
                        contract.functions.transfer(recipient_cs, amount_wei)
                    )
                    tx_hex = receipt.transactionHash.hex()
                    if receipt.status == 1:
                        st.success(f"Transferred {amount} LPT!")
                        st.markdown(tx_link(tx_hex, is_sepolia))
                        log(f"[TRANSFER] {amount} LPT → {recipient[:10]}… | {tx_hex}")
                    else:
                        st.error("Transfer failed on-chain.")
                except Exception as exc:
                    st.error(f"Reverted: {exc}")
                    log(f"[REVERT] transfer: {exc}")

    st.markdown("---")
    st.subheader("Burn (Redeem) Tokens")
    st.caption("Permanently destroy your own LPT (e.g. redeem for a real-world reward).")

    burn_amount = st.number_input("Amount to burn", min_value=1, value=1, step=1, key="burn_amt")
    if st.button("Burn tokens"):
        burn_wei = w3.to_wei(burn_amount, "ether")
        with st.spinner(f"Burning {burn_amount} LPT…"):
            try:
                receipt = send_tx(contract.functions.burn(burn_wei))
                tx_hex = receipt.transactionHash.hex()
                if receipt.status == 1:
                    st.success(f"Burned {burn_amount} LPT.")
                    st.markdown(tx_link(tx_hex, is_sepolia))
                    log(f"[BURN] {burn_amount} LPT | {tx_hex}")
                else:
                    st.error("Burn failed on-chain.")
            except Exception as exc:
                st.error(f"Reverted: {exc}")

    st.markdown("---")
    st.subheader("Check Any Address")
    lookup = st.text_input("Address to look up", placeholder="0x…", key="lookup_addr")
    if st.button("Check balance"):
        try:
            addr = Web3.to_checksum_address(lookup)
            bal  = contract.functions.balanceOf(addr).call()
            st.info(f"`{addr}` holds **{pts(w3, bal)}**")
        except Exception as exc:
            st.error(f"Error: {exc}")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 – ADMIN MINT
# ─────────────────────────────────────────────────────────────────────────────

with tab_admin:
    st.subheader("Mint Loyalty Points")
    st.caption(
        "Only the contract owner (business admin) can mint. "
        "The transaction will revert on-chain if you are not the owner."
    )

    try:
        owner_addr  = contract.functions.owner().call()
        total_sup   = contract.functions.totalSupply().call()
        is_owner    = (account.address.lower() == owner_addr.lower())
        st.markdown(f"**Contract owner:** `{owner_addr}`")
        st.metric("Total supply", pts(w3, total_sup))
        if is_owner:
            st.success("You are the contract owner.")
        else:
            st.warning("You are NOT the owner — mint calls will revert.")
    except Exception as exc:
        st.error(f"Could not fetch contract info: {exc}")

    st.markdown("---")

    mint_to     = st.text_input("Customer wallet address", placeholder="0x…")
    mint_amount = st.number_input(
        "Points to mint", min_value=1, value=100, step=10, key="mint_amt"
    )

    if st.button("Mint tokens"):
        if not mint_to:
            st.warning("Enter a customer address.")
        else:
            try:
                mint_to_cs = Web3.to_checksum_address(mint_to)
            except Exception:
                st.error("Invalid address format.")
                st.stop()

            mint_wei = w3.to_wei(mint_amount, "ether")
            with st.spinner(f"Minting {mint_amount} LPT to {mint_to[:10]}…"):
                try:
                    receipt = send_tx(contract.functions.mint(mint_to_cs, mint_wei))
                    tx_hex  = receipt.transactionHash.hex()
                    if receipt.status == 1:
                        st.success(f"Minted {mint_amount} LPT to {mint_to_cs[:10]}…")
                        st.markdown(tx_link(tx_hex, is_sepolia))
                        log(f"[MINT] {mint_amount} LPT → {mint_to[:10]}… | {tx_hex}")
                    else:
                        st.error("Mint failed on-chain.")
                except Exception as exc:
                    st.error(f"Reverted: {exc}")
                    log(f"[REVERT] mint: {exc}")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 – EVENT LOG
# ─────────────────────────────────────────────────────────────────────────────

with tab_events:
    st.subheader("Session Transaction Log")
    if st.session_state.tx_log:
        for entry in st.session_state.tx_log:
            parts = entry.rsplit("| ", 1)
            if len(parts) == 2 and parts[1].startswith("0x"):
                tx_hex = parts[1].strip()
                st.code(entry)
                if is_sepolia:
                    st.markdown(f"[Open on Etherscan]({ETHERSCAN_BASE}/tx/{tx_hex})")
            else:
                st.code(entry)
    else:
        st.info("No transactions recorded yet in this session.")

    st.markdown("---")
    st.subheader("On-chain Events")

    block_range = st.number_input(
        "Scan last N blocks", min_value=10, max_value=10000, value=500, step=100
    )

    col_mint, col_transfer = st.columns(2)

    with col_mint:
        if st.button("Fetch Mint events"):
            try:
                latest     = w3.eth.block_number
                from_block = max(0, latest - int(block_range))
                minted     = contract.events.TokensMinted.get_logs(
                    from_block=from_block, to_block="latest"
                )
                if minted:
                    rows = [
                        {
                            "To":     e["args"]["to"][:10] + "…",
                            "Amount": pts(w3, e["args"]["amount"]),
                            "Block":  e["blockNumber"],
                        }
                        for e in minted
                    ]
                    st.table(rows)
                else:
                    st.info(f"No mint events in the last {block_range} blocks.")
            except Exception as exc:
                st.error(f"Error: {exc}")

    with col_transfer:
        if st.button("Fetch Transfer events"):
            try:
                latest     = w3.eth.block_number
                from_block = max(0, latest - int(block_range))
                transfers  = contract.events.Transfer.get_logs(
                    from_block=from_block, to_block="latest"
                )
                if transfers:
                    rows = [
                        {
                            "From":   e["args"]["from"][:10] + "…",
                            "To":     e["args"]["to"][:10] + "…",
                            "Amount": pts(w3, e["args"]["value"]),
                            "Block":  e["blockNumber"],
                        }
                        for e in transfers
                    ]
                    st.table(rows)
                else:
                    st.info(f"No transfer events in the last {block_range} blocks.")
            except Exception as exc:
                st.error(f"Error: {exc}")
