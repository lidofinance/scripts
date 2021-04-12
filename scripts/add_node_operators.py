from brownie import ZERO_ADDRESS, accounts
from brownie import interface

from utils.voting import create_vote
from utils.config import (lido_dao_voting_address,
                          lido_dao_token_manager_address,
                          lido_dao_node_operators_registry,
                          get_deployer_account)
from utils.evm_script import encode_call_script

import json, sys, os


def encode_add_operator(name, address, staking_limit):
    return (lido_dao_node_operators_registry,
            interface.NodeOperatorsRegistry(
                lido_dao_node_operators_registry).addNodeOperator.encode_input(
                    name, address, staking_limit))


def add_node_operators(tx_params, node_operators):

    evm_script = encode_call_script([
        encode_add_operator(name=node_operator["name"],
                            address=node_operator["address"],
                            staking_limit=node_operator["staking_limit"])
        for node_operator in node_operators
    ])

    return create_vote(
        voting=interface.Voting(lido_dao_voting_address),
        token_manager=interface.TokenManager(lido_dao_token_manager_address),
        vote_desc=f'Add operators : [] with staking limit 0',
        evm_script=evm_script,
        tx_params=tx_params)


def main():
    file_path = os.environ['NODE_OPERATORS_JSON']
    with open(file_path) as json_file:
        data = json.load(json_file)
        (vote_id, _) = add_node_operators({"from": get_deployer_account()},
                                          data["node_operators"])
    return (f'Voting {vote_id}')
