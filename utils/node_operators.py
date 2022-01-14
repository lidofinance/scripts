from utils.evm_script import encode_call_script

from utils.config import contracts

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


def _encode_add_operator(address, name, registry):
    return (registry.address, registry.addNodeOperator.encode_input(name, address))

def encode_add_operator_lido(address, name):
    return _encode_add_operator(address, name, contracts.node_operators_registry)