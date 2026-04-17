### Smart Contracts and DApp Development

[GitHub Repo Link](https://github.com/SebastianPerilla/blockchain/edit/main/assignments/assignment03/README.md)

Smart contracts, on chain state, off chain logic, and application design In class, we discussed smart contracts, blockchain state, transactions, wallets, contract functions, events, gas costs, and the di8erence between logic that should live on chain and logic that should stay o8 chain. We also discussed that a decentralized application is not only a smart contract, but a full application made up of smart contracts, a frontend, and often a database.

In this assignment, you will work on Ethereum compatible smart contracts and build small applications that help you understand how a decentralized application is designed and implemented. The focus of the assignment is not only to make the application work, but also to make clear design choices about what should go on chain, what should stay o8 chain, and why. The goal of this assignment is to help you get a feel for developing a real dApp. You will deploy smart contracts, connect them to a frontend, send transactions from a wallet, read on chain state, and reason about the trade o8s of your design.

### Minimum Contract Quality Requirements

1. Validate Important Inputs and reject invalid actions
2. Use Clear Error Handling with require(...), revert(...), or custom errors where appropriate
3. Emit events for important state changes
4. Include at least one restricted function for admin only actions where relevant
5. Keey the contract design simple and avoid uneccesary storage or unecessary features
6. Document the purpose of each public function with short comments
7. Think carefully about who is allowed to call each function and when

