from brownie import interface

from utils.voting import create_vote
from utils.config import (lido_dao_voting_address,
                          lido_dao_token_manager_address,
                          lido_dao_node_operators_registry,
                          get_deployer_account)
from utils.evm_script import encode_call_script

import json, sys, os, re, time

from utils.node_operators import encode_remove_signing_keys


def fetch_last_duplicated_indexes(node_operator_id, index_start, index_end, duplicated_pubkeys):
    return [1778, 1779, 1780, 1781, 1782, 1783, 1784, 1785]


def remove_signing_keys(node_operator_id, indexes_to_remove):

    evm_script = encode_remove_signing_keys(node_operator_id, indexes_to_remove)

    return create_vote(
        voting=interface.Voting(lido_dao_voting_address),
        token_manager=interface.TokenManager(lido_dao_token_manager_address),
        vote_desc=
        f'Add node operators: \n{os.linesep.join(["{} with address {}".format(no["name"], no["address"]) for no in node_operators])}',
        evm_script=evm_script,
        tx_params=tx_params)


def main():
    file_path = os.environ['KEY_DUPLICATES_JSON']
    with open(file_path) as json_file:
        key_duplicates_data = json.load(json_file)

        # validate_key_duplicates_data(key_duplicates_data)

        node_operator_id = key_duplicates_data["nodeOperatorId"]
        index_start = key_duplicates_data["indexStart"]
        index_end = key_duplicates_data["indexEnd"]
        duplicated_pubkeys = key_duplicates_data["duplicatedPubkeys"]

        print('node_operator_id', node_operator_id)
        print('index_start', index_start)
        print('index_end', index_end)
        print('duplicated_pubkeys', len(duplicated_pubkeys))

        indexes_to_remove = fetch_last_duplicated_indexes(
            node_operator_id,
            index_start,
            index_end,
            duplicated_pubkeys
        )

        (vote_id, _) = remove_signing_keys(
            node_operator_id,
            indexes_to_remove,
            {"from": get_deployer_account()}
        )

        # (vote_id, _) = add_node_operators({"from": get_deployer_account()},
        #                                   node_operators)
        # time.sleep(5)  # hack: waiting thread 2
        print(f'Voting created: {vote_id}')
    return 0


def validate_key_duplicates_data(key_duplicates_data):
    for node_operator in node_operators:
        assert re.search(r"^(0x)?[0-9a-f]{40}$", node_operator["address"],
                         re.IGNORECASE) is not None

        assert 'name' in node_operator, "Node operator should contain \"name\""
        assert bool(node_operator["name"].strip()
                    ), "Node operators name should not be empty "

    addresses = [no["address"] for no in node_operators]
    assert len(addresses) == len(set(addresses))


