from pytest import raises
from scripts.add_node_operators import (add_node_operators,
                                        validate_node_operators_data)

NODE_OPERATORS = [{
    "name": "Test",
    "address": "0x54032650b14df07b85bF18A3a3eC8E0Af2e028d5"
}, {
    "name": "Test1",
    "address": "0x54034650b14df07b85bF18A3a3eC8E0Af2e028d5"
}, {
    "name": "Test2",
    "address": "0x54033650b14df07b85bF18A3a3eC8E0Af2e028d5"
}, {
    "name": "Test4",
    "address": "0x54035650b14df07b85bF18A3a3eC8E0Af2e028d5"
}]


def get_node_operators(node_operators_registry):
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
    active_node_operators = get_node_operators(node_operators_registry)

    for node_operator in NODE_OPERATORS:
        assert len([
            no
            for no in active_node_operators if node_operator["name"] == no[1]
                                               and node_operator["address"] == no[2]
        ]) > 0


def test_validator():
    validate_node_operators_data(NODE_OPERATORS)


def test_validator_faild_on_duplicate():
    with raises(Exception):
        validate_node_operators_data((NODE_OPERATORS[0], NODE_OPERATORS[0]))


def test_validator_faild_on_address_length():
    with raises(Exception):
        validate_node_operators_data(({
            "name": "Test",
            "address": "0x54032650b14df07b85bF18A3a3eC8E02e028d5"
        }))
