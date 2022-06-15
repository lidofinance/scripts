<div style="display: flex;" align="center">
  <h1 align="center">Voting scripts</h1>
  <img src="assets/voting.png" width="60" height="60" align="left" style="padding: 20px"/>
</div>

![python ~3.9](https://img.shields.io/badge/python->=3.8,<3.10-blue)
![poetry 1.1.13](https://img.shields.io/badge/poetry-1.1.13-blue)
![eth_brownie 1.19.0](https://img.shields.io/badge/eth__brownie-1.19.0-brown)
![AVotesParser 0.5.1](https://img.shields.io/badge/AVotesParser-0.5.1-brown)
![Ganache ~7.3.0](https://img.shields.io/badge/ganache-7.3.0-orange)
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
poetry run brownie networks import network-config.yaml True
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

## Common tests

There are two groups of common tests in `tests` directory: regression
(`tests/common/regression/test_*.py`) and snapshot (`tests/common/snapshot/test_*.py`).

The regression tests check the on-chain protocol state:
1) after executing the vote script `scripts/vote_*.py` if it exists
2) just the current on-chain state otherwise

The snapshot tests run only if the vote script exists.

If there are multiple vote scripts all the scripts are run and executed
sequentially in lexicographical order by script name.

### Common tests in master branch

As there is no vote script (as the workflow defines) only the regression tests run.

### Common tests in omnibus branch

As the vote script exists (as the workflow defines):
a) the regression tests run after executing the vote
b) the snapshot tests run

### Snapshot tests

By snapshot here we denote a subset of storage data of a contract (or multiple contracts).
The ideas is to check that the voting doesn't modify a contract storage other than the
expected changes.

Snapshot tests work as follows:
1) Go over some protocol use scenario (e. g. stake by use + oracle report)
2) Store the snapshot along the steps
3) Revert the chain changes
4) Execute the vote
5) Do (1) and (2) again
6) Compare the snapshots got during the first and the second scenario runs
7) The expected outcome is that the voting doesn't change

Current snapshot implementation in kind of MVP and need a number of issues to
be addressed in the future:
1) expand the number of storage variables observed
2) allow modification of the storage variables supposed not to be changed after
the voting without modification of the common test files
3) extract getters from ABIs automatically

## Use cases and scripts examples

* [Node operators management](usecase/node_operators_management.md)
* [Reward manager tokens recovery](usecase/reward_manager_tokens_recovery.md)
