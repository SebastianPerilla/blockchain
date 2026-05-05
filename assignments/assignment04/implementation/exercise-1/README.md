# Exercise 1 – Vending Machine on Sepolia

## Overview

This exercise deploys the VendingMachine smart contract (unchanged from Assignment 3) to the
Ethereum Sepolia public testnet and updates the Streamlit frontend to connect to it.

**Deployed contract:** `<paste address after deploy>`
**Etherscan:** `https://sepolia.etherscan.io/address/<address>`

**Purchase proof transactions:**
- `https://sepolia.etherscan.io/tx/<tx_hash_1>`
- `https://sepolia.etherscan.io/tx/<tx_hash_2>`

---

## Setup

### Prerequisites

- Node.js ≥ 18, npm
- Python ≥ 3.10, pip
- A Sepolia wallet with test ETH (from https://cloud.google.com/application/web3/faucet)
- An Infura or Alchemy account for the Sepolia RPC endpoint

### 1. Install Node dependencies

```bash
cd assignment04/implementation/exercise-1
npm install
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set:
#   SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/<your_key>
#   PRIVATE_KEY=0x<your_wallet_private_key>
```

### 3. Compile the contract

```bash
npx hardhat compile
python app/extract_abi.py    # regenerates app/abi.json from the artifact
```

### 4. Run tests (against local Hardhat network)

```bash
npx hardhat test
```

### 5. Deploy to Sepolia

```bash
npx hardhat run scripts/deploy.ts --network sepolia
```

The deployed address is written to `app/deployment.json` automatically.

### 6. Launch the frontend

```bash
pip install streamlit web3
streamlit run app/app.py
```

Open the sidebar, confirm the RPC URL and contract address, paste your private key, and click
**Connect**.

---

## Test cases

Tests run against the Hardhat in-process network (`npx hardhat test`).  The suite covers:

| # | Scenario | Expected result |
|---|----------|-----------------|
| 1 | Buyer purchases one Cola at exact price | `ItemPurchased` event emitted; owned qty = 1 |
| 2 | Buyer purchases 2 Cola; stock decrements | stock drops by 2 |
| 3 | Buyer over-pays by 1 ETH | change refunded; net spent = price + gas |
| 4 | Two buyers accumulate contract balance | balance = sum of both purchases |
| 5 | Payment too low | reverts with `insufficient payment` |
| 6 | Zero ETH sent | reverts with `insufficient payment` |
| 7 | Quantity exceeds stock | reverts with `insufficient stock` |
| 8 | Stock fully depleted, buyer tries again | reverts with `insufficient stock` |
| 9 | Same buyer purchases twice | owned qty accumulates |
| 10 | Two buyers, independent ownership | each buyer's qty tracked separately |
| 11 | Non-owner calls restock | reverts with `caller is not the owner` |
| 12 | Non-owner adds product | reverts |
| 13 | Non-owner changes price | reverts |
| 14 | Non-owner withdraws | reverts |
| 15 | Owner restocks, emits event | `ProductRestocked` with correct new stock |
| 16 | Owner adds product | productCount increments |
| 17 | Owner withdraws | owner balance increases by exact purchase amount |
| 18 | getAllProducts returns seeded data | 3 products with correct names and prices |

---

## Design choices

### What changed moving from Ganache/Hardhat-local to Sepolia

**Smart contract – nothing changed.**
The Solidity code, ABI, and bytecode are byte-for-byte identical.  Solidity is EVM-agnostic;
the same contract works on any EVM chain.

**Frontend – three targeted changes:**

1. **Removed `ExtraDataToPOAMiddleware`.**
   Ganache/Clique (PoA) chains inject a non-standard `extraData` field that confuses web3.py.
   The middleware patches that.  Sepolia uses Proof-of-Stake and does not add extra data, so
   the middleware is not only unnecessary but would interfere with the connection.

2. **Switched to EIP-1559 gas (`maxFeePerGas` / `maxPriorityFeePerGas`).**
   Sepolia is a post-London network.  Legacy `gasPrice` still works, but EIP-1559 gives better
   fee predictability.  The app reads `baseFeePerGas` from the latest block and adds a 2 gwei
   priority tip with a 2× base-fee ceiling.

3. **Replaced `create_filter` with `get_logs`.**
   `create_filter` calls `eth_newFilter` which requires the provider to hold stateful filter
   objects.  Infura and Alchemy do not support this endpoint.  `get_logs` is stateless and
   universally supported.  The only downside is that you must specify a block range up front;
   the UI exposes a "last N blocks" slider for this.

**Hardhat config – Sepolia network added, env vars for secrets.**
The private key and RPC URL are read from `.env` so they are never committed.

### On-chain vs off-chain

| Data | Location | Reason |
|------|----------|--------|
| Product catalogue (name, price, stock) | On-chain | Core machine state; must be trustlessly readable by anyone |
| Purchase ownership (`ownedItems`) | On-chain | Proof of ownership is the whole point of using a blockchain |
| Contract revenue (ETH balance) | On-chain | Implicit; funds are held by the contract address |
| User session / connection state | Off-chain (Streamlit) | Ephemeral UI state, no value in persisting it on-chain |
| Transaction log in the UI | Off-chain (session memory) | Convenience display; permanent record is on-chain via events |

### Gas / cost observations on Sepolia vs local

- On a local Hardhat node gas is free (accounts start with 10 000 ETH, gas price is 1 wei).
- On Sepolia gas is priced in real testnet ETH.  The `purchase` function costs ~50 000 gas;
  at a 10 gwei base fee that is ~0.0005 ETH per call — negligible with faucet ETH.
- The `withdraw` pattern (CEI — checks, effects, interactions) is unchanged and continues
  to protect against re-entrancy on the live network.

### Access control

- `onlyOwner` guards `restock`, `addProduct`, `setPrice`, `withdraw`.
- `owner` is set to `msg.sender` at deploy time (the wallet in `.env`).
- No ownership transfer function is provided intentionally — the contract is a
  homework exercise, not a production system.
