from pytest import raises
from scripts.set_node_operators_limit import (set_node_operator_staking_limits,
                                              validate_data)

NODE_OPERATORS = [
    {
        "id": 0,
        "limit": 0
    },
    {
        "id": 3,
        "limit": 10
    },
    {
        "id": 5,
        "limit": 10
    },
    {
        "id": 6,
        "limit": 10
    },
]


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


def test_validator():
    validate_data(NODE_OPERATORS)


def test_validator_failed_on_duplicate():
    with raises(Exception):
        validate_data((NODE_OPERATORS[0], NODE_OPERATORS[0]))


def test_validator_failed_on_wrong_id():
    with raises(Exception):
        validate_data(({"id": -1, "limit": 20}))


def test_validator_failed_on_wrong_limit():
    with raises(Exception):
        validate_data(({"id": 1, "limit": -20}))


def test_validator_failed_on_not_existing_node_operator():
    with raises(Exception):
        validate_data(({"id": 1000000, "limit": 20}))
