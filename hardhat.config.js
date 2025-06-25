module.exports = {
  networks: {
    hardhat: {
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
