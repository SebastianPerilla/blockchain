
## Exercise 2: Build a web2 version and web3 version of the same app

In this exercise you will implment the same application twice, once as a normal web2 app, and once as a web3 app.

The goal is to understand what belongs on chain, what should remain off chain and what changes when trust is handled by a smart contract instead of a centralized backend.

### Proposed app: Event Ticket booking and resale

You will build an application where users can browse events, buy tickets, and transfer or resell them.

#### Part A: web2 version

Implement a web2 version of the application. You may use any backend and frontend stack you want. Scalbility for your app is also not important just show the main functionality.

The web2 app much support at least:

- Event creation by an admin
- Ticket purchase by users
- Ticket ownership tracking
- Transfer or resale of tickets


#### Part B: web3 version

Implement a decentralized version of the same app. You can re-use the same front-end from the web2 app and use a web3 to connect the frontend to the smart contracts.

## Minimum Technical Requirements for Exercise 2:

Your solution for Exercise 2 must implement the same core ticketing application in both a web2 version and a web3 version

__The web2 version much include at least__:

1. Creation of at least two events
2. At least two different users who can buy tickets
3. Ticket ownership tracking
4. Ticket transfer or resale functionality
5. At least one admin only action, such as event creation or ticket release
6. Persistent storage for users, events, and ticket ownership
7. A simple interface or terminal client that allows a user to view events , buy tickets, and view owned tickets

The web3 version must include at least:

Solidity smart contract for ticket management
Creation of at least two events or ticketed offerings
Ticket purchase functionality through blockchain transactions
Tricket ownership functionality
ticket transfer functionality
resale functionality
at least one admin only funnction, such as event creation, ticket issuance, or price update
re-use the same front-end/client from the web2 app and use web3 to connect the frontend to the smart contracts

## Testing Requirements for Exercise web2

Testing is also a required part of this exercise. You must include at least eight test in total for the web3 version. your tests must include:

1. Successful ticket purchase
2. Failed purchase when the rules are not satisfied
3. Successful transfer of a ticket
4. Failed transfer by a user who is not the ownership
5. Successful resale flow
6. At least one permission failure involving an admin only action
7. At least one edge case involving repeated or invalid state transitions
8. At least one test that checks final ownership after a sequence of actions

For this exercise, also include a short README.md file in the implementation folder that explains:

- How you tested the project, what were your tests cases
- The Main design choices, especially what is on chain and what is off chain
- Include a short comparison section in where you explain the difference between the web2 and web3 versions of your app

---

## Implementation Notes

### How to Run

#### Prerequisites
- Python 3.10+, `pip install streamlit web3`
- Node.js 18+, then inside `exercise-2/`: `npm install`

#### Web2 app
```bash
streamlit run app/web2_app.py
```
Switch between **admin**, **alice**, and **bob** in the sidebar.  
The SQLite database (`app/web2_tickets.db`) is created automatically and seeded with two events on first run.

#### Web3 app

**Terminal 1** — start the local Hardhat node:
```bash
npx hardhat node
```

**Terminal 2** — compile and deploy:
```bash
npx hardhat compile
npx hardhat run scripts/deploy.js --network localhost
```

**Terminal 3** — launch the Streamlit app:
```bash
streamlit run app/web3_app.py
```
Select any of the five pre-funded Hardhat accounts from the sidebar.  
Account 0 is the admin (contract deployer).

#### Running the tests
```bash
npx hardhat test
```

---

### Test Cases

The test file `tests/TicketManager.test.js` contains 10 tests:

| # | Description | Category |
|---|-------------|----------|
| 1 | User buys a ticket with the exact price | Successful purchase |
| 2a | Purchase fails when ETH sent is below the ticket price | Failed purchase |
| 2b | Purchase fails when the event capacity is exhausted | Failed purchase |
| 3 | Owner transfers a ticket; ownership arrays updated | Successful transfer |
| 4 | A non-owner cannot transfer someone else's ticket | Failed transfer |
| 5 | Full resale cycle: list, verify listing, buy, verify new owner | Successful resale |
| 6 | Non-admin account cannot create an event | Permission failure |
| 7 | Cannot transfer a ticket that is currently listed for resale; cancel + retry succeeds | Edge-case / invalid state |
| 8 | buy → transfer → resale → final owner checked end-to-end | Final ownership sequence |
| 9 | Non-admin cannot deactivate an event | Second permission failure |

All 10 tests pass against the in-process Hardhat EVM.

---

### Design Choices

#### What is on-chain (Web3)

| Data / Logic | Why on-chain |
|---|---|
| Event definitions (name, date, venue, price, capacity) | Immutable public record; anyone can verify |
| Ticket NFT-like records (owner, resale status) | Ownership must be trustless and transferable |
| `buyTicket`, `transferTicket`, `listForResale`, `buyResaleTicket` | Value exchange and ownership transfer — must be atomic |
| `onlyAdmin` guard on `createEvent` / `deactivateEvent` | Enforced by the EVM, not by a server |
| ETH escrow and payout during resale | Trustless payment — no intermediary needed |

#### What is off-chain (Web3)

| Data / Logic | Why off-chain |
|---|---|
| User-facing labels (account nicknames) | Convenience only; addresses are the real identity |
| Frontend state (spinner, session) | UI concern; not worth the gas |
| Human-readable event images, descriptions | Storage cost on-chain is prohibitive for blobs |

#### Web2 — everything off-chain

All state lives in a SQLite database managed by the Python server.  
The admin privilege is enforced only by the application code — any database modification can override it.  
Ticket ownership is a table row; moving it requires trusting the server.

---

### Web2 vs Web3 Comparison

| Aspect | Web2 (SQLite) | Web3 (Smart Contract) |
|---|---|---|
| **Trust model** | Trust the server operator | Trust the EVM code (verifiable by anyone) |
| **Ownership proof** | A row in the `tickets` table | An on-chain mapping; proven by signing a message |
| **Admin enforcement** | `if role == "admin"` in Python | `require(msg.sender == admin)` — cannot be bypassed |
| **Resale payment** | Simulated (no real money) | Atomic ETH transfer in the same transaction |
| **Persistence** | Local file (`web2_tickets.db`) | Distributed across all Ethereum nodes |
| **Censorship** | Server owner can alter or delete any record | Contract state is immutable once deployed |
| **Cost** | Free (SQLite is free) | Gas fees per write transaction |
| **Speed** | Milliseconds | ~1–15 s per block confirmation |
| **Privacy** | Server can see everything | All state is public on-chain |
| **Frontend** | Streamlit + `sqlite3` | Same Streamlit layout + `web3.py` |

**Key insight:** the Web3 version shifts the enforcement of business rules from "trust the server" to "trust the code." The frontend is nearly identical — the only differences are how data is read (contract calls instead of SQL queries) and how writes are performed (signed transactions instead of DB updates).
