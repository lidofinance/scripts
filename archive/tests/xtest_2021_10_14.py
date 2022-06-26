"""
Tests for voting 10/14/2021.
"""
import pytest
from scripts.vote_2021_10_14 import start_vote
from collections import namedtuple
from utils.config import (ldo_token_address)
from brownie import (interface)


@pytest.fixture(scope='module')
def ldo():
    return interface.ERC20(ldo_token_address)


Payout = namedtuple(
    'Payout', ['address', 'amount', 'reference']
)


def test_2021_10_14(ldo_holder, helpers, accounts, dao_voting, ldo):
    referral_payout_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'
    referral_payout_balance_before = ldo.balanceOf(referral_payout_address)
    sushi_address = '0xE5576eB1dD4aA524D67Cf9a32C8742540252b6F4'
    sushi_balance_before = ldo.balanceOf(sushi_address)

    vote_id, _ = start_vote({
        'from': ldo_holder
    }, silent=True)

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    referral_payout_balance_after = ldo.balanceOf(referral_payout_address)
    sushi_balance_after = ldo.balanceOf(sushi_address)

    assert referral_payout_balance_after - referral_payout_balance_before == 303_142_5 * 10 ** 17
    assert sushi_balance_after - sushi_balance_before == 200_000 * 10 ** 18
