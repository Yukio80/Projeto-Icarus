const hre = require("hardhat");

async function main() {
  const [deployer, bot, ...others] = await hre.ethers.getSigners();

  console.log(`Deployer: ${deployer.address}`);
  console.log(`Bot (stakeholder): ${bot.address}`);

  const ReputationNFT = await hre.ethers.getContractFactory("ReputationNFT");
  const nft = await ReputationNFT.deploy();
  await nft.waitForDeployment();
  const nftAddress = await nft.getAddress();
  console.log(`\nReputationNFT deployed: ${nftAddress}`);

  const stakeholders = [bot, ...others.slice(0, 4)];
  console.log(`\nMinting reputation tokens for ${stakeholders.length} stakeholders...`);

  for (const s of stakeholders) {
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
  console.log(`\n  -> Bot ${bot.address}: +30 XP (3 votes recorded)`);

  const botRep = await nft.getReputation(bot.address);
  const multiplier = await nft.getVotingMultiplier(bot.address);
  console.log(`\nBot reputation:`);
  console.log(`  XP: ${botRep.xp}`);
  console.log(`  Level: ${['BRONZE','SILVER','GOLD','DIAMOND'][botRep.level]}`);
  console.log(`  Proposals voted: ${botRep.proposalsVoted}`);
  console.log(`  Voting multiplier: ${multiplier}x`);

  console.log("\n--- Save to .env ---");
  console.log(`REPUTATION_NFT_ADDRESS=${nftAddress}`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
