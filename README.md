# scripts

Repository for internal scripts.
Primarily, these scripts used on omnibus voting.

## Network setup
#### Mainnet-fork (default)

By default, all scripts run in mainnet fork mode (don't forget to review fork param at brownie config. 

To run tests you need to set the additional brownie commandline params: `--network mainnet-fork` and `-s`. The first one needed for etherscan addresses resolving and the second one to reveal stdout. Also, define the following env variables: 

```bash
export ETHERSCAN_TOKEN=<etherscan_key>
export WEB3_INFURA_PROJECT_ID=<infura_key>
```
#### Mainnet

To run scripts on actually mainnet you need to add param `--network mainnet` to the end of the command and set the following env variables:

```bash
export DEPLOYER=<brownie_wallet_name>
export WEB3_INFURA_PROJECT_ID=<infura_key>
```

## Adding node operators

Script to pack up adding new node operators in one vote

```bash
NODE_OPERATORS_JSON=node_operators.json brownie run add_node_operators
```

### node_operators.json

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

## Setting node operators limits

Script to pack up setting node operators staking limits in one vote

```bash
NODE_OPERATORS_JSON=node_operators.json brownie run set_node_operators_limit
```

### node_operators.json

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
