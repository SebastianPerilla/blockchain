import { expect } from "chai";
import { ethers } from "hardhat";
import { LoyaltyToken } from "../typechain-types";
import { HardhatEthersSigner } from "@nomicfoundation/hardhat-ethers/signers";

describe("LoyaltyToken", function () {
  let token: LoyaltyToken;
  let owner: HardhatEthersSigner;
  let alice: HardhatEthersSigner;
  let bob: HardhatEthersSigner;
  let stranger: HardhatEthersSigner;

  const HUNDRED = ethers.parseUnits("100", 18);
  const FIFTY   = ethers.parseUnits("50",  18);
  const TEN     = ethers.parseUnits("10",  18);
  const ONE     = ethers.parseUnits("1",   18);

  beforeEach(async function () {
    [owner, alice, bob, stranger] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("LoyaltyToken");
    token = (await Factory.deploy("LoyaltyPoints", "LPT")) as LoyaltyToken;
    await token.waitForDeployment();
  });

  // ─── 1. Deployment ─────────────────────────────────────────────────────────

  describe("Deployment", function () {
    it("sets the token name and symbol", async function () {
      expect(await token.name()).to.equal("LoyaltyPoints");
      expect(await token.symbol()).to.equal("LPT");
    });

    it("starts with zero total supply", async function () {
      expect(await token.totalSupply()).to.equal(0n);
    });

    it("sets the deployer as owner", async function () {
      expect(await token.owner()).to.equal(owner.address);
    });

    it("uses 18 decimals (ERC-20 standard)", async function () {
      expect(await token.decimals()).to.equal(18);
    });
  });

  // ─── 2. Minting ───────────────────────────────────────────────────────────

  describe("mint()", function () {
    it("owner can mint tokens to a customer", async function () {
      await token.connect(owner).mint(alice.address, HUNDRED);
      expect(await token.balanceOf(alice.address)).to.equal(HUNDRED);
    });

    it("minting increases total supply", async function () {
      await token.connect(owner).mint(alice.address, HUNDRED);
      await token.connect(owner).mint(bob.address, FIFTY);
      expect(await token.totalSupply()).to.equal(HUNDRED + FIFTY);
    });

    it("emits TokensMinted event", async function () {
      await expect(token.connect(owner).mint(alice.address, HUNDRED))
        .to.emit(token, "TokensMinted")
        .withArgs(alice.address, HUNDRED);
    });

    it("non-owner cannot mint", async function () {
      await expect(
        token.connect(alice).mint(alice.address, HUNDRED)
      ).to.be.revertedWithCustomError(token, "OwnableUnauthorizedAccount");
    });

    it("reverts when minting to zero address", async function () {
      await expect(
        token.connect(owner).mint(ethers.ZeroAddress, HUNDRED)
      ).to.be.revertedWith("LoyaltyToken: mint to zero address");
    });

    it("reverts when minting zero amount", async function () {
      await expect(
        token.connect(owner).mint(alice.address, 0)
      ).to.be.revertedWith("LoyaltyToken: amount must be > 0");
    });
  });

  // ─── 3. Transfer ─────────────────────────────────────────────────────────

  describe("transfer()", function () {
    beforeEach(async function () {
      await token.connect(owner).mint(alice.address, HUNDRED);
    });

    it("user can transfer tokens to another wallet", async function () {
      await token.connect(alice).transfer(bob.address, FIFTY);
      expect(await token.balanceOf(alice.address)).to.equal(FIFTY);
      expect(await token.balanceOf(bob.address)).to.equal(FIFTY);
    });

    it("emits ERC-20 Transfer event", async function () {
      await expect(token.connect(alice).transfer(bob.address, TEN))
        .to.emit(token, "Transfer")
        .withArgs(alice.address, bob.address, TEN);
    });

    it("reverts when transferring more than balance", async function () {
      const tooMuch = HUNDRED + ONE;
      await expect(
        token.connect(alice).transfer(bob.address, tooMuch)
      ).to.be.revertedWithCustomError(token, "ERC20InsufficientBalance");
    });

    it("total supply does not change on transfer", async function () {
      const supplyBefore = await token.totalSupply();
      await token.connect(alice).transfer(bob.address, FIFTY);
      expect(await token.totalSupply()).to.equal(supplyBefore);
    });
  });

  // ─── 4. Approve + transferFrom ────────────────────────────────────────────

  describe("approve() + transferFrom()", function () {
    beforeEach(async function () {
      await token.connect(owner).mint(alice.address, HUNDRED);
    });

    it("approved address can spend on behalf of owner", async function () {
      await token.connect(alice).approve(bob.address, FIFTY);
      await token.connect(bob).transferFrom(alice.address, stranger.address, FIFTY);
      expect(await token.balanceOf(stranger.address)).to.equal(FIFTY);
      expect(await token.balanceOf(alice.address)).to.equal(FIFTY);
    });

    it("emits Approval event", async function () {
      await expect(token.connect(alice).approve(bob.address, TEN))
        .to.emit(token, "Approval")
        .withArgs(alice.address, bob.address, TEN);
    });

    it("reverts when spending more than allowance", async function () {
      await token.connect(alice).approve(bob.address, TEN);
      await expect(
        token.connect(bob).transferFrom(alice.address, stranger.address, FIFTY)
      ).to.be.revertedWithCustomError(token, "ERC20InsufficientAllowance");
    });

    it("allowance decreases after transferFrom", async function () {
      await token.connect(alice).approve(bob.address, FIFTY);
      await token.connect(bob).transferFrom(alice.address, stranger.address, TEN);
      expect(await token.allowance(alice.address, bob.address)).to.equal(FIFTY - TEN);
    });
  });

  // ─── 5. Burn ─────────────────────────────────────────────────────────────

  describe("burn()", function () {
    beforeEach(async function () {
      await token.connect(owner).mint(alice.address, HUNDRED);
    });

    it("user can burn their own tokens", async function () {
      await token.connect(alice).burn(TEN);
      expect(await token.balanceOf(alice.address)).to.equal(HUNDRED - TEN);
    });

    it("burn decreases total supply", async function () {
      const supplyBefore = await token.totalSupply();
      await token.connect(alice).burn(TEN);
      expect(await token.totalSupply()).to.equal(supplyBefore - TEN);
    });

    it("emits TokensBurned event", async function () {
      await expect(token.connect(alice).burn(TEN))
        .to.emit(token, "TokensBurned")
        .withArgs(alice.address, TEN);
    });

    it("reverts when burning more than balance", async function () {
      const tooMuch = HUNDRED + ONE;
      await expect(
        token.connect(alice).burn(tooMuch)
      ).to.be.revertedWithCustomError(token, "ERC20InsufficientBalance");
    });

    it("reverts when burning zero", async function () {
      await expect(
        token.connect(alice).burn(0)
      ).to.be.revertedWith("LoyaltyToken: amount must be > 0");
    });
  });

  // ─── 6. burnFrom ─────────────────────────────────────────────────────────

  describe("burnFrom()", function () {
    beforeEach(async function () {
      await token.connect(owner).mint(alice.address, HUNDRED);
    });

    it("approved address can burn on behalf of token holder", async function () {
      await token.connect(alice).approve(bob.address, FIFTY);
      await token.connect(bob).burnFrom(alice.address, TEN);
      expect(await token.balanceOf(alice.address)).to.equal(HUNDRED - TEN);
      expect(await token.allowance(alice.address, bob.address)).to.equal(FIFTY - TEN);
    });

    it("reverts when burning more than allowance", async function () {
      await token.connect(alice).approve(bob.address, TEN);
      await expect(
        token.connect(bob).burnFrom(alice.address, FIFTY)
      ).to.be.revertedWithCustomError(token, "ERC20InsufficientAllowance");
    });
  });

  // ─── 7. Multiple customers ────────────────────────────────────────────────

  describe("Multi-customer scenarios", function () {
    it("each customer's balance is tracked independently", async function () {
      await token.connect(owner).mint(alice.address, HUNDRED);
      await token.connect(owner).mint(bob.address, FIFTY);
      expect(await token.balanceOf(alice.address)).to.equal(HUNDRED);
      expect(await token.balanceOf(bob.address)).to.equal(FIFTY);
    });

    it("transfer between two customers leaves total supply unchanged", async function () {
      await token.connect(owner).mint(alice.address, HUNDRED);
      await token.connect(owner).mint(bob.address, FIFTY);
      const supplyBefore = await token.totalSupply();
      await token.connect(alice).transfer(bob.address, TEN);
      expect(await token.totalSupply()).to.equal(supplyBefore);
      expect(await token.balanceOf(alice.address)).to.equal(HUNDRED - TEN);
      expect(await token.balanceOf(bob.address)).to.equal(FIFTY + TEN);
    });
  });
});
