const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying BotRegistry with account:", deployer.address);

  const BotRegistry = await hre.ethers.getContractFactory("BotRegistry");
  const botRegistry = await BotRegistry.deploy();
  await botRegistry.waitForDeployment();

  const addr = await botRegistry.getAddress();
  console.log("BotRegistry deployed to:", addr);

  // Write to .env
  const fs = require("fs");
  const envPath = "./.env";
  let env = fs.readFileSync(envPath, "utf8");
  if (env.includes("BOT_REGISTRY_ADDRESS")) {
    env = env.replace(/BOT_REGISTRY_ADDRESS=.*/, `BOT_REGISTRY_ADDRESS=${addr}`);
  } else {
    env += `\nBOT_REGISTRY_ADDRESS=${addr}`;
  }
  fs.writeFileSync(envPath, env);
  console.log("Wrote BOT_REGISTRY_ADDRESS to .env");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
