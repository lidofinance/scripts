"""
Tests for voting 09/23/2021.
"""
import pytest
from scripts.vote_2021_09_23 import start_vote
from collections import namedtuple
from utils.config import (ldo_token_address)
from brownie import (interface)


@pytest.fixture(scope='module')
def ldo():
    return interface.ERC20(ldo_token_address)


NodeOperatorIncLimit = namedtuple(
    'NodeOperatorIncLimit', ['name', 'id', 'limit'],
)
Payout = namedtuple(
    'Payout', ['address', 'amount', 'reference']
)

NODE_OPERATORS = [
    # name, id, limit
    NodeOperatorIncLimit('Everstake', 7, 5000),
    NodeOperatorIncLimit('Blockdaemon', 13, 200),
]


def test_2021_09_23(ldo_holder, helpers, accounts, dao_voting, ldo, node_operators_registry):

    stsol_rewards_address = '0xaE49a2C1e2CD3D8f2679a4A49db58983B8de343E'
    stsol_rewards_balance_before = ldo.balanceOf(stsol_rewards_address)

    jacob_payout_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'
    jacob_payout_balance_before = ldo.balanceOf(jacob_payout_address)

    vote_id, _ = start_vote({
        'from': ldo_holder
    }, silent=True)

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    for node_operator in NODE_OPERATORS:
        assert node_operators_registry.getNodeOperator(
            node_operator.id, True
        )[3] == node_operator.limit, f'Failed on {node_operator.name}'

    stsol_rewards_balance_after = ldo.balanceOf(stsol_rewards_address)
    jacob_payout_balance_after = ldo.balanceOf(jacob_payout_address)

    assert stsol_rewards_balance_after - stsol_rewards_balance_before == 400_000 * 10**18
    assert jacob_payout_balance_after - jacob_payout_balance_before == 3_500 * 10**18
