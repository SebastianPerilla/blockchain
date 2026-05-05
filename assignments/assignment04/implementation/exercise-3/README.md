# Exercise 3 – ERC-721 NFT Event Tickets

## Overview

`EventTicket` (symbol: **ETKT**) is an ERC-721 NFT contract that represents event tickets.
Each ticket is a unique token with fully on-chain metadata.  The admin creates events;
users buy tickets (minting NFTs), transfer them, and trade on the built-in resale market.

---

## Setup

```bash
cd assignment04/implementation/exercise-3
npm install
npx hardhat compile
python app/extract_abi.py    # writes app/abi.json
```

### Run locally

```bash
npx hardhat node              # terminal 1
npm run deploy:local          # writes app/deployment.json
streamlit run app/app.py      # terminal 2
```

Use Account 0 (deployer) as the admin.  Accounts 1-3 are pre-funded test users.

### Deploy to Sepolia (optional)

```bash
cp .env.example .env          # fill in SEPOLIA_RPC_URL and PRIVATE_KEY
npm run deploy:sepolia
SEPOLIA_RPC_URL=... streamlit run app/app.py
```

---

## Test cases

Run with `npx hardhat test`.

| # | Scenario | Expected |
|---|----------|----------|
| 1 | Deployment: name/symbol/owner | "EventTicket" / "ETKT" / deployer |
| 2 | Initial supply | 0 |
| 3 | Owner creates event | eventCount = 1, event.active = true |
| 4 | createEvent emits EventCreated | correct args |
| 5 | Non-owner cannot create event | `OwnableUnauthorizedAccount` |
| 6 | Create event with empty name | reverts |
| 7 | Create event with 0 tickets | reverts |
| 8 | Buy ticket → NFT minted to buyer | ownerOf(1) = buyer |
| 9 | Sequential seat numbers | seat 1, seat 2, … |
| 10 | buyTicket emits TicketMinted | correct tokenId, eventId, buyer, seat |
| 11 | Refund over-payment on primary sale | net cost = price + gas |
| 12 | Buy with insufficient payment | reverts |
| 13 | Buy when sold out | reverts |
| 14 | Buy for non-existent event | reverts |
| 15 | Buy for inactive event | reverts |
| 16 | tokenURI returns data URI | starts with `data:application/json;base64,` |
| 17 | Decoded JSON has correct event name and venue | correct values |
| 18 | tokenURI reverts for non-existent token | reverts |
| 19 | Standard ERC-721 transferFrom | ownership changes |
| 20 | Transfer emits standard Transfer event | correct args |
| 21 | Standard approve + transferFrom | spender can transfer |
| 22 | listForResale sets resalePrice | correct mapping value |
| 23 | listForResale emits TicketListedForResale | correct args |
| 24 | Contract is approved after listing | getApproved(tokenId) = contract |
| 25 | Non-owner cannot list | reverts |
| 26 | List with zero price | reverts |
| 27 | List already-listed ticket | reverts |
| 28 | cancelResaleListing clears price | resalePrice = 0 |
| 29 | Cancel emits ResaleCancelled | correct args |
| 30 | Approval revoked after cancel | getApproved = address(0) |
| 31 | Non-owner cannot cancel | reverts |
| 32 | buyResaleTicket: buyer gets NFT | ownerOf = buyer |
| 33 | buyResaleTicket: seller gets ETH | balance increases by price |
| 34 | Listing cleared after sale | resalePrice = 0 |
| 35 | buyResaleTicket emits TicketResold | correct args |
| 36 | Refund surplus to buyer on resale | net cost = price + gas |
| 37 | Buy unlisted ticket | reverts |
| 38 | Insufficient payment on resale | reverts |
| 39 | Cannot buy own ticket | reverts |
| 40 | Buy → relist → buy again | second buyer gets NFT |
| 41 | totalSupply tracks minted count | correct after multiple mints |
| 42 | tokenOfOwnerByIndex enumerates correctly | returns correct token IDs |
| 43 | deactivateEvent | event.active = false |
| 44 | Non-owner cannot deactivate | reverts |
| 45 | Cannot deactivate already-inactive event | reverts |

---

## Design choices

### ERC-721 vs custom ownership (Assignment 3 approach)

