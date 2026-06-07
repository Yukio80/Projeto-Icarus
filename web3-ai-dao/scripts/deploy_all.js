const hre = require("hardhat");

async function main() {
  const [deployer, bot, ...others] = await hre.ethers.getSigners();
  const stakeholderCount = Math.min(10, others.length);

  console.log(`Deployer: ${deployer.address}`);
  console.log(`Bot (stakeholder): ${bot.address}`);
  console.log(`Stakeholders: ${stakeholderCount}`);

  // 1. Deploy GovernanceToken
  const GovernanceToken = await hre.ethers.getContractFactory("GovernanceToken");
  const token = await GovernanceToken.deploy(deployer.address);
  await token.waitForDeployment();
  const tokenAddress = await token.getAddress();
  console.log(`\nGovernanceToken deployed: ${tokenAddress}`);

  // 2. Deploy ReputationNFT
  const ReputationNFT = await hre.ethers.getContractFactory("ReputationNFT");
  const nft = await ReputationNFT.deploy();
  await nft.waitForDeployment();
  const nftAddress = await nft.getAddress();
  console.log(`ReputationNFT deployed: ${nftAddress}`);

  // 3. Deploy AIStakeholderDAO with reputation NFT address
  const AIStakeholderDAO = await hre.ethers.getContractFactory("AIStakeholderDAO");
  const dao = await AIStakeholderDAO.deploy(tokenAddress, deployer.address, nftAddress);
  await dao.waitForDeployment();
  const daoAddress = await dao.getAddress();
  console.log(`AIStakeholderDAO deployed: ${daoAddress}`);

  // 3a. Authorize DAO to record reputation on behalf of voters
  await nft.connect(deployer).setAuthorizedContract(daoAddress, true);
  console.log(`DAO authorized on ReputationNFT: ${daoAddress}`);

  // 4. Distribute AIGOV tokens
  const DECIMALS = 18n;
  const TOKENS_PER_STAKEHOLDER = 10_000n * 10n ** DECIMALS;
  const TREASURY_AMOUNT = 50_000n * 10n ** DECIMALS;

  console.log(`\nDistributing tokens to ${stakeholderCount} stakeholders...`);
  for (let i = 0; i < stakeholderCount; i++) {
    await token.transfer(others[i].address, TOKENS_PER_STAKEHOLDER);
  }
  console.log(`  -> ${stakeholderCount} stakeholders received ${ethers.formatEther(TOKENS_PER_STAKEHOLDER)} AIGOV each`);

  await token.transfer(bot.address, TOKENS_PER_STAKEHOLDER);
  console.log(`  -> Bot ${bot.address}: ${ethers.formatEther(TOKENS_PER_STAKEHOLDER)} AIGOV`);

  await token.transfer(daoAddress, TREASURY_AMOUNT);
  console.log(`  -> DAO Treasury: ${ethers.formatEther(TREASURY_AMOUNT)} AIGOV`);

  // 5. Mint reputation tokens
  const repStakeholders = [bot, ...others.slice(0, 4)];
  console.log(`\nMinting reputation tokens for ${repStakeholders.length} stakeholders...`);

  for (const s of repStakeholders) {
    const tx = await nft.mint(s.address);
    await tx.wait();
    console.log(`  -> ${s.address}: REP #${await nft.totalMinted()} minted`);

    await nft.connect(deployer).addXP(s.address, 50);
    console.log(`  -> ${s.address}: +50 XP (initial)`);
  }

  await nft.connect(deployer).addXP(bot.address, 40);
  await nft.connect(deployer).recordVote(bot.address);
  await nft.connect(deployer).recordVote(bot.address);
  await nft.connect(deployer).recordVote(bot.address);
  console.log(`  -> Bot ${bot.address}: +30 XP (3 simulated votes)`);

  // 6. Show bot reputation
  const botRep = await nft.getReputation(bot.address);
  const multiplier = await nft.getVotingMultiplier(bot.address);
  const votingPower = await dao.getVotingPower(bot.address);
  const tokenBalance = await token.balanceOf(bot.address);

  console.log(`\nBot reputation:`);
  console.log(`  XP: ${botRep.xp}`);
  console.log(`  Level: ${['BRONZE','SILVER','GOLD','DIAMOND'][botRep.level]}`);
  console.log(`  Proposals voted: ${botRep.proposalsVoted}`);
  console.log(`  Voting multiplier: ${multiplier}x`);
  console.log(`  AIGOV balance: ${ethers.formatEther(tokenBalance)}`);
  console.log(`  Effective voting power: ${ethers.formatEther(votingPower)}`);

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
