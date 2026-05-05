# Exercise 2 – ERC-20 Loyalty Token

## Overview

`LoyaltyToken` (symbol: **LPT**) is an ERC-20 token that represents loyalty points
for a business rewards programme.  The business admin (contract owner) mints points to
reward customers.  Customers can view balances, transfer points to other wallets, and
burn (redeem) their own points.

---

## Setup

```bash
cd assignment04/implementation/exercise-2
npm install
npx hardhat compile
python app/extract_abi.py     # writes app/abi.json
```

### Run locally

```bash
npx hardhat node              # terminal 1 – local blockchain
npm run deploy:local          # deploy, writes app/deployment.json
streamlit run app/app.py      # terminal 2
```

### Deploy to Sepolia (optional)

```bash
cp .env.example .env          # fill in SEPOLIA_RPC_URL and PRIVATE_KEY
npm run deploy:sepolia
streamlit run app/app.py
```

---

## Test cases

Run with `npx hardhat test`.

| # | Scenario | Expected |
|---|----------|----------|
| 1 | Deployment: name, symbol, decimals | "LoyaltyPoints", "LPT", 18 |
| 2 | Deployment: initial total supply | 0 |
| 3 | Deployment: owner is deployer | deployer address |
| 4 | Owner mints to customer | balance increases |
| 5 | Minting increases total supply | supply = sum of mints |
| 6 | Mint emits `TokensMinted` event | correct args |
| 7 | Non-owner calls mint | reverts `OwnableUnauthorizedAccount` |
| 8 | Mint to zero address | reverts `mint to zero address` |
| 9 | Mint zero amount | reverts `amount must be > 0` |
| 10 | Customer transfers tokens | balances updated correctly |
| 11 | Transfer emits ERC-20 `Transfer` event | correct args |
| 12 | Transfer more than balance | reverts `ERC20InsufficientBalance` |
| 13 | Transfer does not change total supply | supply unchanged |
| 14 | Approve + transferFrom | spender can spend approved amount |
| 15 | transferFrom emits `Approval` event | correct args |
| 16 | transferFrom exceeds allowance | reverts `ERC20InsufficientAllowance` |
| 17 | Allowance decrements after transferFrom | correct remaining allowance |
| 18 | User burns own tokens | balance decreases |
| 19 | Burn decreases total supply | supply decreases |
| 20 | Burn emits `TokensBurned` event | correct args |
| 21 | Burn more than balance | reverts `ERC20InsufficientBalance` |
| 22 | Burn zero amount | reverts `amount must be > 0` |
| 23 | burnFrom with approval | burns correctly, reduces allowance |
| 24 | burnFrom exceeds allowance | reverts |
| 25 | Multiple customers: balances independent | each tracked separately |
| 26 | Transfer between customers: supply unchanged | supply invariant holds |

---

## Design choices

### Smart contract

**Why OpenZeppelin ERC20?**
The ERC-20 standard is non-trivial to implement correctly (allowance edge cases,
integer overflow before 0.8, event signatures, etc.). OpenZeppelin's implementation
is battle-tested and formally audited.  Using it means our contract inherits that
security without adding risk.  The only custom logic we add is `mint`, `burn`, and
`burnFrom` — each is small and easy to reason about.

**Why no initial supply?**
Loyalty points are earned, not pre-distributed.  The business mints points on demand
as customers earn them.  This mirrors how real programmes work and avoids holding a
large pre-minted reserve.

**Why `burn` and `burnFrom`?**
`burn` lets users redeem their own points (destroy them in exchange for a real-world
reward handled off-chain).  `burnFrom` follows the standard allowance pattern and
allows a future redemption smart contract to burn on behalf of a user — a composable
design that does not require changes to this contract.

**Why 18 decimals?**
The ERC-20 standard defaults to 18 decimals.  Using the default keeps the token
compatible with wallets (MetaMask, Etherscan) and DeFi tooling out of the box.
The frontend displays whole points by dividing by 1e18.

**Owner cannot burn other users' tokens.**
An explicit trust boundary: the admin can increase supply (mint) but cannot
confiscate user balances.  This is important for user trust in a loyalty programme.

### What is on-chain vs off-chain

| Data / Logic | Location | Reason |
|---|---|---|
| Token balances | On-chain | Core state — must be trustless and auditable |
| Allowances | On-chain | ERC-20 standard; required for transferFrom/burnFrom |
| Total supply | On-chain | Derived by ERC-20 from mint/burn calls |
| Token name, symbol, decimals | On-chain | ERC-20 metadata standard |
| Ownership (who can mint) | On-chain | Access control must be enforced by the contract |
| Mint/transfer/burn events | On-chain (emitted) | Permanent audit trail |
| User wallet / session state | Off-chain (Streamlit) | Ephemeral UI — no value persisting on-chain |
| "Points = reward" mapping | Off-chain (business logic) | Not in scope; arbitrary business rules |

### Access control

- `onlyOwner` (from OpenZeppelin `Ownable`) guards `mint`.
- Any token holder can `transfer`, `approve`, `burn` their own balance.
- Any approved address can call `transferFrom` or `burnFrom` up to the allowance.
- No ownership transfer function is exposed — this is a homework contract.

### Gas

- `mint`: ~65 000 gas
- `transfer`: ~35 000 gas
- `burn`: ~30 000 gas

All within comfortable limits for Sepolia testnet ETH.
