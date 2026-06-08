require("@nomicfoundation/hardhat-toolbox");

module.exports = {
  solidity: {
    version: "0.8.27",
    settings: {
      optimizer: { enabled: true, runs: 200 },
      evmVersion: "cancun",
    },
  },
  networks: {
    localhost: {
      url: "http://127.0.0.1:8545",
    },
    hardhat: {
      chainId: 31337,
    },
    sepolia: {
      url: process.env.RPC_URL || "https://eth-sepolia.g.alchemy.com/v2/YOUR_KEY",
      accounts: [process.env.DEPLOYER_PRIVATE_KEY],
    },
  },
};
