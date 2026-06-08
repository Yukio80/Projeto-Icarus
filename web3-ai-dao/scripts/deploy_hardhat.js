const hre = require("hardhat");

async function main() {
  const [deployer, ...stakeholders] = await hre.ethers.getSigners();
  const stakeholderCount = Math.min(10, stakeholders.length);

  console.log(`Deployer: ${deployer.address}`);
  console.log(`Stakeholders: ${stakeholderCount}`);

  const GovernanceToken = await hre.ethers.getContractFactory("GovernanceToken");
  const token = await GovernanceToken.deploy(deployer.address);
  await token.waitForDeployment();
  const tokenAddress = await token.getAddress();
  console.log(`\nGovernanceToken deployed: ${tokenAddress}`);

  const ReputationNFT = await hre.ethers.getContractFactory("ReputationNFT");
  const nft = await ReputationNFT.deploy();
  await nft.waitForDeployment();
  const nftAddress = await nft.getAddress();
  console.log(`ReputationNFT deployed: ${nftAddress}`);

  const AIStakeholderDAO = await hre.ethers.getContractFactory("AIStakeholderDAO");
  const dao = await AIStakeholderDAO.deploy(tokenAddress, deployer.address, nftAddress);
  await dao.waitForDeployment();
  const daoAddress = await dao.getAddress();
  console.log(`AIStakeholderDAO deployed: ${daoAddress}`);

  await nft.connect(deployer).setAuthorizedContract(daoAddress, true);
  console.log(`DAO authorized on ReputationNFT: ${daoAddress}`);

  const DECIMALS = 18n;
  const TOKENS_PER_STAKEHOLDER = 10_000n * 10n ** DECIMALS;
  const TREASURY_AMOUNT = 50_000n * 10n ** DECIMALS;
  const totalDistributed = TOKENS_PER_STAKEHOLDER * BigInt(stakeholderCount) + TREASURY_AMOUNT;

  console.log(`\nDistributing ${stakeholderCount} x ${ethers.formatEther(TOKENS_PER_STAKEHOLDER)} tokens to stakeholders...`);
  for (let i = 0; i < stakeholderCount; i++) {
    await token.transfer(stakeholders[i].address, TOKENS_PER_STAKEHOLDER);
    console.log(`  -> ${stakeholders[i].address}: ${ethers.formatEther(TOKENS_PER_STAKEHOLDER)} AIGOV`);
  }

  console.log(`\nFunding treasury with ${ethers.formatEther(TREASURY_AMOUNT)} tokens...`);
  await token.transfer(daoAddress, TREASURY_AMOUNT);
  console.log(`  -> DAO Treasury: ${ethers.formatEther(TREASURY_AMOUNT)} AIGOV`);

  const remaining = ethers.formatEther(await token.totalSupply() - totalDistributed);
  console.log(`\nRemaining with deployer: ${remaining} AIGOV`);

  console.log("\n--- Save to .env ---");
  console.log(`TOKEN_ADDRESS=${tokenAddress}`);
  console.log(`DAO_ADDRESS=${daoAddress}`);
  console.log(`REPUTATION_NFT_ADDRESS=${nftAddress}`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
