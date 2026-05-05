import { ethers, network } from "hardhat";
import * as fs from "fs";
import * as path from "path";

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying EventTicket with account:", deployer.address);
  console.log(
    "Account balance:",
    ethers.formatEther(await ethers.provider.getBalance(deployer.address)),
    "ETH"
  );
  console.log("Network:", network.name);

  const Factory = await ethers.getContractFactory("EventTicket");
  const contract = await Factory.deploy();
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  console.log("\nEventTicket deployed to:", address);

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
