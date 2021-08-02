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


def get_node_operators(registry):
    return [{**registry.getNodeOperator(i, True), **{'index': i}} for i in range(registry.getNodeOperatorsCount())]


def encode_remove_signing_key(id, index_to_remove, registry):
    return (
        registry.address,
        registry.removeSigningKey.encode_input(id, index_to_remove)
    )


def encode_remove_signing_keys(id, indexes_to_remove, registry):
    return [
        encode_remove_signing_key(id=id,
                                  index_to_remove=key_index,
                                  registry=registry)
        for key_index in indexes_to_remove
    ]
