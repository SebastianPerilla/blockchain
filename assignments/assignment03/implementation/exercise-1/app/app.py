"""
Vending Machine dApp – Streamlit Frontend
==========================================
Connects to a local Hardhat node (or any RPC endpoint) and lets users
interact with the VendingMachine smart contract.

How to run
----------
1.  npx hardhat node                    # terminal 1 – local blockchain
2.  npx hardhat run scripts/deploy.ts --network localhost   # deploy
3.  Copy the deployed address into the sidebar (or set CONTRACT_ADDRESS below)
4.  streamlit run app/app.py            # terminal 2

Private keys shown in the Hardhat node output can be pasted into the
"Wallet private key" field to act as different users.
"""

import json
import pathlib
import streamlit as st
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# ─── Config ──────────────────────────────────────────────────────────────────

ABI_PATH = pathlib.Path(__file__).parent / "abi.json"
ABI = json.loads(ABI_PATH.read_text())

st.set_page_config(
    page_title="Vending Machine dApp",
    page_icon="🥤",
    layout="wide",
)

# ─── Session state helpers ────────────────────────────────────────────────────

def init_state():
    defaults = {
        "connected": False,
        "w3": None,
        "contract": None,
        "account": None,
        "tx_log": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ─── Sidebar – connection ─────────────────────────────────────────────────────

with st.sidebar:
    st.title("Connection")
    rpc_url = st.text_input("RPC URL", value="http://127.0.0.1:8545")
    contract_address = st.text_input("Contract address", placeholder="0x…")
    private_key = st.text_input(
        "Wallet private key",
        type="password",
        placeholder="0x…  (Hardhat test key is fine)",
    )

    connect_btn = st.button("Connect", use_container_width=True)

    if connect_btn:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            # Some local nodes (Ganache) inject extra PoA data – handle it
            w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

            if not w3.is_connected():
                st.error("Cannot reach the RPC endpoint. Is the node running?")
            elif not contract_address:
                st.error("Please paste the deployed contract address.")
            elif not private_key:
                st.error("Please provide a private key to sign transactions.")
            else:
                account = w3.eth.account.from_key(private_key)
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
        st.markdown(f"**Balance:** {w3.from_wei(bal, 'ether'):.4f} ETH")

# ─── Utility ─────────────────────────────────────────────────────────────────

def send_tx(fn, value_wei=0):
    """Sign and broadcast a contract transaction; return the receipt."""
    w3      = st.session_state.w3
    account = st.session_state.account
    nonce   = w3.eth.get_transaction_count(account.address)
    tx      = fn.build_transaction(
        {
            "from":     account.address,
            "nonce":    nonce,
            "value":    value_wei,
            "gas":      300_000,
            "gasPrice": w3.eth.gas_price,
        }
    )
    signed  = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt

def log(msg):
    st.session_state.tx_log.insert(0, msg)

# ─── Main UI ─────────────────────────────────────────────────────────────────

st.title("🥤 Vending Machine dApp")

if not st.session_state.connected:
    st.info("Fill in the sidebar and click **Connect** to get started.")
    st.stop()

w3       = st.session_state.w3
contract = st.session_state.contract
account  = st.session_state.account

# ── Tabs ─────────────────────────────────────────────────────────────────────

tab_shop, tab_inventory, tab_admin, tab_events = st.tabs(
    ["🛒 Shop", "🎒 My Inventory", "🔧 Admin", "📋 Transaction Log"]
)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 – SHOP
# ─────────────────────────────────────────────────────────────────────────────

with tab_shop:
    st.subheader("Available Products")

    if st.button("Refresh products"):
        pass  # triggers a rerun

    try:
        ids, names, prices, stocks = contract.functions.getAllProducts().call()
    except Exception as exc:
        st.error(f"Could not load products: {exc}")
        st.stop()

    if not ids:
        st.warning("No products found in the contract.")
    else:
        # Display products in a responsive grid (3 columns)
        cols = st.columns(min(len(ids), 3))
        for idx, (pid, name, price, stock) in enumerate(zip(ids, names, prices, stocks)):
            col = cols[idx % 3]
            with col:
                price_eth = w3.from_wei(price, "ether")
                availability = "In stock" if stock > 0 else "Out of stock"
                colour = "green" if stock > 0 else "red"
                st.markdown(
                    f"""
                    <div style="border:1px solid #ddd; border-radius:8px; padding:16px; margin-bottom:8px;">
                        <h3 style="margin:0">{name}</h3>
                        <p style="margin:4px 0">Price: <b>{price_eth} ETH</b></p>
                        <p style="margin:4px 0">Stock: <b>{stock}</b></p>
                        <p style="color:{colour}; margin:4px 0"><b>{availability}</b></p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if stock > 0:
                    qty_key = f"qty_{pid}"
                    qty = st.number_input(
                        "Quantity",
                        min_value=1,
                        max_value=int(stock),
                        value=1,
                        key=qty_key,
                    )
                    if st.button(f"Buy {name}", key=f"buy_{pid}"):
                        total_cost = price * qty
                        with st.spinner(f"Purchasing {qty} × {name}…"):
                            try:
                                receipt = send_tx(
                                    contract.functions.purchase(pid, qty),
                                    value_wei=total_cost,
                                )
                                status = "success" if receipt.status == 1 else "failed"
                                log(
                                    f"[{status.upper()}] Bought {qty}×{name} "
                                    f"for {w3.from_wei(total_cost,'ether')} ETH | "
                                    f"tx {receipt.transactionHash.hex()[:16]}…"
                                )
                                if receipt.status == 1:
                                    st.success(
                                        f"Purchased {qty} × {name}! "
                                        f"Paid {w3.from_wei(total_cost,'ether')} ETH"
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
        "Check another address (leave blank to use your connected wallet)",
        placeholder="0x…",
    )
    lookup_address = (
        Web3.to_checksum_address(custom_address)
        if custom_address
        else account.address
    )

    if st.button("Load inventory"):
        pass  # triggers rerun

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

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 – ADMIN
# ─────────────────────────────────────────────────────────────────────────────

with tab_admin:
    st.subheader("Admin Panel")
    st.caption(
        "These functions are protected by `onlyOwner`. "
        "They will revert if the connected wallet is not the contract owner."
    )

    # ── Restock ──────────────────────────────────────────────────────────────
    st.markdown("### Restock a product")
    try:
        ids, names, _, _ = contract.functions.getAllProducts().call()
        product_options = {name: pid for name, pid in zip(names, ids)}
    except Exception:
        product_options = {}

    if product_options:
        restock_product = st.selectbox("Product to restock", list(product_options.keys()))
        restock_qty = st.number_input("Additional units", min_value=1, value=5, key="restock_qty")
        if st.button("Restock"):
            pid = product_options[restock_product]
            with st.spinner("Sending restock transaction…"):
                try:
                    receipt = send_tx(contract.functions.restock(pid, restock_qty))
                    if receipt.status == 1:
                        st.success(f"Restocked {restock_qty} units of {restock_product}.")
                        log(f"[RESTOCK] {restock_product} +{restock_qty} | tx {receipt.transactionHash.hex()[:16]}…")
                    else:
                        st.error("Restock transaction failed on-chain.")
                except Exception as exc:
                    st.error(f"Restock reverted: {exc}")

    st.markdown("---")

    # ── Add product ──────────────────────────────────────────────────────────
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
                        st.success(f"'{new_name}' added to the machine.")
                        log(f"[ADD PRODUCT] {new_name} @ {new_price} ETH | tx {receipt.transactionHash.hex()[:16]}…")
                    else:
                        st.error("Transaction failed.")
                except Exception as exc:
                    st.error(f"Reverted: {exc}")

    st.markdown("---")

    # ── Withdraw ─────────────────────────────────────────────────────────────
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
                    st.success("Funds withdrawn.")
                    log(f"[WITHDRAW] | tx {receipt.transactionHash.hex()[:16]}…")
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
            st.code(entry)
    else:
        st.info("No transactions recorded yet in this session.")

    st.markdown("---")
    st.subheader("On-chain Purchase Events (last 500 blocks)")
    if st.button("Fetch purchase events"):
        try:
            latest = w3.eth.block_number
            from_block = max(0, latest - 500)
            purchase_filter = contract.events.ItemPurchased.create_filter(
                from_block=from_block, to_block="latest"
            )
            events = purchase_filter.get_all_entries()
            if events:
                rows = [
                    {
                        "Buyer":    e["args"]["buyer"][:10] + "…",
                        "Product":  e["args"]["productName"],
                        "Qty":      e["args"]["quantity"],
                        "Paid ETH": w3.from_wei(e["args"]["totalPaid"], "ether"),
                        "Block":    e["blockNumber"],
                    }
                    for e in events
                ]
                st.table(rows)
            else:
                st.info("No purchase events in the last 500 blocks.")
        except Exception as exc:
            st.error(f"Could not fetch events: {exc}")
