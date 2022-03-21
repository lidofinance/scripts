"""
Tests for voting 10/05/2021.
"""
import pytest
from scripts.vote_2021_10_05 import start_vote
from collections import namedtuple
from utils.config import (ldo_token_address)
from brownie import (interface)


@pytest.fixture(scope='module')
def ldo():
    return interface.ERC20(ldo_token_address)


NodeOperatorIncLimit = namedtuple(
    'NodeOperatorIncLimit', ['name', 'id', 'limit'],
)

NODE_OPERATORS = [
    # name, id, limit
    NodeOperatorIncLimit('Staking Facilities', 0, 4400),
    NodeOperatorIncLimit('Certus One', 1, 1000),
    NodeOperatorIncLimit('p2p', 2, 5265),
    NodeOperatorIncLimit('Chorus One', 3, 5000),
    NodeOperatorIncLimit('stakefish', 4, 5265),
    NodeOperatorIncLimit('Blockscape', 5, 5265),
    NodeOperatorIncLimit('DSRV', 6, 4000),
    NodeOperatorIncLimit('Everstake', 7, 3000),
    NodeOperatorIncLimit('SkillZ', 8, 5265),
    NodeOperatorIncLimit('RockX', 9, 684),
    NodeOperatorIncLimit('Figment', 10, 683),
    NodeOperatorIncLimit('Allnodes', 11, 683),
    NodeOperatorIncLimit('Anyblock Analytics', 12, 683),
    NodeOperatorIncLimit('Blockdaemon', 13, 683),

]


def test_2021_10_05(ldo_holder, helpers, accounts, dao_voting, ldo, node_operators_registry):
    vote_id, _ = start_vote({
        'from': ldo_holder
    }, silent=True)

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    for node_operator in NODE_OPERATORS:
        nop = node_operators_registry.getNodeOperator(
            node_operator.id, True
        )
        limit = nop[3]
        used = nop[6]
        assert limit == node_operator.limit, f'Failed on {node_operator.name}'
        assert used == limit, f'Not used on {node_operator.name}'
