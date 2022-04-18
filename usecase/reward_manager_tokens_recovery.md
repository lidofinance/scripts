### 💸 Rewards Manager Tokens Recoverer

This repo contains contract RewardsManagerTokensRecoverer to simplify tokens recovering from Lido's reward managers via Aragon voting.

#### Setup

Please, bring back archived scripts and test first:
```shell
cp ./tests/archive/xtest_rewards_manager_tokens_recoverer.py ./tests/test_rewards_manager_tokens_recoverer.py
cp ./scripts/archive/deploy_rewards_manager_tokens_recoverer.py ./scripts
```

#### Deployment

To run deployment of the RewardsManagerTokensRecoverer contract use the command
`DEPLOYER=<DEPLOYER_ACCOUNT> brownie run deploy_rewards_manager_tokens_recoverer`.

#### Tests

To run tests for the RewardsManagerTokensRecoverer contract use the command
`brownie test ./tests/test_rewards_manager_tokens_recoverer.py -s`.
