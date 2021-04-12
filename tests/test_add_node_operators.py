import pytest
from scripts.add_node_operators import add_node_operators

NODE_OPERATORS = [{
    "name": "Test",
    "address": "0x54032650b14df07b85bF18A3a3eC8E0Af2e028d5",
    "staking_limit": 0
},
{
    "name": "Test1",
    "address": "0x54034650b14df07b85bF18A3a3eC8E0Af2e028d5",
    "staking_limit": 0
},
{
    "name": "Test2",
    "address": "0x54033650b14df07b85bF18A3a3eC8E0Af2e028d5",
    "staking_limit": 0
},
{
    "name": "Test4",
    "address": "0x54035650b14df07b85bF18A3a3eC8E0Af2e028d5",
    "staking_limit": 0
}]


def getNodeOperatorsList(node_operators_registry):
    return [
        node_operators_registry.getNodeOperator(i, True)
        for i in range(int(node_operators_registry.getNodeOperatorsCount()))
    ]


def test_add_operators(ldo_holder, helpers, accounts, dao_voting,
                        node_operators_registry):
    (vote_id, _) = add_node_operators({"from": ldo_holder}, NODE_OPERATORS)
    print(f'Vote {vote_id} created')
    helpers.execute_vote(vote_id=vote_id,
                         accounts=accounts,
                         dao_voting=dao_voting)
    print(f'Vote {vote_id} executed')
    active_node_operators = getNodeOperatorsList(node_operators_registry)

    for node_operator in NODE_OPERATORS:
        assert len([
            no for no in active_node_operators
            if node_operator["name"] == no[1] and node_operator["address"] ==
            no[2] and node_operator["staking_limit"] == no[4]
        ]) > 0
