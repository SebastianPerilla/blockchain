import { expect } from "chai";
import { ethers } from "hardhat";
import { VendingMachine } from "../typechain-types";
import { HardhatEthersSigner } from "@nomicfoundation/hardhat-ethers/signers";

describe("VendingMachine", function () {
  let vendingMachine: VendingMachine;
  let owner: HardhatEthersSigner;
  let buyer: HardhatEthersSigner;
  let stranger: HardhatEthersSigner;

  // Product IDs seeded in constructor
  const COLA_ID      = 0;
  const CHIPS_ID     = 1;
  const CHOC_ID      = 2;

  const COLA_PRICE   = ethers.parseEther("0.001");
  const CHIPS_PRICE  = ethers.parseEther("0.002");

  beforeEach(async function () {
    [owner, buyer, stranger] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("VendingMachine");
    vendingMachine = (await Factory.deploy()) as VendingMachine;
    await vendingMachine.waitForDeployment();
  });

  // ─── 1. Successful purchase ────────────────────────────────────────────────

  describe("purchase()", function () {
    it("allows a buyer to purchase one Cola", async function () {
      await expect(
        vendingMachine.connect(buyer).purchase(COLA_ID, 1, { value: COLA_PRICE })
      ).to.emit(vendingMachine, "ItemPurchased")
        .withArgs(buyer.address, COLA_ID, "Cola", 1n, COLA_PRICE);

      const owned = await vendingMachine.getOwnedQuantity(buyer.address, COLA_ID);
      expect(owned).to.equal(1n);
    });

    it("decrements stock after a successful purchase", async function () {
      const [, , , stocksBefore] = await vendingMachine.getAllProducts();
      const colaBefore = stocksBefore[COLA_ID];

      await vendingMachine.connect(buyer).purchase(COLA_ID, 2, { value: COLA_PRICE * 2n });

      const [, , , stocksAfter] = await vendingMachine.getAllProducts();
      expect(stocksAfter[COLA_ID]).to.equal(colaBefore - 2n);
    });

    it("refunds over-payment", async function () {
      const overpayment = COLA_PRICE + ethers.parseEther("1");
      const balanceBefore = await ethers.provider.getBalance(buyer.address);

      const tx = await vendingMachine
        .connect(buyer)
        .purchase(COLA_ID, 1, { value: overpayment });
      const receipt = await tx.wait();
      const gasUsed = receipt!.gasUsed * receipt!.gasPrice;

      const balanceAfter = await ethers.provider.getBalance(buyer.address);
      // net cost = COLA_PRICE + gas (not the full over-payment)
      const netSpent = balanceBefore - balanceAfter;
      expect(netSpent).to.equal(COLA_PRICE + gasUsed);
    });

    it("accumulates contract balance correctly across multiple buyers", async function () {
      await vendingMachine.connect(buyer).purchase(COLA_ID, 1, { value: COLA_PRICE });
      await vendingMachine.connect(stranger).purchase(CHIPS_ID, 1, { value: CHIPS_PRICE });

      const balance = await vendingMachine.contractBalance();
      expect(balance).to.equal(COLA_PRICE + CHIPS_PRICE);
    });

    // ─── 2. Insufficient payment ──────────────────────────────────────────────

    it("reverts when payment is too low", async function () {
      const tooLittle = COLA_PRICE - 1n;
      await expect(
        vendingMachine.connect(buyer).purchase(COLA_ID, 1, { value: tooLittle })
      ).to.be.revertedWith("VendingMachine: insufficient payment");
    });

    it("reverts when paying nothing", async function () {
      await expect(
        vendingMachine.connect(buyer).purchase(COLA_ID, 1, { value: 0n })
      ).to.be.revertedWith("VendingMachine: insufficient payment");
    });

    // ─── 3. Out of stock ─────────────────────────────────────────────────────

    it("reverts when quantity exceeds stock", async function () {
      // Chocolate has initial stock of 5
      await expect(
        vendingMachine.connect(buyer).purchase(CHOC_ID, 99, {
          value: ethers.parseEther("0.003") * 99n,
        })
      ).to.be.revertedWith("VendingMachine: insufficient stock");
    });

    it("reverts when stock is fully depleted and buyer tries again", async function () {
      // Deplete the 5 Chocolates
      await vendingMachine.connect(buyer).purchase(CHOC_ID, 5, {
        value: ethers.parseEther("0.003") * 5n,
      });

      await expect(
        vendingMachine.connect(buyer).purchase(CHOC_ID, 1, {
          value: ethers.parseEther("0.003"),
        })
      ).to.be.revertedWith("VendingMachine: insufficient stock");
    });

    // ─── 5. State changes after purchase ──────────────────────────────────────

    it("tracks ownership across multiple purchases by the same buyer", async function () {
      await vendingMachine.connect(buyer).purchase(COLA_ID, 2, { value: COLA_PRICE * 2n });
      await vendingMachine.connect(buyer).purchase(COLA_ID, 3, { value: COLA_PRICE * 3n });

      const owned = await vendingMachine.getOwnedQuantity(buyer.address, COLA_ID);
      expect(owned).to.equal(5n);
    });

    it("tracks ownership independently per buyer", async function () {
      await vendingMachine.connect(buyer).purchase(CHIPS_ID, 1, { value: CHIPS_PRICE });
      await vendingMachine.connect(stranger).purchase(CHIPS_ID, 2, { value: CHIPS_PRICE * 2n });

      expect(await vendingMachine.getOwnedQuantity(buyer.address, CHIPS_ID)).to.equal(1n);
      expect(await vendingMachine.getOwnedQuantity(stranger.address, CHIPS_ID)).to.equal(2n);
    });
  });

  // ─── 4. Permission failures ───────────────────────────────────────────────

  describe("Admin functions", function () {
    it("non-owner cannot restock", async function () {
      await expect(
        vendingMachine.connect(buyer).restock(COLA_ID, 5)
      ).to.be.revertedWith("VendingMachine: caller is not the owner");
    });

    it("non-owner cannot add a product", async function () {
      await expect(
        vendingMachine.connect(buyer).addProduct("Water", ethers.parseEther("0.001"), 10)
      ).to.be.revertedWith("VendingMachine: caller is not the owner");
    });

    it("non-owner cannot change price", async function () {
      await expect(
        vendingMachine.connect(buyer).setPrice(COLA_ID, ethers.parseEther("0.005"))
      ).to.be.revertedWith("VendingMachine: caller is not the owner");
    });

    it("non-owner cannot withdraw funds", async function () {
      await vendingMachine.connect(buyer).purchase(COLA_ID, 1, { value: COLA_PRICE });
      await expect(
        vendingMachine.connect(buyer).withdraw()
      ).to.be.revertedWith("VendingMachine: caller is not the owner");
    });

    it("owner can restock and emit ProductRestocked event", async function () {
      const [, , , stocksBefore] = await vendingMachine.getAllProducts();
      const before = stocksBefore[COLA_ID];

      await expect(vendingMachine.connect(owner).restock(COLA_ID, 5))
        .to.emit(vendingMachine, "ProductRestocked")
        .withArgs(COLA_ID, "Cola", before + 5n);

      const [, , , stocksAfter] = await vendingMachine.getAllProducts();
      expect(stocksAfter[COLA_ID]).to.equal(before + 5n);
    });

    it("owner can add a new product", async function () {
      const countBefore = await vendingMachine.productCount();
      await vendingMachine.connect(owner).addProduct("Energy Drink", ethers.parseEther("0.004"), 3);
      expect(await vendingMachine.productCount()).to.equal(countBefore + 1n);
    });

    it("owner can withdraw accumulated ETH", async function () {
      await vendingMachine.connect(buyer).purchase(COLA_ID, 1, { value: COLA_PRICE });
      const ownerBefore = await ethers.provider.getBalance(owner.address);
      const tx = await vendingMachine.connect(owner).withdraw();
      const receipt = await tx.wait();
      const gas = receipt!.gasUsed * receipt!.gasPrice;
      const ownerAfter = await ethers.provider.getBalance(owner.address);
      expect(ownerAfter).to.equal(ownerBefore + COLA_PRICE - gas);
    });
  });

  // ─── View helpers ─────────────────────────────────────────────────────────

  describe("getAllProducts()", function () {
    it("returns all three seeded products", async function () {
      const [ids, names, prices, stocks] = await vendingMachine.getAllProducts();
      expect(ids.length).to.equal(3);
      expect(names[0]).to.equal("Cola");
      expect(names[1]).to.equal("Chips");
      expect(names[2]).to.equal("Chocolate Bar");
      expect(prices[0]).to.equal(COLA_PRICE);
      expect(stocks[0]).to.equal(10n);
    });
  });
});
