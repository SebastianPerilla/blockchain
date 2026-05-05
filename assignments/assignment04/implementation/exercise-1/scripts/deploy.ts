import { ethers, network } from "hardhat";
import * as fs from "fs";
import * as path from "path";

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying VendingMachine with account:", deployer.address);
  console.log(
    "Account balance:",
    ethers.formatEther(await ethers.provider.getBalance(deployer.address)),
    "ETH"
  );
  console.log("Network:", network.name);

  const Factory = await ethers.getContractFactory("VendingMachine");
  const vm = await Factory.deploy();
  await vm.waitForDeployment();

  const address = await vm.getAddress();
  console.log("\nVendingMachine deployed to:", address);

  if (network.name === "sepolia") {
    console.log(`Sepolia Etherscan: https://sepolia.etherscan.io/address/${address}`);
  }

  const deploymentInfo = {
    address,
    deployer: deployer.address,
    network: network.name,
    ...(network.name === "sepolia" && {
      etherscan: `https://sepolia.etherscan.io/address/${address}`,
    }),
  };

  const outPath = path.join(__dirname, "..", "app", "deployment.json");
  fs.writeFileSync(outPath, JSON.stringify(deploymentInfo, null, 2));
  console.log("Deployment info saved to app/deployment.json");
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
