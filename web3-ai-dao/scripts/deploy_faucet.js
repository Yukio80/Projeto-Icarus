const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

// Manual .env parse (dotenv not installed in root)
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
  console.log("Deploying Faucet with account:", deployer.address);

  const tokenAddr = process.env.TOKEN_ADDRESS;
  const registryAddr = process.env.BOT_REGISTRY_ADDRESS;
  const nftAddr = process.env.REPUTATION_NFT_ADDRESS;

  if (!tokenAddr || !registryAddr) {
    console.error("Missing TOKEN_ADDRESS or BOT_REGISTRY_ADDRESS in .env");
    process.exit(1);
  }

  const Faucet = await hre.ethers.getContractFactory("Faucet");
  const faucet = await Faucet.deploy(tokenAddr, registryAddr);
  await faucet.waitForDeployment();

  const addr = await faucet.getAddress();
  console.log("Faucet deployed to:", addr);

  // Fund faucet with 50k AIGOV
  const token = await hre.ethers.getContractAt("GovernanceToken", tokenAddr);
  const FUND = hre.ethers.parseUnits("50000", 18);
  const tx = await token.transfer(addr, FUND);
  await tx.wait();
  console.log(`Funded faucet with 50,000 AIGOV tx=${tx.hash}`);

  // Authorize faucet on ReputationNFT
  if (nftAddr) {
    const nft = await hre.ethers.getContractAt("ReputationNFT", nftAddr);
    const authTx = await nft.setAuthorizedContract(addr, true);
    await authTx.wait();
    console.log(`Authorized faucet on ReputationNFT tx=${authTx.hash}`);
  }

  // Write to .env
  const fs = require("fs");
  const envPath = "./.env";
  let env = fs.readFileSync(envPath, "utf8");
  const key = "FAUCET_ADDRESS";
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
