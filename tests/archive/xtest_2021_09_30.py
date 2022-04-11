"""
Tests for voting 09/30/2021.
"""
import pytest
from scripts.vote_2021_09_30 import start_vote
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
    NodeOperatorIncLimit('Blockdaemon', 13, 950),
]


def test_2021_09_30(ldo_holder, helpers, accounts, dao_voting, ldo, node_operators_registry):
    referral_payout_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'
    referral_payout_balance_before = ldo.balanceOf(referral_payout_address)

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

    referral_payout_balance_after = ldo.balanceOf(referral_payout_address)

    assert referral_payout_balance_after - referral_payout_balance_before == 101_133_42 * 10 ** 16
