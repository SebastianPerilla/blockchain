/**
 * TicketManager — Hardhat / ethers v6 test suite
 *
 * Covers all 8 required test categories:
 *  1. Successful ticket purchase
 *  2. Failed purchase (insufficient payment & sold out)
 *  3. Successful ticket transfer
 *  4. Failed transfer by non-owner
 *  5. Successful resale flow
 *  6. Permission failure on admin-only action
 *  7. Edge-case: invalid state transition (transfer while listed for resale)
 *  8. Final ownership check after a sequence of actions
 *
 * Run: npx hardhat test
 */
const { expect } = require("chai");
const { ethers }  = require("hardhat");

describe("TicketManager", function () {
  let tm;
  let admin, alice, bob, carol;

  const PRICE1        = ethers.parseEther("0.01");   // event 1 price
  const PRICE2        = ethers.parseEther("0.05");   // event 2 price
  const SMALL_TICKETS = 3;                           // low cap for sold-out test

  // ── Deploy a fresh contract + two events before every test ─────────────────
  beforeEach(async function () {
    [admin, alice, bob, carol] = await ethers.getSigners();

    const Factory = await ethers.getContractFactory("TicketManager");
    tm = await Factory.deploy();

    // Event 1 — low cap, cheap
    await tm.connect(admin).createEvent(
      "Summer Festival", "2025-06-15", "Central Park", PRICE1, SMALL_TICKETS
    );
    // Event 2 — larger cap, pricier
    await tm.connect(admin).createEvent(
      "Tech Conference", "2025-09-20", "Convention Centre", PRICE2, 50
    );
  });

  // ────────────────────────────────────────────────────────────────────────────
  // TEST 1  Successful ticket purchase
  // ────────────────────────────────────────────────────────────────────────────
  it("1. should allow a user to buy a ticket for an active event", async function () {
    await expect(
      tm.connect(alice).buyTicket(1, { value: PRICE1 })
    ).to.emit(tm, "TicketPurchased");

    const ids = await tm.getUserTickets(alice.address);
    expect(ids.length).to.equal(1);

    // Verify on-chain state
    const ticket = await tm.getTicket(ids[0]);
    expect(ticket.owner).to.equal(alice.address);
    expect(ticket.forResale).to.be.false;
  });

  // ────────────────────────────────────────────────────────────────────────────
  // TEST 2a  Failed purchase — insufficient payment
  // ────────────────────────────────────────────────────────────────────────────
  it("2a. should reject a ticket purchase with insufficient ETH", async function () {
    await expect(
      tm.connect(alice).buyTicket(1, { value: ethers.parseEther("0.001") })
    ).to.be.revertedWith("Insufficient payment");
  });

  // ────────────────────────────────────────────────────────────────────────────
  // TEST 2b  Failed purchase — event sold out
  // ────────────────────────────────────────────────────────────────────────────
  it("2b. should reject a ticket purchase when the event is sold out", async function () {
    // Fill all SMALL_TICKETS spots
    for (let i = 0; i < SMALL_TICKETS; i++) {
      const buyer = [alice, bob, carol][i];
      await tm.connect(buyer).buyTicket(1, { value: PRICE1 });
    }
    await expect(
      tm.connect(alice).buyTicket(1, { value: PRICE1 })
    ).to.be.revertedWith("Sold out");
  });

  // ────────────────────────────────────────────────────────────────────────────
  // TEST 3  Successful ticket transfer
  // ────────────────────────────────────────────────────────────────────────────
  it("3. should allow the owner to transfer a ticket to another address", async function () {
    await tm.connect(alice).buyTicket(1, { value: PRICE1 });
    const [ticketId] = await tm.getUserTickets(alice.address);

    await expect(
      tm.connect(alice).transferTicket(ticketId, bob.address)
    ).to.emit(tm, "TicketTransferred")
      .withArgs(ticketId, alice.address, bob.address);

    const ticket = await tm.getTicket(ticketId);
    expect(ticket.owner).to.equal(bob.address);

    // Alice's list should be empty, Bob's should contain the ticket
    expect((await tm.getUserTickets(alice.address)).length).to.equal(0);
    expect((await tm.getUserTickets(bob.address)).length).to.equal(1);
  });

  // ────────────────────────────────────────────────────────────────────────────
  // TEST 4  Failed transfer by non-owner
  // ────────────────────────────────────────────────────────────────────────────
  it("4. should reject a transfer attempted by a non-owner", async function () {
    await tm.connect(alice).buyTicket(1, { value: PRICE1 });
    const [ticketId] = await tm.getUserTickets(alice.address);

    await expect(
      tm.connect(bob).transferTicket(ticketId, carol.address)
    ).to.be.revertedWith("Not the ticket owner");
  });

  // ────────────────────────────────────────────────────────────────────────────
  // TEST 5  Successful resale flow (list → buy)
  // ────────────────────────────────────────────────────────────────────────────
  it("5. should complete a full resale flow: list then purchase", async function () {
    await tm.connect(alice).buyTicket(1, { value: PRICE1 });
    const [ticketId] = await tm.getUserTickets(alice.address);

    const RESALE_PRICE = ethers.parseEther("0.02");

    // Alice lists for resale
    await expect(
      tm.connect(alice).listForResale(ticketId, RESALE_PRICE)
    ).to.emit(tm, "TicketListedForResale").withArgs(ticketId, RESALE_PRICE);

    let ticket = await tm.getTicket(ticketId);
    expect(ticket.forResale).to.be.true;
    expect(ticket.resalePrice).to.equal(RESALE_PRICE);

    // Bob buys the resale ticket
    const bobBalanceBefore = await ethers.provider.getBalance(alice.address);
    await expect(
      tm.connect(bob).buyResaleTicket(ticketId, { value: RESALE_PRICE })
    ).to.emit(tm, "TicketResold");

    ticket = await tm.getTicket(ticketId);
    expect(ticket.owner).to.equal(bob.address);
    expect(ticket.forResale).to.be.false;

    // Alice received the resale payment (balance increased)
    const bobBalanceAfter = await ethers.provider.getBalance(alice.address);
    expect(bobBalanceAfter).to.be.gt(bobBalanceBefore);
  });

  // ────────────────────────────────────────────────────────────────────────────
  // TEST 6  Permission failure — non-admin tries to create an event
  // ────────────────────────────────────────────────────────────────────────────
  it("6. should reject event creation by a non-admin account", async function () {
    await expect(
      tm.connect(alice).createEvent(
        "Fake Rave", "2025-12-31", "Warehouse", PRICE1, 50
      )
    ).to.be.revertedWith("Only admin can call this");
  });

  // ────────────────────────────────────────────────────────────────────────────
  // TEST 7  Edge case — cannot transfer a ticket that is listed for resale
  // ────────────────────────────────────────────────────────────────────────────
  it("7. should reject a direct transfer while the ticket is listed for resale", async function () {
    await tm.connect(alice).buyTicket(1, { value: PRICE1 });
    const [ticketId] = await tm.getUserTickets(alice.address);

    await tm.connect(alice).listForResale(ticketId, ethers.parseEther("0.02"));

    // Transfer should fail while listing is active
    await expect(
      tm.connect(alice).transferTicket(ticketId, bob.address)
    ).to.be.revertedWith("Cancel resale listing first");

    // After cancelling, transfer should succeed
    await tm.connect(alice).cancelResaleListing(ticketId);
    await expect(
      tm.connect(alice).transferTicket(ticketId, bob.address)
    ).to.emit(tm, "TicketTransferred");
  });

  // ────────────────────────────────────────────────────────────────────────────
  // TEST 8  Final ownership after a full sequence of actions
  //         buy (alice) → transfer (alice → bob) → resale (bob → carol)
  // ────────────────────────────────────────────────────────────────────────────
  it("8. should correctly track ownership through buy → transfer → resale", async function () {
    // Step 1: Alice buys
    await tm.connect(alice).buyTicket(1, { value: PRICE1 });
    const [ticketId] = await tm.getUserTickets(alice.address);
    expect((await tm.getTicket(ticketId)).owner).to.equal(alice.address);

    // Step 2: Alice transfers to Bob
    await tm.connect(alice).transferTicket(ticketId, bob.address);
    expect((await tm.getTicket(ticketId)).owner).to.equal(bob.address);

    // Step 3: Bob lists for resale
    const RESALE_PRICE = ethers.parseEther("0.015");
    await tm.connect(bob).listForResale(ticketId, RESALE_PRICE);

    // Step 4: Carol buys from resale
    await tm.connect(carol).buyResaleTicket(ticketId, { value: RESALE_PRICE });

    // Final assertions
    const finalTicket = await tm.getTicket(ticketId);
    expect(finalTicket.owner).to.equal(carol.address);
    expect(finalTicket.forResale).to.be.false;

    // Ownership arrays are consistent
    expect((await tm.getUserTickets(alice.address)).length).to.equal(0);
    expect((await tm.getUserTickets(bob.address)).length).to.equal(0);
    const carolIds = await tm.getUserTickets(carol.address);
    expect(carolIds).to.include(ticketId);
  });

  // ────────────────────────────────────────────────────────────────────────────
  // TEST 9  Extra: non-admin cannot deactivate an event
  // ────────────────────────────────────────────────────────────────────────────
  it("9. should reject event deactivation by a non-admin", async function () {
    await expect(
      tm.connect(alice).deactivateEvent(1)
    ).to.be.revertedWith("Only admin can call this");
  });
});
