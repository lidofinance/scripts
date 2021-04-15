from brownie import interface

from utils.voting import create_vote
from utils.config import (lido_dao_voting_address,
                          lido_dao_token_manager_address,
                          lido_dao_node_operators_registry,
                          get_deployer_account)
from utils.evm_script import encode_call_script

import json, sys, os, re, time


def encode_add_operator(name, address):
    return (lido_dao_node_operators_registry,
            interface.NodeOperatorsRegistry(
                lido_dao_node_operators_registry).addNodeOperator.encode_input(
                    name, address, 0))


def add_node_operators(tx_params, node_operators):

    evm_script = encode_call_script([
        encode_add_operator(name=node_operator["name"],
                            address=node_operator["address"])
        for node_operator in node_operators
    ])

    return create_vote(
        voting=interface.Voting(lido_dao_voting_address),
        token_manager=interface.TokenManager(lido_dao_token_manager_address),
        vote_desc=
        f'Add node operators: \n{os.linesep.join(["{} with address {}".format(no["name"], no["address"]) for no in node_operators])}',
        evm_script=evm_script,
        tx_params=tx_params)


def main():
    file_path = os.environ['NODE_OPERATORS_JSON']
    with open(file_path) as json_file:
        data = json.load(json_file)
        node_operators = data["node_operators"]
        validate_node_operators_data(node_operators)
        (vote_id, _) = add_node_operators({"from": get_deployer_account()},
                                          node_operators)
        time.sleep(5)  # hack: waiting thread 2
        print(f'Voting created: {vote_id}')
    return 0


def validate_node_operators_data(node_operators):
    for node_operator in node_operators:
        assert re.search(r"^(0x)?[0-9a-f]{40}$", node_operator["address"],
                         re.IGNORECASE) is not None

        assert 'name' in node_operator, "Node operator should contain \"name\""
        assert bool(node_operator["name"].strip()
                    ), "Node operators name should not be empty "

    addresses = [no["address"] for no in node_operators]
    assert len(addresses) == len(set(addresses))