The original `TicketManager` maintained a `_userTickets` mapping from address to
ticket ID arrays, and all ownership checks were hand-rolled with custom modifiers.
Replacing this with ERC-721 eliminates that bookkeeping entirely.  The ERC-721 standard
provides:

- **`ownerOf(tokenId)`** — canonical, trustless ownership
- **`balanceOf(address)`** — count of owned tokens
- **`transferFrom` / `safeTransferFrom`** — standard, composable transfers
- **`approve` / `getApproved`** — atomic approval flow
- **Wallet compatibility** — MetaMask, Etherscan, OpenSea can display tickets

The contract is significantly smaller than Assignment 3 because the standard handles
all ownership logic.

### ERC721Enumerable extension

Added to enable simple frontend enumeration of a wallet's tokens via
`tokenOfOwnerByIndex`.  Without it, the frontend would have to scan Transfer event
logs from genesis to find owned tokens — expensive and complex.  The storage cost
(two extra mappings in the extension) is justified by the clean frontend API.

### On-chain metadata vs IPFS tokenURI

| Approach | Pro | Con |
|----------|-----|-----|
| On-chain (chosen) | No external dependency; always available; immutable; censorship-resistant | Slightly more gas on mint (~5k extra for base64 encoding) |
| IPFS URI | Cheaper; supports rich media (images) | Requires pinning; link can rot; external dependency |

The metadata (event name, date, venue, seat number) is already in contract storage
from the Event struct.  Building the JSON in `tokenURI()` adds no storage cost — it
is computed at read time.  For a ticketing system, immutability matters: a ticket's
metadata should never change after issuance.  On-chain guarantees this; IPFS does not.

### Resale mechanism — using ERC-721 approve internally

`listForResale()` calls `_approve(address(this), tokenId, owner)` so the contract
itself holds approval for the token.  When a buyer calls `buyResaleTicket()`, the
contract uses `_transfer()` (the internal auth-free function) to move the NFT.  This
is safe because:

1. Price is cleared before the transfer (CEI pattern — no re-entrancy possible)
2. All conditions are validated before the transfer
3. The approval is implicitly cleared by `_transfer` (OZ clears token approval on every transfer)

The alternative (requiring the seller to manually `approve` then call `listForResale`
as two separate transactions) would be worse UX.  Our approach combines both steps
atomically.

### What is on-chain vs off-chain

| Data / Logic | Location | Reason |
|---|---|---|
| NFT ownership (`ownerOf`) | On-chain | Core ERC-721 state |
| Event details (name, date, venue, price) | On-chain | Needed for ticket validity and metadata |
| Seat assignment | On-chain | Part of ticket uniqueness |
| Resale price listings | On-chain | Price must be trustlessly verifiable |
| NFT metadata (`tokenURI`) | On-chain (generated) | Derived from event struct at read time |
| UI session state / wallet selection | Off-chain (Streamlit) | Ephemeral, no blockchain value |
| "Seat map" image / rich media | Off-chain (not in scope) | Too large for on-chain storage |

### How did the app change with ERC-721?

| Aspect | Assignment 3 (TicketManager) | This version (ERC-721) |
|--------|------------------------------|------------------------|
| Ownership source | `getUserTickets(address)` — custom mapping | `tokenOfOwnerByIndex` — ERC-721 standard |
| Transfer | `transferTicket(ticketId, to)` — custom function | `safeTransferFrom(from, to, tokenId)` — ERC-721 standard |
| Ticket display | Custom struct fields | Decode `tokenURI()` base64 JSON metadata |
| Resale | `listForResale` + `buyResaleTicket` (same concept) | Same, but approval is via ERC-721 approve pattern |
| NFT wallet visibility | Not visible in MetaMask/Etherscan | Visible in any ERC-721 compatible tool |

### Benefits of NFTs for event ticketing

1. **Composability** — tickets can be traded on any ERC-721 marketplace (OpenSea, etc.) without changes to the contract
2. **No custom ownership tracking** — ERC-721 handles it; less code means fewer bugs
3. **Wallet-native** — MetaMask shows the ticket in the user's wallet automatically
4. **Provable scarcity** — `totalSupply()` is verifiable on-chain; no double-minting possible
5. **Immutable metadata** — `tokenURI()` is computed from contract state and cannot be altered after issuance
6. **Standard composability** — future extensions (royalties via ERC-2981, soulbound via ERC-5192) can be added without redesigning the core
