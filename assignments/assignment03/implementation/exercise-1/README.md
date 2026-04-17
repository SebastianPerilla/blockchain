# Exercise 1: Build a Vending Machine dApp

In this Exercise you will design and implement a vending machine application as a web3 app. The application should simulate a digital vending machine that sells different items. A user:

1. Connects a wallet
2. Sees the available items
3. Buys one or more items
4. Becomes the owner of the purchased items inside the application

## Your solution much include:

1. A solidity smart contract(s) that models the vending Machine
2. A python client (or frontend GUI) that interacts with the contract through a wallet
3. The vending machine smart contract should have several items for sale
4. A way to track which user owns which purchased items
5. A way to show the current stock and item availability

## Minimum Technical Requirements for Exercise 1

Your vending machine solution must include at least the following features:

1. At least three different products
2. A price for each product 
3. A stock quantity for each product
4. A purchase function that allows a user to buy one or more items
5. Validation for insufficient payment
6. Validation for out of stock items
7. Ownership tracking so that purchased items can be linked to the buyer
8. At least two events one for purchases and one for restocking or product updates
9. A frontend or client that clearly shows product information current stock, ownership, and transaction status

### Testing Requirements for Exercise 1

In this exercise we will also learn how to test the smart contract. In hardhat in the test folder ou can put your test script (eg. test.ts), write the test cases and then run them using npx hardhat test. Testing is a required part of the submission.

Your much include at least five tests for the smart contract logic. Your tests much include:

1. At least one successful purchase
2. At least one failed purchase due to insufficient payment
3. At least on failed purchase due to unavailable stock
4. At least one permission failure for example a non admin user trying to restocking
5. At least one test that checks state changes after a successfull transaction.

Good tests should not only show that the contract works in one happy path case, but also show what happens when users make mistakes or try invalid actions


# Proposed Solution:

- I will make this vending machine application using python streamlit (probably) to have the gui where people can interact with it. This means that the interface will be there and I can show the requirements necessary there:










