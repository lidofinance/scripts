module.exports = {
  networks: {
    hardhat: {
      hardfork: "cancun",
      chainId: 1,
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
