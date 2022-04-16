<div style="display: flex;" align="center">
  <h1 align="center">Voting scripts</h1>
  <img src="assets/voting.png" width="60" height="60" align="left" style="padding: 20px"/>
</div>

![python ~3.9](https://img.shields.io/badge/python->=3.8,<3.10-blue)
![poetry 1.1.13](https://img.shields.io/badge/poetry-1.1.13-blue)
![eth_brownie 1.18.1](https://img.shields.io/badge/eth__brownie-1.18.1-brown)
![AVotesParser 0.5](https://img.shields.io/badge/AVotesParser-0.5-brown)
![Ganache ~7.0.4](https://img.shields.io/badge/ganache-7.0.4-orange)
![license MIT](https://img.shields.io/badge/license-MIT-brightgreen)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)


Lido DAO Aragon omnibus voting scripts.

## 🏁 Getting started

- This project uses Brownie development framework. Learn more about [Brownie](https://eth-brownie.readthedocs.io/en/stable/index.html).
- [Poetry](https://python-poetry.org/) dependency and packaging manager is used to bootstrap environment and keep the repo sane.
### Prerequisites

- Python >= 3.8, <3.10
- Pip >= 20.0
- Node >= 16.0
- yarn >= 1.22

#### Step 1. Install Poetry

Use the following command to install poetry:

```shell
pip install --user poetry==1.1.13
```

alternatively, you could proceed with `pipx`:

```shell
pipx install poetry==1.1.13
```

#### Step 2. Setup dependencies with poetry

Ensure that poetry bin path is added to your `$PATH` env variable.
Usually it's `$HOME/.local/bin` for most Unix-like systems.

```shell
poetry install
```

Note: if you have encountered `Invalid hashes` errors while trying to run previous command, please remove poetry's cache:

* GNU/Linux

```shell
rm -rf ~/.cache/pypoetry/cache/
rm -rf ~/.cache/pypoetry/artifacts/
```
* MAC OS:

```shell
rm -rf ~/Library/Caches/pypoetry/cache
rm -rf ~/Library/Caches/pypoetry/artifacts
```

#### Step 3. Install Ganache locally

Simply run the following command from the project's directory
```shell
yarn
```
#### Step 4. Activate virtual environment

📝 While previous steps needed only once to init the environment from scratch, the current step is used regularly to activate the environment every time you need it.

```shell
poetry shell
```

## ⚗️ Workflow

### Network setup

In a typical weekly omnibus workflow, you need only the `mainnet-fork` and `mainnet` networks. In the case of a large test campaign on Lido upgrades, it also could be useful to go with `görli` and `görli-fork` testnets first.

#### Mainnet setup

By default, all scripts run in mainnet fork mode (don't forget to edit fork
param at brownie config). To run scripts on actually mainnet you need to add
param `--network mainnet` to the end of the command and set the following env
variables:

This section covers network configuration params and their usage.

#### Environment variables setup

Despite the chosen network you always need to set the following var:
```bash
export WEB3_INFURA_PROJECT_ID=<infura_api_key>
```

To start a new vote please provide the `DEPLOYER` brownie account name (wallet):
```bash
export DEPLOYER=<brownie_wallet_name>
```

To run tests with a contract name resolution guided by the Etherscan you should provide the etherscan API token:
```bash
export ETHERSCAN_TOKEN=<etherscan_api_key>
```

#### Command-line arguments requirements

Always pass network name explicitly with `--network {network-name}` brownie command-line arguments for both vote and tests scripts.

To reveal a full test output pass the `-s` flag when running test scripts with `brownie test`
##### Fork-mode development networks

By default, you should start testing process in a network fork mode (don't forget to review brownie fork params). The Mainnet-fork mode exists in brownie by default. To add the Görli Testnet fork mode please run once the following command (to setup and save new network):
```bash
brownie networks add "Development" goerli-fork host=http://127.0.0.1 cmd=ganache-cli port=8545 gas_limit=12000000 fork=https://goerli.infura.io/v3/${WEB3_INFURA_PROJECT_ID} chain_id=5 mnemonic=brownie accounts=10
```
Now you have the `goerli-fork` brownie network configuration to work with.

###### Notes on running tests in a forked mode

* To forcibly bypass etherscan contract and event names decoding set the `OMNIBUS_BYPASS_EVENTS_DECODING` environment variable to `1`. It could be useful in case of etherscan downtimes or usage of some unverified contracts (especially, on the Görli Testnet).
* To re-use the already created `vote_id` you can pass the `OMNIBUS_VOTE_ID` environment variable (e.g. `OMNIBUS_VOTE_ID=104`).

##### Live networks

You can start votes on the live networks by running scripts either on the Mainnet (setting `--network mainnet`) or on the Görli Testnet (`--network goerli`). You can't run tests on the live networks.

## Repository housekeeping

Please move your outdated scripts into `scripts/archive` and outdated tests into `tests/archive` directories.

To mask obsoleted tests and prevent them from running by `brownie test` even when residing in archive directory, please consider to rename them: `test_` → `xtest_`.

## Use cases

### 🕸️ Notes for the node operators management ops

#### Adding node operators

Script to pack up adding new node operators in one vote

```bash
NODE_OPERATORS_JSON=node_operators.json brownie run add_node_operators --network {name}
```

##### node_operators.json

```json
{
  "node_operators": [
    {
      "name": "Test",
      "address": "0x000..."
    },
    ...
  ]
}

```

#### Setting node operators limits

Script to pack up setting node operators staking limits in one vote

```bash
NODE_OPERATORS_JSON=node_operators.json brownie run set_node_operators_limit --network {name}
```

##### node_operators.json

```json
{
  "node_operators": [
    {
      "id": 1,
      "limit": 20
    },
    ...
  ]
}

```

### 💸 Rewards Manager Tokens Recoverer

This repo contains contract RewardsManagerTokensRecoverer to simplify tokens recovering from Lido's reward managers via Aragon voting.

#### Setup

Please, bring back archived scripts and test first:
```shell
cp ./tests/archive/xtest_rewards_manager_tokens_recoverer.py ./tests/test_rewards_manager_tokens_recoverer.py
cp ./scripts/archive/deploy_rewards_manager_tokens_recoverer.py ./scripts
```

#### Deployment

To run deployment of the RewardsManagerTokensRecoverer contract use the command `DEPLOYER=<DEPLOYER_ACCOUNT> brownie run deploy_rewards_manager_tokens_recoverer`.

#### Tests

To run tests for the RewardsManagerTokensRecoverer contract use the command `brownie test ./tests/test_rewards_manager_tokens_recoverer.py -s`.
