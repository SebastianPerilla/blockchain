# Assignment 03 – Exercise 1: Vending Machine dApp
## Solution Documentation

---

## Table of Contents
1. [Project Structure](#1-project-structure)
2. [Tech Stack and Design Rationale](#2-tech-stack-and-design-rationale)
3. [Smart Contract Design](#3-smart-contract-design)
4. [Security Analysis](#4-security-analysis)
5. [Testing Strategy](#5-testing-strategy)
6. [Frontend Design (Streamlit)](#6-frontend-design-streamlit)
7. [How to Run](#7-how-to-run)
8. [Design Trade-offs and Limitations](#8-design-tradeoffs-and-limitations)

---

## 1. Project Structure

```
exercise-1/
├── contracts/
│   └── VendingMachine.sol      # Core smart contract
├── tests/
│   └── VendingMachine.test.ts  # Hardhat/Mocha/Chai tests (18 tests)
├── scripts/
│   └── deploy.ts               # Hardhat deployment script
├── app/
│   ├── app.py                  # Streamlit frontend
│   ├── extract_abi.py          # Helper: pulls ABI from Hardhat artifact
│   ├── abi.json                # Contract ABI (generated)
│   └── deployment.json         # Deployed address (generated on deploy)
├── hardhat.config.ts
├── tsconfig.json
├── package.json
├── README.md                   # Assignment brief
└── SOLUTION.md                 # This document
```

---

## 2. Tech Stack and Design Rationale

| Layer | Technology | Why |
|---|---|---|
| Smart contract | **Solidity 0.8.20** | Latest stable release; built-in overflow protection removes the need for SafeMath |
| Local blockchain | **Hardhat Network** | Built into Hardhat, zero-config, deterministic accounts, instant mining |
| Tests | **Hardhat + Ethers v6 + Mocha/Chai** | First-class TypeScript support, generated type bindings from `hardhat-toolbox`, covers the required test cases cleanly |
| Deploy script | **TypeScript (`scripts/deploy.ts`)** | Same language as tests, writes `deployment.json` so the Python frontend knows the contract address |
| Frontend | **Python Streamlit + web3.py** | Pure-Python, minimal boilerplate; re-renders on every interaction so state is always fresh from the chain |
| Wallet signing | **web3.py `eth_account`** | Signs transactions locally (private key never leaves the machine); no MetaMask dependency, which keeps the demo self-contained |

**Why not a JavaScript/React frontend?**
The assignment explicitly allowed a Python client. Streamlit gives an interactive GUI with ~150 lines of Python, no build pipeline, and very direct mapping between UI actions and web3 calls. This makes the flow easy to read and explain.

---

## 3. Smart Contract Design

### 3.1 Data Model

```solidity
struct Product {
    string  name;
    uint256 price;   // in wei — no floating point ambiguity
    uint256 stock;
    bool    exists;  // sentinel so we can distinguish "never added" from stock=0
}

mapping(uint8 => Product)                        products;
mapping(address => mapping(uint8 => uint256))    ownedItems;
uint8 productCount;
```

**Why a `mapping` instead of an `array`?**
- IDs are stable. If we ever remove a product we don't shift indices, so no client code breaks.
- No risk of an unbounded loop when iterating from outside the contract.
- A `uint8` ID cap means at most 255 products — plenty for a vending machine, and it saves gas compared to `uint256` keys.

**Why store `ownedItems` on-chain?**
The requirement is that "a user *becomes the owner inside the application*". That means the ownership claim must be verifiable without trusting any off-chain database. Storing it in a nested mapping is the minimal on-chain footprint: one storage slot per (buyer, productId) pair, written only when a purchase occurs.

**Why `price` in wei?**
Solidity has no floating-point arithmetic. Storing prices in wei avoids any division remainder issue. The frontend converts to ETH for display only.

### 3.2 Key Functions

| Function | Access | Description |
|---|---|---|
| `purchase(productId, qty)` | public payable | Core buy flow — validates stock, payment, updates state, emits event, refunds change |
| `restock(productId, qty)` | onlyOwner | Adds units to an existing product's stock |
| `addProduct(name, price, stock)` | onlyOwner | Adds a new product; increments `productCount` |
| `setPrice(productId, price)` | onlyOwner | Updates the price of an existing product |
| `withdraw()` | onlyOwner | Sends the full contract balance to the owner |
| `getAllProducts()` | view | Returns all products as parallel arrays — one call replaces N calls from the client |
| `getOwnedQuantity(user, productId)` | view | Returns how many of a product a user owns |
| `contractBalance()` | view | Returns `address(this).balance` |

### 3.3 Events

```solidity
event ItemPurchased(address indexed buyer, uint8 indexed productId,
                    string productName, uint256 quantity, uint256 totalPaid);

event ProductRestocked(uint8 indexed productId, string productName, uint256 newStock);

event ProductAdded(uint8 indexed productId, string name, uint256 price, uint256 initialStock);

event FundsWithdrawn(address indexed to, uint256 amount);
```

`ItemPurchased` and `ProductRestocked` satisfy the two-event minimum.  
`buyer` and `productId` are indexed so off-chain listeners can filter efficiently.

---

## 4. Security Analysis

### 4.1 Re-entrancy

`purchase()` follows **checks-effects-interactions**:
1. Check: `stock >= quantity` and `msg.value >= totalCost`
2. Effect: decrement stock, increment `ownedItems`
3. Interaction: refund change via `.call{value: change}("")`

If the refund reverts (e.g. a contract with a malicious `receive()`) the whole transaction reverts — the state changes roll back. There is no scenario where stock is decremented but the buyer doesn't pay.

`withdraw()` also zeros-state-before-transfer by emitting the event and calling `payable(owner).call` in that order.

### 4.2 Access Control

All admin functions (`restock`, `addProduct`, `setPrice`, `withdraw`) are guarded by the `onlyOwner` modifier which compares `msg.sender` to the immutable `owner` address set in the constructor.  
A malicious non-owner calling these will get an immediate `require` revert — no gas is wasted beyond the failed call.

### 4.3 Integer Arithmetic

Solidity 0.8.x throws on overflow by default. `price * quantity` cannot silently wrap. For very large quantities with high prices the multiplication would revert before any state is changed.

### 4.4 Over-payment / Refunds

We deliberately **refund** surplus ETH rather than accepting it silently as a donation. This prevents users from accidentally sending more than required and losing funds. The refund uses a low-level `.call` (rather than `transfer`) so it works with contracts that have expensive `receive` fallbacks.

### 4.5 Invalid Product ID

All public functions that take a `productId` go through the `productExists` modifier which checks the `exists` flag. Calling with a non-existent ID reverts immediately.

### 4.6 Replay / Double-spend

Each purchase is atomic: within a single transaction, stock is decremented and ownership is incremented. There is no multi-step commit/reveal that could be replayed. Block re-organisations are irrelevant for a local demo but would be a concern on mainnet — for high-value items a confirmation depth check could be added off-chain.

### 4.7 Front-running

On a public network a miner could see a `purchase` in the mempool and front-run it to drain stock. For a production vending machine a commit/reveal or a rate limit per block per address would mitigate this. For this exercise (local Hardhat network) it is out of scope.

---

## 5. Testing Strategy

Tests live in `tests/VendingMachine.test.ts` and are run with `npx hardhat test`.

### Coverage Matrix

| Requirement | Test(s) |
|---|---|
| ✅ At least one successful purchase | "allows a buyer to purchase one Cola" |
| ✅ Failed purchase – insufficient payment | "reverts when payment is too low", "reverts when paying nothing" |
| ✅ Failed purchase – out of stock | "reverts when quantity exceeds stock", "reverts when stock fully depleted" |
| ✅ Permission failure (non-owner admin) | "non-owner cannot restock/addProduct/setPrice/withdraw" (4 tests) |
| ✅ State changes after successful purchase | "decrements stock", "tracks ownership across multiple purchases", "tracks ownership independently per buyer", "accumulates contract balance" |
| Bonus | "refunds over-payment", "owner can withdraw", "owner can restock + event", "getAllProducts returns all three" |

**Total: 18 tests, all passing.**

### Test Design Philosophy
- Each test has one clear assertion and uses `beforeEach` to get a fresh contract deployment, so tests are fully independent.
- Failure tests assert the exact revert message, not just that a revert happened — this catches accidental reverts from the wrong path.
- The "refunds over-payment" test measures the actual ETH balance delta (accounting for gas) to prove the refund logic is correct.

---

## 6. Frontend Design (Streamlit)

### Architecture

```
Streamlit app (Python)
        │
        │  JSON-RPC (HTTP)
        ▼
Hardhat node / Ganache (local)
        │
        ▼
VendingMachine.sol
```

The app uses `web3.py` to:
1. Connect to the local RPC
2. Load the contract using the ABI from `abi.json`
3. Call view functions directly (no gas, no signing)
4. Build, sign (with the in-memory private key), and broadcast state-changing transactions

### UI Tabs

| Tab | Contents |
|---|---|
| 🛒 Shop | Product cards with price, stock, buy button and quantity selector |
| 🎒 My Inventory | Shows items owned by the connected wallet (or any address) |
| 🔧 Admin | Restock, add product, update price, withdraw ETH |
| 📋 Transaction Log | In-session log + on-chain `ItemPurchased` event history |

### Why Streamlit over a JS frontend?
- **No build step**: `streamlit run app/app.py` is all that's needed.
- **Readable**: each button maps to exactly one `contract.functions.X().call()` or `send_tx(contract.functions.X(…))` — the control flow is linear and easy to audit.
- **Consistent with the course stack**: the course uses Python web3; Streamlit keeps everything in the same language.

---

## 7. How to Run

### Prerequisites

```bash
node >= 18
npm >= 9
python3 >= 3.10
```

### Step 1 — Install dependencies

```bash
# from exercise-1/
npm install
pip3 install streamlit web3 --break-system-packages
```

### Step 2 — Compile the contract and run tests

```bash
npx hardhat compile
npx hardhat test
```

Expected: **18 passing**

### Step 3 — Start a local Hardhat node

```bash
npx hardhat node
```

Leave this terminal running. Copy one of the displayed private keys — you will need it.

### Step 4 — Deploy the contract

Open a **second terminal** (same directory):

```bash
npx hardhat run scripts/deploy.ts --network localhost
```

The deployed address is printed and also saved to `app/deployment.json`.

### Step 5 — Start the Streamlit app

```bash
streamlit run app/app.py
```

Browser opens at `http://localhost:8501`.

### Step 6 — Connect

In the sidebar:
- **RPC URL**: `http://127.0.0.1:8545` (default)
- **Contract address**: paste from Step 4 output (or read `app/deployment.json`)
- **Wallet private key**: paste a key from the Hardhat node output in Step 3
- Click **Connect**

---

## 8. Design Trade-offs and Limitations

| Decision | Alternative | Why we chose this |
|---|---|---|
| `uint8` product ID | `uint256` | Saves gas; 255 products is more than enough |
| Store ownership on-chain | Off-chain DB + events | Requirement says "becomes owner inside the application" — provability requires on-chain state |
| Price in wei | Price in a custom decimal type | Avoids any division ambiguity; ETH conversion is display-only |
| `owner` = deployer | Role-based access (OpenZeppelin `Ownable`) | Simpler contract, no external dependency; meets the single-admin requirement |
| Refund surplus payment | Reject non-exact payment | Better UX; prevents accidental ETH loss |
| `getAllProducts()` bulk view | Individual `getProduct(id)` calls | Reduces round-trips from the frontend; array return is still O(n) in memory but n ≤ 255 |
| Streamlit + web3.py | React + ethers.js | No build pipeline; matches course Python stack; easy to read and audit |
| Local signing (private key in UI) | MetaMask injection | Self-contained demo; MetaMask requires a browser extension and JS |

**Known limitations for production use:**
- The private key is entered in plain text in the Streamlit sidebar — acceptable for a local demo with a test key, not for mainnet.
- No front-running protection on the purchase function.
- The `owner` address is fixed at deploy time with no transfer mechanism.
- No pagination for `getAllProducts()` — fine for ≤255 products.
