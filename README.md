# scripts

## Adding node operators

```bash
NODE_OPERATORS_JSON=node_operators.json brownie run add_node_operators
```

### node_operators.json

```json
{
  "node_operators": [
    {
      "name": "Test", 
      "address": "0x000...", 
      "staking_limit": 0
      },
    ...
  ]
}

```
