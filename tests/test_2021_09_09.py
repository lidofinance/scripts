"""
Tests for voting 09/09/2021.
"""
import pytest

from collections import namedtuple

from brownie import interface  # noqa

from scripts.vote_2021_09_09 import start_vote

from utils.config import ldo_token_address

NodeOperatorIncLimit = namedtuple(
    'NodeOperatorIncLimit', ['name', 'id', 'limit'],
)
Payout = namedtuple(
    'Payout', ['address', 'amount', 'reference']
)

NODE_OPERATORS = [
    # name, id, limit
    NodeOperatorIncLimit('p2p', 2, 7800),
    NodeOperatorIncLimit('DSRV', 6, 4000),
    NodeOperatorIncLimit('Blockdaemon', 13, 100)
]

curve_payout = Payout(
    address='0x753D5167C31fBEB5b49624314d74A957Eb271709',
    amount=3_550_000 * (10 ** 18),
    reference='Curve pool LP rewards transfer',
)
balancer_payout = Payout(
    address='0x1dD909cDdF3dbe61aC08112dC0Fdf2Ab949f79D8',
    amount=300_000 * (10 ** 18),
    reference='Balancer pool LP rewards transfer',
)
sushi_payout = Payout(
    address='0xE5576eB1dD4aA524D67Cf9a32C8742540252b6F4',
    amount=200_000 * (10 ** 18),
    reference='Sushi pool LP rewards transfer',
)
grant_payout = Payout(
    address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
    amount=54_000 * (10 ** 18),
    reference='ETH1 Execution Client Teams LEGO Grant',
)


def curve_balance(ldo) -> int:
    """Return balance for target of curve payout."""
    return ldo.balanceOf(curve_payout.address)

def balancer_balance(ldo) -> int:
    """Return balance for target of balancer payout."""
    return ldo.balanceOf(balancer_payout.address)

def sushi_balance(ldo) -> int:
    """Return balance for target of sushi payout."""
    return ldo.balanceOf(sushi_payout.address)

def grant_balance(ldo) -> int:
    """Return balance for target of grant payout."""
    return ldo.balanceOf(grant_payout.address)


@pytest.fixture(scope='module')
def ldo():
    """Return contract of LDO token."""
    return interface.ERC20(ldo_token_address)


def test_common(
        ldo_holder, helpers, accounts,
        dao_voting, ldo, node_operators_registry
):
    """Perform testing for the whole voting."""
    curve_balance_before = curve_balance(ldo)
    balancer_balance_before = balancer_balance(ldo)
    sushi_balance_before = sushi_balance(ldo)
    grant_balance_before = grant_balance(ldo)

    vote_id, _ = start_vote({
        'from': ldo_holder
    }, silent=True)

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    curve_balance_after = curve_balance(ldo)
    balancer_balance_after = balancer_balance(ldo)
    sushi_balance_after = sushi_balance(ldo)
    grant_balance_after = grant_balance(ldo)

    curve_inc = curve_balance_after - curve_balance_before
    balancer_inc = balancer_balance_after - balancer_balance_before
    sushi_inc = sushi_balance_after - sushi_balance_before
    grant_inc = grant_balance_after - grant_balance_before

    assert curve_inc == curve_payout.amount, 'Failed on Curve'
    assert balancer_inc == balancer_payout.amount, 'Failed on Balancer'
    assert sushi_inc == sushi_payout.amount, 'Failed on Sushi'
    assert grant_inc == grant_payout.amount, 'Failed on Grant'

    for node_operator in NODE_OPERATORS:
        assert node_operators_registry.getNodeOperator(
            node_operator.id, True
        )[3] == node_operator.limit, f'Failed on {node_operator.name}'
