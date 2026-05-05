"""
Vending Machine dApp – Streamlit Frontend (Sepolia testnet)
===========================================================
Connects to the Ethereum Sepolia testnet via an Infura or Alchemy RPC
endpoint and lets users interact with the deployed VendingMachine contract.

How to run
----------
1.  Deploy the contract to Sepolia:
      npx hardhat run scripts/deploy.ts --network sepolia
    (requires .env with SEPOLIA_RPC_URL and PRIVATE_KEY)
2.  The contract address is saved to app/deployment.json automatically.
3.  streamlit run app/app.py

Changes vs the local (Ganache/Hardhat) version
-----------------------------------------------
- No ExtraDataToPOAMiddleware: Sepolia uses PoS; the extra-data workaround
  for PoA chains (Ganache) is not needed and would break the connection.
- EIP-1559 gas: transactions use maxFeePerGas / maxPriorityFeePerGas so
  fees are estimated correctly on the live network.
- get_logs instead of create_filter: Infura and Alchemy do not support the
  stateful eth_newFilter RPC method used by create_filter.  get_logs is a
  stateless call that works with every provider.
- Etherscan links: every confirmed transaction shows a clickable Sepolia
  Etherscan URL so users can verify their purchases on-chain.
- The smart contract itself required zero changes: the Solidity logic,
  events, and ABI are identical.  Only the deployment target changed.
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
    """Return RPC URL from deployment.json env hint or a placeholder."""
    rpc = os.getenv("SEPOLIA_RPC_URL", "")
    if rpc:
        return rpc
    return "https://sepolia.infura.io/v3/YOUR_PROJECT_ID"

def _default_address() -> str:
    if DEPLOYMENT_PATH.exists():
        data = json.loads(DEPLOYMENT_PATH.read_text())
        return data.get("address", "")
    return ""

st.set_page_config(
    page_title="Vending Machine – Sepolia",
    page_icon="🥤",
    layout="wide",
)

# ─── Session state ────────────────────────────────────────────────────────────

def init_state():
    defaults = {
        "connected": False,
        "w3":        None,
        "contract":  None,
        "account":   None,
        "tx_log":    [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ─── Sidebar – connection ─────────────────────────────────────────────────────

with st.sidebar:
    st.title("Connection")
    st.caption("Connect to the Sepolia testnet via Infura or Alchemy.")

    rpc_url          = st.text_input("RPC URL (Infura / Alchemy)", value=_default_rpc())
    contract_address = st.text_input("Contract address", value=_default_address(), placeholder="0x…")
    private_key      = st.text_input(
        "Wallet private key",
        type="password",
        placeholder="0x…  (use a dedicated testnet wallet)",
    )

    connect_btn = st.button("Connect", use_container_width=True)

    if connect_btn:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            # Sepolia is a PoS chain — no ExtraDataToPOAMiddleware needed.

            if not w3.is_connected():
                st.error("Cannot reach the RPC endpoint. Check your Infura/Alchemy URL.")
            elif not contract_address:
                st.error("Please paste the deployed contract address.")
            elif not private_key:
                st.error("Please provide a private key to sign transactions.")
            else:
                account  = w3.eth.account.from_key(private_key)
                contract = w3.eth.contract(
                    address=Web3.to_checksum_address(contract_address),
                    abi=ABI,
                )
                st.session_state.update(
                    connected=True,
                    w3=w3,
                    contract=contract,
                    account=account,
                )
                st.success(f"Connected as {account.address[:10]}…")
        except Exception as exc:
            st.error(f"Connection error: {exc}")

    if st.session_state.connected:
        acc = st.session_state.account
        w3  = st.session_state.w3
        bal = w3.eth.get_balance(acc.address)
        st.markdown("---")
        st.markdown(f"**Address:** `{acc.address}`")
        st.markdown(f"**Balance:** {w3.from_wei(bal, 'ether'):.6f} ETH")
        st.markdown(
            f"[View on Etherscan]({ETHERSCAN_BASE}/address/{acc.address})",
            unsafe_allow_html=False,
        )

# ─── Utility ─────────────────────────────────────────────────────────────────

def send_tx(fn, value_wei: int = 0):
    """Sign and broadcast a contract transaction using EIP-1559 fees."""
    w3      = st.session_state.w3
    account = st.session_state.account
    nonce   = w3.eth.get_transaction_count(account.address)

    # EIP-1559: estimate base fee + tip instead of legacy gasPrice
    base_fee  = w3.eth.get_block("latest")["baseFeePerGas"]
    max_tip   = w3.to_wei(2, "gwei")                      # 2 gwei priority fee
    max_fee   = base_fee * 2 + max_tip                    # comfortable ceiling

    tx = fn.build_transaction(
        {
            "from":                 account.address,
            "nonce":                nonce,
            "value":                value_wei,
            "gas":                  300_000,
            "maxFeePerGas":         max_fee,
            "maxPriorityFeePerGas": max_tip,
        }
    )
    signed  = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    return receipt


def etherscan_tx(tx_hash: str) -> str:
    return f"{ETHERSCAN_BASE}/tx/{tx_hash}"


def log(msg: str):
    st.session_state.tx_log.insert(0, msg)

# ─── Main UI ─────────────────────────────────────────────────────────────────

st.title("🥤 Vending Machine dApp — Sepolia Testnet")

if not st.session_state.connected:
    st.info("Fill in the sidebar and click **Connect** to get started.")
    st.stop()

w3       = st.session_state.w3
contract = st.session_state.contract
account  = st.session_state.account

tab_shop, tab_inventory, tab_admin, tab_events = st.tabs(
    ["🛒 Shop", "🎒 My Inventory", "🔧 Admin", "📋 Transaction Log"]
)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 – SHOP
# ─────────────────────────────────────────────────────────────────────────────

with tab_shop:
    st.subheader("Available Products")
    if st.button("Refresh products"):
        pass  # triggers rerun

    try:
        ids, names, prices, stocks = contract.functions.getAllProducts().call()
    except Exception as exc:
        st.error(f"Could not load products: {exc}")
        st.stop()

    if not ids:
        st.warning("No products found in the contract.")
    else:
        cols = st.columns(min(len(ids), 3))
        for idx, (pid, name, price, stock) in enumerate(zip(ids, names, prices, stocks)):
            col = cols[idx % 3]
            with col:
                price_eth    = w3.from_wei(price, "ether")
                availability = "In stock" if stock > 0 else "Out of stock"
                colour       = "green" if stock > 0 else "red"
                st.markdown(
                    f"""
                    <div style="border:1px solid #ddd;border-radius:8px;padding:16px;margin-bottom:8px;">
                        <h3 style="margin:0">{name}</h3>
                        <p style="margin:4px 0">Price: <b>{price_eth} ETH</b></p>
                        <p style="margin:4px 0">Stock: <b>{stock}</b></p>
                        <p style="color:{colour};margin:4px 0"><b>{availability}</b></p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if stock > 0:
                    qty = st.number_input(
                        "Quantity", min_value=1, max_value=int(stock), value=1,
                        key=f"qty_{pid}",
                    )
                    if st.button(f"Buy {name}", key=f"buy_{pid}"):
                        total_cost = price * qty
                        with st.spinner(f"Purchasing {qty} × {name} on Sepolia…"):
                            try:
                                receipt = send_tx(
                                    contract.functions.purchase(pid, qty),
                                    value_wei=total_cost,
                                )
                                tx_hex  = receipt.transactionHash.hex()
                                status  = "success" if receipt.status == 1 else "failed"
                                log(
                                    f"[{status.upper()}] Bought {qty}×{name} "
                                    f"for {w3.from_wei(total_cost,'ether')} ETH | "
                                    f"tx {tx_hex}"
                                )
                                if receipt.status == 1:
                                    st.success(
                                        f"Purchased {qty} × {name}!  "
                                        f"Paid {w3.from_wei(total_cost,'ether')} ETH"
                                    )
                                    st.markdown(
                                        f"[View transaction on Etherscan]({etherscan_tx(tx_hex)})"
                                    )
                                else:
                                    st.error("Transaction failed on-chain.")
                            except Exception as exc:
                                st.error(f"Transaction reverted: {exc}")
                                log(f"[REVERT] {exc}")
                else:
                    st.button(f"Out of stock", key=f"buy_{pid}", disabled=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 – MY INVENTORY
# ─────────────────────────────────────────────────────────────────────────────

with tab_inventory:
    st.subheader(f"Items owned by `{account.address}`")

    custom_address = st.text_input(
        "Check another address (leave blank for your wallet)",
        placeholder="0x…",
    )
    lookup_address = (
        Web3.to_checksum_address(custom_address) if custom_address else account.address
    )

    if st.button("Load inventory"):
        pass

    try:
        ids, names, prices, stocks = contract.functions.getAllProducts().call()
        owned_data = []
        for pid, name in zip(ids, names):
            qty = contract.functions.getOwnedQuantity(lookup_address, pid).call()
            if qty > 0:
                owned_data.append({"Product": name, "Quantity Owned": qty})
    except Exception as exc:
        st.error(f"Could not load inventory: {exc}")
        st.stop()

    if owned_data:
        st.table(owned_data)
    else:
        st.info("No items owned at this address yet.")

    st.markdown(
        f"[View address on Etherscan]({ETHERSCAN_BASE}/address/{lookup_address})"
    )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 – ADMIN
# ─────────────────────────────────────────────────────────────────────────────

with tab_admin:
    st.subheader("Admin Panel")
    st.caption(
        "These functions are protected by `onlyOwner`. "
        "They will revert if the connected wallet is not the contract owner."
    )

    st.markdown("### Restock a product")
    try:
        ids, names, _, _ = contract.functions.getAllProducts().call()
        product_options  = {name: pid for name, pid in zip(names, ids)}
    except Exception:
        product_options = {}

    if product_options:
        restock_product = st.selectbox("Product to restock", list(product_options.keys()))
        restock_qty     = st.number_input("Additional units", min_value=1, value=5, key="restock_qty")
        if st.button("Restock"):
            pid = product_options[restock_product]
            with st.spinner("Sending restock transaction to Sepolia…"):
                try:
                    receipt = send_tx(contract.functions.restock(pid, restock_qty))
                    if receipt.status == 1:
                        tx_hex = receipt.transactionHash.hex()
                        st.success(f"Restocked {restock_qty} units of {restock_product}.")
                        st.markdown(f"[View on Etherscan]({etherscan_tx(tx_hex)})")
                        log(f"[RESTOCK] {restock_product} +{restock_qty} | tx {tx_hex}")
                    else:
                        st.error("Restock transaction failed on-chain.")
                except Exception as exc:
                    st.error(f"Restock reverted: {exc}")

    st.markdown("---")

    st.markdown("### Add a new product")
    new_name  = st.text_input("Product name")
    new_price = st.number_input("Price (ETH)", min_value=0.0001, step=0.001, format="%.4f")
    new_stock = st.number_input("Initial stock", min_value=1, value=10)
    if st.button("Add product"):
        if not new_name:
            st.warning("Please enter a product name.")
        else:
            price_wei = w3.to_wei(new_price, "ether")
            with st.spinner("Adding product…"):
                try:
                    receipt = send_tx(contract.functions.addProduct(new_name, price_wei, new_stock))
                    if receipt.status == 1:
                        tx_hex = receipt.transactionHash.hex()
                        st.success(f"'{new_name}' added to the machine.")
                        st.markdown(f"[View on Etherscan]({etherscan_tx(tx_hex)})")
                        log(f"[ADD PRODUCT] {new_name} @ {new_price} ETH | tx {tx_hex}")
                    else:
                        st.error("Transaction failed.")
                except Exception as exc:
                    st.error(f"Reverted: {exc}")

    st.markdown("---")

    st.markdown("### Withdraw contract balance")
    try:
        bal = contract.functions.contractBalance().call()
        st.metric("Contract balance", f"{w3.from_wei(bal, 'ether'):.6f} ETH")
    except Exception:
        pass

    if st.button("Withdraw all ETH to owner"):
        with st.spinner("Withdrawing…"):
            try:
                receipt = send_tx(contract.functions.withdraw())
                if receipt.status == 1:
                    tx_hex = receipt.transactionHash.hex()
                    st.success("Funds withdrawn.")
                    st.markdown(f"[View on Etherscan]({etherscan_tx(tx_hex)})")
                    log(f"[WITHDRAW] tx {tx_hex}")
                else:
                    st.error("Withdrawal failed.")
            except Exception as exc:
                st.error(f"Reverted: {exc}")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 – TRANSACTION LOG
# ─────────────────────────────────────────────────────────────────────────────

with tab_events:
    st.subheader("Session Transaction Log")
    if st.session_state.tx_log:
        for entry in st.session_state.tx_log:
            # If entry contains a full tx hash, linkify it
            parts = entry.split("tx ")
            if len(parts) == 2 and parts[1].startswith("0x"):
                tx_hex = parts[1].strip()
                st.code(entry)
                st.markdown(f"[Open on Etherscan]({etherscan_tx(tx_hex)})")
            else:
                st.code(entry)
    else:
        st.info("No transactions recorded yet in this session.")

    st.markdown("---")
    st.subheader("On-chain Purchase Events")

    block_range = st.number_input(
        "Scan last N blocks", min_value=100, max_value=10000, value=1000, step=100
    )

    if st.button("Fetch purchase events"):
        try:
            latest     = w3.eth.block_number
            from_block = max(0, latest - int(block_range))

            # Use get_logs (stateless) — create_filter is not supported by
            # Infura / Alchemy and would raise an error on public RPC endpoints.
            event_sig  = contract.events.ItemPurchased._get_event_abi()
            raw_logs   = contract.events.ItemPurchased.get_logs(
                from_block=from_block,
                to_block="latest",
            )

            if raw_logs:
                rows = [
                    {
                        "Buyer":    e["args"]["buyer"][:10] + "…",
                        "Product":  e["args"]["productName"],
                        "Qty":      e["args"]["quantity"],
                        "Paid ETH": w3.from_wei(e["args"]["totalPaid"], "ether"),
                        "Block":    e["blockNumber"],
                        "Tx":       e["transactionHash"].hex(),
                    }
                    for e in raw_logs
                ]
                st.table([{k: v for k, v in r.items() if k != "Tx"} for r in rows])
                st.markdown("**Transaction links:**")
                for r in rows:
                    st.markdown(
                        f"- Block {r['Block']}: "
                        f"[{r['Tx'][:20]}…]({etherscan_tx(r['Tx'])})"
                    )
            else:
                st.info(f"No purchase events in the last {block_range} blocks.")
        except Exception as exc:
            st.error(f"Could not fetch events: {exc}")
