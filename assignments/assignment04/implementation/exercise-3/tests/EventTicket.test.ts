import { expect } from "chai";
import { ethers } from "hardhat";
import { EventTicket } from "../typechain-types";
import { HardhatEthersSigner } from "@nomicfoundation/hardhat-ethers/signers";

describe("EventTicket", function () {
  let contract: EventTicket;
  let owner: HardhatEthersSigner;
  let alice: HardhatEthersSigner;
  let bob: HardhatEthersSigner;
  let carol: HardhatEthersSigner;

  const PRICE = ethers.parseEther("0.01");
  const TOTAL = 10n;

  async function createEvent(
    name = "Concert",
    date = "2025-12-01",
    venue = "Arena",
    price = PRICE,
    total = TOTAL
  ) {
    return contract.connect(owner).createEvent(name, date, venue, price, total);
  }

  beforeEach(async function () {
    [owner, alice, bob, carol] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("EventTicket");
    contract = (await Factory.deploy()) as EventTicket;
    await contract.waitForDeployment();
  });

  // ─── 1. Deployment ─────────────────────────────────────────────────────────

  describe("Deployment", function () {
    it("sets correct ERC-721 name and symbol", async function () {
      expect(await contract.name()).to.equal("EventTicket");
      expect(await contract.symbol()).to.equal("ETKT");
    });

    it("sets the deployer as owner", async function () {
      expect(await contract.owner()).to.equal(owner.address);
    });

    it("starts with zero events and zero supply", async function () {
      expect(await contract.eventCount()).to.equal(0n);
      expect(await contract.totalSupply()).to.equal(0n);
    });
  });

  // ─── 2. createEvent ────────────────────────────────────────────────────────

  describe("createEvent()", function () {
    it("owner can create an event", async function () {
      await createEvent();
      expect(await contract.eventCount()).to.equal(1n);
      const ev = await contract.events(1);
      expect(ev.name).to.equal("Concert");
      expect(ev.active).to.be.true;
    });

    it("emits EventCreated", async function () {
      await expect(createEvent())
        .to.emit(contract, "EventCreated")
        .withArgs(1n, "Concert", PRICE, TOTAL);
    });

    it("non-owner cannot create an event", async function () {
      await expect(createEvent.call(null)).not.to.throw; // sanity
      await expect(
        contract.connect(alice).createEvent("X", "2025-01-01", "Venue", PRICE, TOTAL)
      ).to.be.revertedWithCustomError(contract, "OwnableUnauthorizedAccount");
    });

    it("reverts on empty name", async function () {
      await expect(
        contract.connect(owner).createEvent("", "2025-01-01", "Venue", PRICE, TOTAL)
      ).to.be.revertedWith("EventTicket: name required");
    });

    it("reverts when totalTickets is zero", async function () {
      await expect(
        contract.connect(owner).createEvent("X", "2025-01-01", "Venue", PRICE, 0)
      ).to.be.revertedWith("EventTicket: must have at least one ticket");
    });
  });

  // ─── 3. buyTicket ──────────────────────────────────────────────────────────

  describe("buyTicket()", function () {
    beforeEach(async function () {
      await createEvent();
    });

    it("mints an NFT to the buyer", async function () {
      await contract.connect(alice).buyTicket(1, { value: PRICE });
      expect(await contract.ownerOf(1)).to.equal(alice.address);
      expect(await contract.balanceOf(alice.address)).to.equal(1n);
    });

    it("assigns sequential seat numbers", async function () {
      await contract.connect(alice).buyTicket(1, { value: PRICE });
      await contract.connect(bob).buyTicket(1, { value: PRICE });
      const [, seat1] = await contract.getTicketInfo(1);
      const [, seat2] = await contract.getTicketInfo(2);
      expect(seat1).to.equal(1n);
      expect(seat2).to.equal(2n);
    });

    it("emits TicketMinted with correct args", async function () {
      await expect(contract.connect(alice).buyTicket(1, { value: PRICE }))
        .to.emit(contract, "TicketMinted")
        .withArgs(1n, 1n, alice.address, 1n);
    });

    it("refunds over-payment", async function () {
      const overpay = PRICE + ethers.parseEther("1");
      const before  = await ethers.provider.getBalance(alice.address);
      const tx      = await contract.connect(alice).buyTicket(1, { value: overpay });
      const receipt = await tx.wait();
      const gas     = receipt!.gasUsed * receipt!.gasPrice;
      const after   = await ethers.provider.getBalance(alice.address);
      expect(before - after).to.equal(PRICE + gas);
    });

    it("reverts on insufficient payment", async function () {
      await expect(
        contract.connect(alice).buyTicket(1, { value: PRICE - 1n })
      ).to.be.revertedWith("EventTicket: insufficient payment");
    });

    it("reverts when sold out", async function () {
      // TOTAL = 10; buy all of them
      for (let i = 0; i < 10; i++) {
        await contract.connect(alice).buyTicket(1, { value: PRICE });
      }
      await expect(
        contract.connect(bob).buyTicket(1, { value: PRICE })
      ).to.be.revertedWith("EventTicket: sold out");
    });

    it("reverts on non-existent event", async function () {
      await expect(
        contract.connect(alice).buyTicket(99, { value: PRICE })
      ).to.be.revertedWith("EventTicket: event does not exist");
    });

    it("reverts on inactive event", async function () {
      await contract.connect(owner).deactivateEvent(1);
      await expect(
        contract.connect(alice).buyTicket(1, { value: PRICE })
      ).to.be.revertedWith("EventTicket: event not active");
    });
  });

  // ─── 4. tokenURI ──────────────────────────────────────────────────────────

  describe("tokenURI()", function () {
    beforeEach(async function () {
      await createEvent("Rock Night", "2025-12-25", "Stadium");
      await contract.connect(alice).buyTicket(1, { value: PRICE });
    });

    it("returns a data URI", async function () {
      const uri = await contract.tokenURI(1);
      expect(uri).to.match(/^data:application\/json;base64,/);
    });

    it("decoded JSON contains correct event name", async function () {
      const uri  = await contract.tokenURI(1);
      const b64  = uri.replace("data:application/json;base64,", "");
      const json = JSON.parse(Buffer.from(b64, "base64").toString("utf8"));
      expect(json.name).to.include("Rock Night");
      expect(json.attributes.find((a: any) => a.trait_type === "Venue").value).to.equal("Stadium");
      expect(json.attributes.find((a: any) => a.trait_type === "Seat").value).to.equal(1);
    });

    it("reverts for non-existent token", async function () {
      await expect(contract.tokenURI(999))
        .to.be.revertedWith("EventTicket: token does not exist");
    });
  });

  // ─── 5. Standard ERC-721 transfers ────────────────────────────────────────

  describe("ERC-721 standard transfers", function () {
    beforeEach(async function () {
      await createEvent();
      await contract.connect(alice).buyTicket(1, { value: PRICE });
    });

    it("owner can directly transfer their ticket to another wallet", async function () {
      await contract.connect(alice).transferFrom(alice.address, bob.address, 1);
      expect(await contract.ownerOf(1)).to.equal(bob.address);
    });

    it("emits standard Transfer event", async function () {
      await expect(contract.connect(alice).transferFrom(alice.address, bob.address, 1))
        .to.emit(contract, "Transfer")
        .withArgs(alice.address, bob.address, 1n);
    });

    it("approve + transferFrom works", async function () {
      await contract.connect(alice).approve(bob.address, 1);
      await contract.connect(bob).transferFrom(alice.address, carol.address, 1);
      expect(await contract.ownerOf(1)).to.equal(carol.address);
    });
  });

  // ─── 6. listForResale ─────────────────────────────────────────────────────

  describe("listForResale()", function () {
    beforeEach(async function () {
      await createEvent();
      await contract.connect(alice).buyTicket(1, { value: PRICE });
    });

    it("owner can list ticket for resale", async function () {
      await contract.connect(alice).listForResale(1, PRICE * 2n);
      expect(await contract.resalePrice(1)).to.equal(PRICE * 2n);
    });

    it("emits TicketListedForResale", async function () {
      await expect(contract.connect(alice).listForResale(1, PRICE * 2n))
        .to.emit(contract, "TicketListedForResale")
        .withArgs(1n, PRICE * 2n);
    });

    it("contract is approved for the token after listing", async function () {
      await contract.connect(alice).listForResale(1, PRICE * 2n);
      expect(await contract.getApproved(1)).to.equal(await contract.getAddress());
    });

    it("non-owner cannot list", async function () {
      await expect(
        contract.connect(bob).listForResale(1, PRICE)
      ).to.be.revertedWith("EventTicket: not the ticket owner");
    });

    it("cannot list with zero price", async function () {
      await expect(
        contract.connect(alice).listForResale(1, 0n)
      ).to.be.revertedWith("EventTicket: price must be > 0");
    });

    it("cannot list an already-listed ticket", async function () {
      await contract.connect(alice).listForResale(1, PRICE);
      await expect(
        contract.connect(alice).listForResale(1, PRICE)
      ).to.be.revertedWith("EventTicket: already listed");
    });
  });

  // ─── 7. cancelResaleListing ───────────────────────────────────────────────

  describe("cancelResaleListing()", function () {
    beforeEach(async function () {
      await createEvent();
      await contract.connect(alice).buyTicket(1, { value: PRICE });
      await contract.connect(alice).listForResale(1, PRICE * 2n);
    });

    it("owner can cancel the listing", async function () {
      await contract.connect(alice).cancelResaleListing(1);
      expect(await contract.resalePrice(1)).to.equal(0n);
    });

    it("emits ResaleCancelled", async function () {
      await expect(contract.connect(alice).cancelResaleListing(1))
        .to.emit(contract, "ResaleCancelled")
        .withArgs(1n);
    });

    it("approval is revoked after cancellation", async function () {
      await contract.connect(alice).cancelResaleListing(1);
      expect(await contract.getApproved(1)).to.equal(ethers.ZeroAddress);
    });

    it("non-owner cannot cancel", async function () {
      await expect(
        contract.connect(bob).cancelResaleListing(1)
      ).to.be.revertedWith("EventTicket: not the ticket owner");
    });
  });

  // ─── 8. buyResaleTicket ───────────────────────────────────────────────────

  describe("buyResaleTicket()", function () {
    const RESALE = PRICE * 2n;

    beforeEach(async function () {
      await createEvent();
      await contract.connect(alice).buyTicket(1, { value: PRICE });
      await contract.connect(alice).listForResale(1, RESALE);
    });

    it("buyer receives the NFT", async function () {
      await contract.connect(bob).buyResaleTicket(1, { value: RESALE });
      expect(await contract.ownerOf(1)).to.equal(bob.address);
    });

    it("seller receives the ETH", async function () {
      const before = await ethers.provider.getBalance(alice.address);
      await contract.connect(bob).buyResaleTicket(1, { value: RESALE });
      const after  = await ethers.provider.getBalance(alice.address);
      expect(after - before).to.equal(RESALE);
    });

    it("listing is cleared after sale", async function () {
      await contract.connect(bob).buyResaleTicket(1, { value: RESALE });
      expect(await contract.resalePrice(1)).to.equal(0n);
    });

    it("emits TicketResold", async function () {
      await expect(contract.connect(bob).buyResaleTicket(1, { value: RESALE }))
        .to.emit(contract, "TicketResold")
        .withArgs(1n, alice.address, bob.address, RESALE);
    });

    it("refunds over-payment to buyer", async function () {
      const overpay = RESALE + ethers.parseEther("1");
      const before  = await ethers.provider.getBalance(bob.address);
      const tx      = await contract.connect(bob).buyResaleTicket(1, { value: overpay });
      const receipt = await tx.wait();
      const gas     = receipt!.gasUsed * receipt!.gasPrice;
      const after   = await ethers.provider.getBalance(bob.address);
      expect(before - after).to.equal(RESALE + gas);
    });

    it("reverts when ticket not listed", async function () {
      await contract.connect(bob).buyResaleTicket(1, { value: RESALE });
      await expect(
        contract.connect(carol).buyResaleTicket(1, { value: RESALE })
      ).to.be.revertedWith("EventTicket: not for resale");
    });

    it("reverts on insufficient payment", async function () {
      await expect(
        contract.connect(bob).buyResaleTicket(1, { value: RESALE - 1n })
      ).to.be.revertedWith("EventTicket: insufficient payment");
    });

    it("reverts when trying to buy own ticket", async function () {
      await expect(
        contract.connect(alice).buyResaleTicket(1, { value: RESALE })
      ).to.be.revertedWith("EventTicket: cannot buy own ticket");
    });

    it("second buy after transfer (resale cleared)", async function () {
      await contract.connect(bob).buyResaleTicket(1, { value: RESALE });
      // Bob now owns it; list it again
      await contract.connect(bob).listForResale(1, RESALE);
      await contract.connect(carol).buyResaleTicket(1, { value: RESALE });
      expect(await contract.ownerOf(1)).to.equal(carol.address);
    });
  });

  // ─── 9. ERC721Enumerable ──────────────────────────────────────────────────

  describe("ERC721Enumerable", function () {
    beforeEach(async function () {
      await createEvent();
    });

    it("totalSupply increases with each mint", async function () {
      await contract.connect(alice).buyTicket(1, { value: PRICE });
      await contract.connect(alice).buyTicket(1, { value: PRICE });
      expect(await contract.totalSupply()).to.equal(2n);
    });

    it("tokenOfOwnerByIndex enumerates wallet tokens", async function () {
      await contract.connect(alice).buyTicket(1, { value: PRICE }); // tokenId 1
      await contract.connect(alice).buyTicket(1, { value: PRICE }); // tokenId 2
      expect(await contract.tokenOfOwnerByIndex(alice.address, 0)).to.equal(1n);
      expect(await contract.tokenOfOwnerByIndex(alice.address, 1)).to.equal(2n);
    });
  });

  // ─── 10. deactivateEvent ──────────────────────────────────────────────────

  describe("deactivateEvent()", function () {
    it("owner can deactivate an event", async function () {
      await createEvent();
      await contract.connect(owner).deactivateEvent(1);
      const ev = await contract.events(1);
      expect(ev.active).to.be.false;
    });

    it("non-owner cannot deactivate", async function () {
      await createEvent();
      await expect(
        contract.connect(alice).deactivateEvent(1)
      ).to.be.revertedWithCustomError(contract, "OwnableUnauthorizedAccount");
    });

    it("cannot deactivate already-inactive event", async function () {
      await createEvent();
      await contract.connect(owner).deactivateEvent(1);
      await expect(
        contract.connect(owner).deactivateEvent(1)
      ).to.be.revertedWith("EventTicket: event not active");
    });
  });
});
