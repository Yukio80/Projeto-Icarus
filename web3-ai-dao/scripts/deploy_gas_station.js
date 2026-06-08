const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

function loadEnv() {
  const raw = fs.readFileSync(path.join(__dirname, "..", ".env"), "utf8");
  for (const line of raw.split("\n")) {
    const m = line.match(/^([A-Z_]+)=(.+)$/);
    if (m) process.env[m[1]] = m[2];
  }
}
loadEnv();

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying GasStation with account:", deployer.address);
  console.log("Balance:", hre.ethers.formatEther(await deployer.provider.getBalance(deployer.address)), "ETH");

  const registryAddr = process.env.BOT_REGISTRY_ADDRESS;
  if (!registryAddr) {
    console.error("Missing BOT_REGISTRY_ADDRESS in .env");
    process.exit(1);
  }

  const GasStation = await hre.ethers.getContractFactory("GasStation");
  const gasStation = await GasStation.deploy(registryAddr);
  await gasStation.waitForDeployment();

  const addr = await gasStation.getAddress();
  console.log("GasStation deployed to:", addr);

  // Fund with 0.05 ETH (5 refills at 0.01 each)
  const FUND_ETH = hre.ethers.parseEther("0.05");
  const tx = await deployer.sendTransaction({ to: addr, value: FUND_ETH });
  await tx.wait();
  console.log(`Funded with 0.27 ETH tx=${tx.hash}`);
  console.log(`GasStation balance: ${hre.ethers.formatEther(await hre.ethers.provider.getBalance(addr))} ETH`);

  const envPath = path.join(__dirname, "..", ".env");
  let env = fs.readFileSync(envPath, "utf8");
  const key = "GAS_STATION_ADDRESS";
  if (env.includes(key)) {
    env = env.replace(new RegExp(`${key}=.*`), `${key}=${addr}`);
  } else {
    env += `\n${key}=${addr}`;
  }
  fs.writeFileSync(envPath, env);
  console.log(`Wrote ${key}=${addr} to .env`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
