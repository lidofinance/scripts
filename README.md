# scripts

Repository for internal scripts.

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
