# scripts

Repository for internal scripts.

## Mainnet setup

By default, all scripts run in mainnet fork mode (don't forget to edit fork param at brownie config). To run scripts on actually mainnet you need to add param `--network mainnet` to the end of the command and set the following env variables:

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


## Remove node operator keys duplicates

```bash
KEY_DUPLICATES_JSON=key-duplicates.json brownie run check_remove_node_operator_key_duplicates
```

key-duplicates.json

```json
{
  "nodeOperatorId": 7,
  "indexStart": 1700,
  "indexEnd": 1800,
  "signingKeys": [
    {
      "index": 1760,
      "key": "0x8d66e1917a9109b6840f9584ab3195c1cfec19e18081963cb264d82795dee8bf3f70e7e387d03885c0d3751263fb6447"
    },
    ...
  ]
}
```