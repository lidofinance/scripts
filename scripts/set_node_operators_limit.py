from brownie import interface

from utils.voting import create_vote
from utils.config import (lido_dao_voting_address,
                          lido_dao_token_manager_address,
                          lido_dao_node_operators_registry,
                          get_deployer_account)
from utils.evm_script import encode_call_script
from utils.node_operators import encode_set_node_operators_staking_limits_evm_script

import json, sys, os, re, time


def set_node_operator_staking_limits(tx_params, node_operators):
    registry = interface.NodeOperatorsRegistry(lido_dao_node_operators_registry)
    evm_script = encode_set_node_operators_staking_limits_evm_script(node_operators, registry)
    return create_vote(
        voting=interface.Voting(lido_dao_voting_address),
        token_manager=interface.TokenManager(lido_dao_token_manager_address),
        vote_desc=
        f'Set staking limit for operators: \n{os.linesep.join(["id {} set limit to {}".format(no["id"], no["limit"]) for no in node_operators])}',
        evm_script=evm_script,
        tx_params=tx_params)


def main():
    file_path = os.environ['NODE_OPERATORS_JSON']
    with open(file_path) as json_file:
        data = json.load(json_file)
        node_operators = data["node_operators"]
        validate_data(node_operators)
        (vote_id, _) = set_node_operator_staking_limits(
            {"from": get_deployer_account()}, node_operators)
        time.sleep(5)  # hack: waiting thread 2
        print(f'Voting created: {vote_id}')
    return 0


def validate_data(node_operators):
    for node_operator in node_operators:
        assert 'id' in node_operator, "Node operator should contain \"id\""
        assert node_operator["id"] >= 0
        assert 'limit' in node_operator, "Node operator should contain \"limit\""
        assert node_operator["limit"] >= 0

        interface.NodeOperatorsRegistry(
            lido_dao_node_operators_registry).getNodeOperator(
                node_operator["id"], True)

    ids = [no["id"] for no in node_operators]
    assert len(ids) == len(set(ids)), "Duplicated operators"
