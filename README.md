# scripts

Repository for internal scripts.
Primarily, these scripts are used on omnibus voting.

## Network setup

In a typical weekly omnibus workflow, you need only the `mainnet-fork` and `mainnet` networks. In the case of a large test campaign on Lido upgrades, it also could be useful to go with `görli` and `görli-fork` testnets first.

This section covers network configuration params and their usage.

### Environment variables setup

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

### Command-line arguments requirements

Always pass network name explicitly with `--network {network-name}` brownie command-line arguments for both vote and tests scripts.

To reveal a full test output pass the `-s` flag when running test scripts with `brownie test`
#### Fork-mode development networks

By default, you should start testing process in a network fork mode (don't forget to review brownie fork params). The Mainnet-fork mode exists in brownie by default. To add the Görli Testnet fork mode please run once the following command (to setup and save new network):
```bash
brownie networks add "Development" goerli-fork host=http://127.0.0.1 cmd=ganache-cli port=8545 gas_limit=12000000 fork=https://goerli.infura.io/v3/${WEB3_INFURA_PROJECT_ID} chain_id=5 mnemonic=brownie accounts=10
```
Now you have the `goerli-fork` brownie network configuration to work with.

##### Notes on running tests in a forked mode

* To forcibly bypass etherscan contract and event names decoding set the `OMNIBUS_BYPASS_EVENTS_DECODING` environment variable to `1`. It could be useful in case of etherscan downtimes or usage of some unverified contracts (especially, on the Görli Testnet).
* To re-use the already created `vote_id` you can pass the `OMNIBUS_VOTE_ID` environment variable (e.g. `OMNIBUS_VOTE_ID=104`).

#### Live networks

You can start votes on the live networks by running scripts either on the Mainnet (setting `--network mainnet`) or on the Görli Testnet (`--network goerli`). You can't run tests on the live networks.

## Notes for the node operators management ops

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
