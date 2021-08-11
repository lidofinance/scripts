import pytest
from brownie import interface
from utils.config import (lido_dao_node_operators_registry)
from utils.node_operators import find_last_duplicated_signing_keys
from utils.node_operators import get_signing_keys, get_signing_key_indexes
from utils.utils import pp
from scripts.set_node_operators_limit import (set_node_operator_staking_limits)

NODE_OPERATORS = [
    {
        "id": 7,
        "limit": 2000
    },
]


@pytest.fixture(scope='module')
def eth_whale(accounts):
    return accounts.at('0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c',
                       force=True)


def test_assert_working():
    assert True


def test_remove_everstake_dups():
    node_operator_name = 'Everstake'
    node_operator_id = 7
    registry = interface.NodeOperatorsRegistry(lido_dao_node_operators_registry)

    operator_info = registry.getNodeOperator(node_operator_id, True)
    operator_name = operator_info[1]
    operator_address = operator_info[2]

    print('Duplicate keys removal script')
    pp('Operator Name', operator_name)
    pp('Operator address', operator_address)

    assert node_operator_name == operator_name

    start_index = 1700

    signing_keys = get_signing_keys(node_operator_id, registry, True, start_index)
    duplicated_signing_keys = find_last_duplicated_signing_keys(signing_keys)
    duplicated_signing_keys_indexes = get_signing_key_indexes(duplicated_signing_keys)

    duplicated_signing_keys_indexes_sorted = sorted(duplicated_signing_keys_indexes, reverse=True)

    # removing keys
    for index in duplicated_signing_keys_indexes_sorted:
        registry.removeSigningKeyOperatorBH(node_operator_id, index, {'from': operator_address})

    after_removal_signing_keys = get_signing_keys(node_operator_id, registry, True, start_index)
    removed_qty = len(duplicated_signing_keys)

    assert len(after_removal_signing_keys) == (len(signing_keys) - removed_qty)


def test_set_operators_limit(ldo_holder, helpers, accounts, dao_voting,
                             node_operators_registry):
    (vote_id, _) = set_node_operator_staking_limits({"from": ldo_holder},
                                                    NODE_OPERATORS)
    print(f'Vote {vote_id} created')
    helpers.execute_vote(vote_id=vote_id,
                         accounts=accounts,
                         dao_voting=dao_voting)
    print(f'Vote {vote_id} executed')

    for node_operator in NODE_OPERATORS:
        no = node_operators_registry.getNodeOperator(node_operator["id"], True)
        assert node_operator["limit"] == no[3]


def test_new_keys_are_used(eth_whale, node_operators_registry):
    lido = interface.Lido('0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84')

    lido.submit('0x0000000000000000000000000000000000000000', {'from': eth_whale, 'value': '1100 ether'})

    for i in range(0, 10):
        lido.depositBufferedEther(10, {'from': eth_whale})

    no = node_operators_registry.getNodeOperator(7, True)

    assert no[6] >= 1900
