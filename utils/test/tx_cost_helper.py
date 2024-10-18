def transaction_cost(tx):
    gas_used = tx.gas_used
    gas_price = tx.gas_price
    return gas_used * gas_price
