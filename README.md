<div style="display: flex;" align="center">
  <h1 align="center">Voting scripts</h1>
  <img src="assets/voting.png" width="60" height="60" align="left" style="padding: 20px"/>
</div>

![python ~3.10](https://img.shields.io/badge/python->=3.10,<3.11-blue)
![poetry 1.8.2](https://img.shields.io/badge/poetry-1.8.2-blue)
![eth_brownie 1.20.2](https://img.shields.io/badge/eth__brownie-1.20.2-brown)
![AVotesParser 0.5.6](https://img.shields.io/badge/AVotesParser-0.5.6-brown)
![Ganache ~7.9.2-lido](https://img.shields.io/badge/ganache-7.9.2--lido-orange)
![license MIT](https://img.shields.io/badge/license-MIT-brightgreen)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Lido DAO Aragon omnibus voting scripts.

- This project uses Brownie development framework. Learn more about
  [Brownie](https://eth-brownie.readthedocs.io/en/stable/index.html).
- [Poetry](https://python-poetry.org/) dependency and packaging manager is used
  to bootstrap environment and keep the repo sane.
  </br>

## 🐳 Docker: quick and easy environment setup

**The no-brainer workflow for running scripts & tests from Docker**

#### Step 1. Clone the fresh repo:

```shell
git clone git@github.com:lidofinance/scripts.git
cd scripts
```

#### Step 2. Set up the ENV VARs for Mainnet:

| ENV VAR       | RUN TESTS     | RUN VOTES     |
| ------------- | ------------- | ------------- |
| `ETH_RPC_URL` | **mandatory**     | **mandatory**     |
| `ETH_RPC_URL2` | optional* | -     |
| `PINATA_CLOUD_TOKEN`  | -     | **mandatory**     |
| `DEPLOYER`            | -     | **mandatory**     |
| `ETHERSCAN_TOKEN`     | **mandatory**     | **mandatory**     |
| `ETHERSCAN_TOKEN2`     | optional*     | -     |

_*may be optionally set when running tests asynchronously to reduce the risk of getting 529 error_

#### Step 3. Run the container

Run the container in the `scripts` directory and specify the ENV VARs:

```shell
docker run --name scripts -v "$(pwd)":/root/scripts -e ETH_RPC_URL -e ETH_RPC_URL2 -e ETH_RPC_URL3 -e PINATA_CLOUD_TOKEN -e DEPLOYER -e ETHERSCAN_TOKEN -e ETHERSCAN_TOKEN2 -e ETHERSCAN_TOKEN3 -d ghcr.io/lidofinance/scripts:v20
```

#### Step 4. Initialize container

Run:

```shell
make docker-init
```

Note: _It may take up to 5 minutes for the container to initialize properly the first time._

#### Step 4. Now connect to the running container using tty:

```shell
docker exec -it scripts /bin/bash
```

To run a Hardhat node inside a deployed Docker container:

```shell
npx hardhat node --fork $ETH_RPC_URL
```

Do not forget to add a DEPLOYER account:

```shell
poetry run brownie accounts new <id>
```

You now have a fully functional environment to run scripts & tests in, which is linked to your local scripts repo, for example:

```shell
poetry run brownie test tests/acceptance/test_accounting_oracle.py -s
```
You can use the following shortcuts:
- `make test` run all tests on Hardhat node
- `make test vote=XXX` run all tests on Hardhat node with applied Vote #XXX
- `make test dg=XX` run all tests with executed DG proposal #XX
- `make test-1/2`, `make test-2/2` run tests divided into 2 parts (can be run asynchronously)
- `make enact-fork vote=scripts/vote_01_01_0001.py` deploy vote and enact it on mainnet fork
- `make docker` connect to the `scripts` docker container
- `make node` start local mainnet node
- `make slots` check storage slots against local node
- `make ci-prepare-environment` prepare environment for CI tests
- `make init-scripts` initialize scripts repository
- `make init-core` initialize core repository
- `make test-core` run core repository tests


or, to run core repository integrations tests:

```shell
NODE_PORT=8547 make node
poetry run brownie test tests/vote_*.py -mfh-3
make test-core
```

If your container has been stopped (for example, by a system reboot), start it:

```shell
docker start scripts
```

#### How to publish a new version of Scripts Docker image to GHCR

1. Push code changes to the repo
2. Wait for the approvals
3. Add a tag `vXX`, where `XX` is the next release number, to the commit. You can refer to the [Release](https://github.com/lidofinance/scripts/releases) page
4. Wait for the workflow **build and push image** to finish successfully on the tagged commit
5. In this README file, update the image version in section **Step 3. Run the container**

</br>

## 🏁 Manual installation

### Prerequisites

- Python >= 3.10, <3.11
- Pip >= 20.0
- Node >= 16.0
- yarn >= 1.22

</br>

#### Step 1. Install Poetry

Use the following command to install poetry:

```shell
pip install --user poetry==1.8.2
```

alternatively, you could proceed with `pipx`:

```shell
pipx install poetry==1.8.2
```

#### Step 2. Initialize the repository

Ensure that poetry bin path is added to your `$PATH` env variable.
Usually it's `$HOME/.local/bin` for most Unix-like systems.

To initialize dependencies and lido-core repository for its integration tests run:

```shell
make init
```

#### Step 3. Activate virtual environment

📝 While previous steps needed only once to init the environment from scratch,
the current step is used regularly to activate the environment every time you
need it.

```shell
poetry shell
```

#### To run a Hardhat node (preferred) instead of Ganache:

Just use the [Dockerised Hardhat Node](https://github.com/lidofinance/hardhat-node) or alternatively run it manually:

```shell
npx hardhat node --fork $ETH_RPC_URL
```

</br>

## ⚗️ Workflow

### Network setup

By default, you should start composing new scripts and test using forked networks.
You have three forked networks to work with:

- `mainnet-fork`
- `holesky-fork`
- `sepolia-fork`

To start new voting on the live networks you could proceed with:

- `mainnet`
- `holesky`
- `sepolia`

> [!CAUTION]
> You can't run tests on the live networks.

In a typical weekly omnibus workflow, you need only `mainnet-fork` and
`mainnet` networks. In case of large test campaign on Lido upgrades,
it also could be useful to go with `holesky` and `holesky-fork` testnets first.

> [!WARNING] > **Holesky is partially supported.**
> At the moment not all parameters are set in `configs/config_holesky.py` and acceptance/regression/snapshot tests are not operational.
>
> **Sepolia is partially supported.**
> At the moment not all parameters are set in `configs/config_sepolia.py` and acceptance/regression/snapshot tests are not operational.

</br>

### Environment variables setup

Despite the chosen network you always need to set the following var:

```bash
export WEB3_INFURA_PROJECT_ID=<infura_api_key>
```

To start a new vote please provide the `DEPLOYER` brownie account name (wallet):

```bash
export DEPLOYER=<brownie_wallet_name>
```

To run scripts that require decoding of EVM scripts and tests with contract name resolution via Etherscan you should provide the etherscan API token:

```bash
export ETHERSCAN_TOKEN=<etherscan_api_key>
```

To upload Markdown vote description for a new vote to IPFS you can use one of those:

1. [Pinata Cloud](https://www.pinata.cloud/) API key.
1. [Infura](https://www.infura.io/) API key for IPFS.
1. Web3 API token [web3.storage](https://web3.storage/):

```bash
# Pinata Cloud
export PINATA_CLOUD_TOKEN=<pinata_api_key>
# For Infura Web3
export WEB3_INFURA_IPFS_PROJECT_ID=<infura_project_id>
export WEB3_INFURA_IPFS_PROJECT_SECRET=<infura_project_secret>
# For WEB3
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

To run tests with already submitted DG proposals provide their ids comma-separated:

```bash
export DG_PROPOSAL_IDS=1,2,3
```

To use local ABIs for events decoding use:

```bash
export ENV_PARSE_EVENTS_FROM_LOCAL_ABI=1
```

To make default report for acceptance and regression tests after voting execution set:

```bash
export REPORT_AFTER_VOTE=1
```

To run test-1/2 at default rpc node use:
```bash
export SECONDARY_NETWORK=mfh-1
```

</br>

## Tests structure

### `tests/acceptance`

Directory contains state based tests. This tests run every time when tests suite started, if there are any voting scripts or upgrade scripts they will be applied before.

### `tests/regression`

Directory contains scenario tests. This tests run every time when tests suite started, if there are any voting scripts or upgrade scripts they will be applied before.

### `tests/snapshot`

Directory contains snapshot-scenario tests. This tests run only if there are any upgrade scripts.

### `test/vote_*.py`

Tests for current voting

</br>

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
  environment variable (e.g. `OMNIBUS_VOTE_IDS=104`)
- To re-use multiple created votes list the ids comma-separated (e.g. `OMNIBUS_VOTE_IDS=104,105`)
- To re-use the already submitted `proposal_id` you can pass the `DG_PROPOSAL_IDS`
  environment variable comma-separated (e.g. `DG_PROPOSAL_IDS=13,14`)
- To force the large CI runner usage, please name your branch with the `large-vote_` prefix.

</br>

## Code style

Please, use the shared pre-commit hooks to maintain code style:

```bash
poetry run pre-commit install
```

</br>

## Repository housekeeping

Please move your outdated scripts into `archive/scripts` and outdated tests into
`archive/tests` directories.

</br>

## Use cases and scripts examples

- [Node operators management](usecase/node_operators_management.md)
- [Reward manager tokens recovery](usecase/reward_manager_tokens_recovery.md)

</br>

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
