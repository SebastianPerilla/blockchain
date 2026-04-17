/**
 * Deploy TicketManager, create two seed events, and write the contract
 * address to app/contract_address.txt so the Streamlit web3 app can find it.
 *
 * Usage (while `npx hardhat node` is running in another terminal):
 *   npx hardhat run scripts/deploy.js --network localhost
 */
const { ethers } = require("hardhat");
const fs   = require("fs");
const path = require("path");

async function main() {
  const [admin] = await ethers.getSigners();
  console.log("Deploying from:", admin.address);

  const TicketManager = await ethers.getContractFactory("TicketManager");
  const tm = await TicketManager.deploy();
  await tm.waitForDeployment();

  const address = await tm.getAddress();
  console.log("TicketManager deployed at:", address);

  // ── Seed two events ───────────────────────────────────────────────────────
  const price1 = ethers.parseEther("0.01");  // 0.01 ETH
  const price2 = ethers.parseEther("0.05");  // 0.05 ETH

  let tx = await tm.createEvent(
    "Summer Music Festival",
    "2025-06-15",
    "Central Park, NYC",
    price1,
    100
  );
  await tx.wait();
  console.log("Created event: Summer Music Festival");

  tx = await tm.createEvent(
    "Tech Conference 2025",
    "2025-09-20",
    "Convention Centre, SF",
    price2,
    50
  );
  await tx.wait();
  console.log("Created event: Tech Conference 2025");

  // ── Persist address ───────────────────────────────────────────────────────
  const addrFile = path.join(__dirname, "..", "app", "contract_address.txt");
  fs.writeFileSync(addrFile, address);
  console.log("Address written to app/contract_address.txt");
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
