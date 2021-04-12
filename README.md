# scripts

## Adding node operators

```bash
NODE_OPERATORS_JSON=node_operators.json brownie run add_node_operators
```

### node_operators.json

```json
{
	"node_operators": [
		{"name": "Test", "address": "0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5", "staking_limit": 0},
    ...
	]
}

```
