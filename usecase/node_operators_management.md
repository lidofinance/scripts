### 🕸️ Notes for the node operators management ops

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
