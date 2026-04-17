import { ethers } from "hardhat";
import * as fs from "fs";
import * as path from "path";

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying VendingMachine with account:", deployer.address);
  console.log("Account balance:", ethers.formatEther(await ethers.provider.getBalance(deployer.address)), "ETH");

  const Factory = await ethers.getContractFactory("VendingMachine");
  const vm = await Factory.deploy();
  await vm.waitForDeployment();

  const address = await vm.getAddress();
  console.log("\nVendingMachine deployed to:", address);

  // Write deployment info so the Python app can pick it up easily
  const deploymentInfo = { address, deployer: deployer.address, network: "localhost" };
  const outPath = path.join(__dirname, "..", "app", "deployment.json");
  fs.writeFileSync(outPath, JSON.stringify(deploymentInfo, null, 2));
  console.log("Deployment info saved to app/deployment.json");
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
