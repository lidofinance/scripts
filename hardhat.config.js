module.exports = {
  networks: {
    hardhat: {
      chainId: 1,
      // Core's PDG tests require the Prague BLS12-381 precompiles.
      hardfork: "prague",
      // Core's vault role fixtures use signers beyond the default 20 accounts.
      accounts: { count: 30 },
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
