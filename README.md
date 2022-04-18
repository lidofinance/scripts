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

- This project uses Brownie development framework. Learn more about
[Brownie](https://eth-brownie.readthedocs.io/en/stable/index.html).
- [Poetry](https://python-poetry.org/) dependency and packaging manager is used
to bootstrap environment and keep the repo sane.
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

#### Step 4. Import network config to connect brownie with local Ganache

```shell
poetry brownie networks import network-config.yaml True
```

#### Step 5. Activate virtual environment

📝 While previous steps needed only once to init the environment from scratch,
the current step is used regularly to activate the environment every time you
need it.

```shell
poetry shell
```

## ⚗️ Workflow

### Network setup

By default, you should start composing new scripts and test leveraging forked networks.
You have two forked networks to work with:
* `mainnet-fork`
* `goerli-fork`

To start new voting on the live networks you could proceed with:
* `mainnet`
* `goerli`

>Note: you can't run tests on the live networks.

In a typical weekly omnibus workflow, you need only `mainnet-fork` and
`mainnet` networks. In case of large test campaign on Lido upgrades,
it also could be useful to go with `goerli` and `goerli-fork` testnets first.
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

Always pass network name explicitly with `--network {network-name}` brownie
command-line arguments for both vote and tests scripts.

To reveal a full test output pass the `-s` flag when running test scripts with
`brownie test`
#### Notes on running tests in a forked mode

* To forcibly bypass etherscan contract and event names decoding set the
`OMNIBUS_BYPASS_EVENTS_DECODING` environment variable to `1`. It could be useful
in case of etherscan downtimes or usage of some unverified contracts (especially,
on the Görli Testnet).
* To re-use the already created `vote_id` you can pass the `OMNIBUS_VOTE_ID`
environment variable (e.g. `OMNIBUS_VOTE_ID=104`).

## Repository housekeeping

Please move your outdated scripts into `scripts/archive` and outdated tests into
`tests/archive` directories.

To mask obsoleted tests and prevent them from running by `brownie test` even
when residing in archive directory, please consider to rename them:
`test_` → `xtest_`.

## Use cases and scripts examples

* [Node operators management](usecase/node_operators_management.md)
* [Reward manager tokens recovery](usecase/reward_manager_tokens_recovery.md)
