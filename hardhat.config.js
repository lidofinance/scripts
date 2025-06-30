module.exports = {
  networks: {
    hardhat: {
      chainId: 1,
      hardfork: "cancun",
      chains: {
        560048: {
          hardforkHistory: {
            cancun: 0,
          },
        }
      }
    },
  },
};
