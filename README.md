<div style="display: flex;" align="center">
  <h1 align="center">Voting scripts</h1>
  <img src="assets/voting.png" width="60" height="60" align="left" style="padding: 20px"/>
</div>

![python ~3.10](https://img.shields.io/badge/python->=3.10,<3.11-blue)
![poetry 1.5.0](https://img.shields.io/badge/poetry-1.5.0-blue)
![eth_brownie 1.19.3](https://img.shields.io/badge/eth__brownie-1.19.3-brown)
![AVotesParser 0.5.5](https://img.shields.io/badge/AVotesParser-0.5.5-brown)
![Ganache ~7.6.0](https://img.shields.io/badge/ganache-7.6.0-orange)
![license MIT](https://img.shields.io/badge/license-MIT-brightgreen)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Lido DAO Aragon omnibus voting scripts.

## 🏁 Getting started

- This project uses Brownie development framework. Learn more about
[Brownie](https://eth-brownie.readthedocs.io/en/stable/index.html).
- [Poetry](https://python-poetry.org/) dependency and packaging manager is used
to bootstrap environment and keep the repo sane.

### Prerequisites

- Python >= 3.10, <3.11
- Pip >= 20.0
- Node >= 16.0
- yarn >= 1.22

#### Step 1. Install Poetry

Use the following command to install poetry:

```shell
pip install --user poetry==1.5.0
```

alternatively, you could proceed with `pipx`:

```shell
pipx install poetry==1.5.0
```

#### Step 2. Setup dependencies with poetry

Ensure that poetry bin path is added to your `$PATH` env variable.
Usually it's `$HOME/.local/bin` for most Unix-like systems.

This is a workaround related `brownie` deps `pyyaml` issue https://github.com/eth-brownie/brownie/issues/1701
```shell
poetry run pip install "cython<3.0" pyyaml==5.4.1 --no-build-isolation
```

```shell
poetry install
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

By default, you should start composing new scripts and test using forked networks.
You have three forked networks to work with:

- `mainnet-fork`
- `goerli-fork`
- `holesky-fork`

To start new voting on the live networks you could proceed with:

- `mainnet`
- `goerli`
- `holesky`

>Note: you can't run tests on the live networks.

In a typical weekly omnibus workflow, you need only `mainnet-fork` and
`mainnet` networks. In case of large test campaign on Lido upgrades,
it also could be useful to go with `goerli` and `goerli-fork` testnets first.

> **Holesky specifics.**
> Due to Holesky not being supported by Infura yet, setting RPC URL for Holesky is different. Instead of setting `WEB3_INFURA_PROJECT_ID` env variable set `HOLESKY_RPC_URL`.

> **Holesky is partially supported.**
> At the moment not all parameters are set in `configs/config_holesky.py` and acceptance/regression/snapshot tests are not operational.

### Environment variables setup

Despite the chosen network you always need to set the following var:

```bash
export WEB3_INFURA_PROJECT_ID=<infura_api_key>
```

To start a new vote please provide the `DEPLOYER` brownie account name (wallet):

```bash
export DEPLOYER=<brownie_wallet_name>
```

To run tests with a contract name resolution guided by the Etherscan you should
provide the etherscan API token:

```bash
export ETHERSCAN_TOKEN=<etherscan_api_key>
```
To upload Markdown vote description for a new vote to IPFS you should
provide the [web3.storage](https://web3.storage/tokens/) API token:

```bash
export WEB3_STORAGE_TOKEN=<web3_storage_api_key>
```
See [here](utils/README.md#ipfs) to learn more Markdown description

To skip events decoding while testing set the following var:

```bash
export OMNIBUS_BYPASS_EVENTS_DECODING=1
```

To run tests with already started vote provide its id:

```bash
export OMNIBUS_VOTE_IDS=156
```

To use local ABIs for events decoding use:

```bash
export ENV_PARSE_EVENTS_FROM_LOCAL_ABI=1
```

To make default report for acceptance and regression tests after voting execution set:

```bash
export REPORT_AFTER_VOTE=1
```

## Tests structure

### `tests/acceptance`

Directory contains state based tests. This tests run every time when tests suite started, if there are any voting scripts or upgrade scripts they will be applied before.

### `tests/regression`

Directory contains scenario tests. This tests run every time when tests suite started, if there are any voting scripts or upgrade scripts they will be applied before.

### `tests/snapshot`

Directory contains snapshot-scenario tests. This tests run only if there are any upgrade scripts.

### `test/vote_*.py`

Tests for current voting

### Test run

To run all the test on `mainnet-fork` execute

```bash
brownie test
```

You can pass network name explicitly with `--network {network-name}` brownie
command-line argument.

To reveal a full test output pass the `-s` flag

See [here](tests/README.md) to learn more about tests

#### Notes on running tests in a forked mode

- To forcibly bypass etherscan contract and event names decoding set the
`OMNIBUS_BYPASS_EVENTS_DECODING` environment variable to `1`. It could be useful
in case of etherscan downtimes or usage of some unverified contracts (especially,
on the Görli Testnet).
- To re-use the already created `vote_id` you can pass the `OMNIBUS_VOTE_IDS`
environment variable (e.g. `OMNIBUS_VOTE_IDS=104`).
- To re-use multiple created votes list the ids comma-separated (e.g. `OMNIBUS_VOTE_IDS=104,105`)
- To force the large CI runner usage, please name your branch with the `large-vote_` prefix.

## Code style

Please, use the shared pre-commit hooks to maintain code style:

```bash
poetry run pre-commit install
```

## Repository housekeeping

Please move your outdated scripts into `archive/scripts` and outdated tests into
`archive/tests` directories.

## Use cases and scripts examples

- [Node operators management](usecase/node_operators_management.md)
- [Reward manager tokens recovery](usecase/reward_manager_tokens_recovery.md)

## Troubleshooting

### Invalid hashes (step 2)

If you have encountered `Invalid hashes` errors while trying to run previous command, please remove poetry's cache:

- GNU/Linux

```shell
rm -rf ~/.cache/pypoetry/cache/
rm -rf ~/.cache/pypoetry/artifacts/
```

- MAC OS:

```shell
rm -rf ~/Library/Caches/pypoetry/cache
rm -rf ~/Library/Caches/pypoetry/artifacts
```
