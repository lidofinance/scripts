from utils.evm_script import encode_call_script


def encode_set_node_operator_staking_limit(id, limit, registry):
    return (
        registry.address,
        registry.setNodeOperatorStakingLimit.encode_input(id, limit)
    )


def encode_set_node_operators_staking_limits_evm_script(node_operators, registry):
    return encode_call_script([
        encode_set_node_operator_staking_limit(id=node_operator["id"],
                                               limit=node_operator["limit"],
                                               registry=registry)
        for node_operator in node_operators
    ])
