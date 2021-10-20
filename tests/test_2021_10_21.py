"""
Tests for voting 10/21/2021.
"""
import pytest
from scripts.vote_2021_10_21 import start_vote
from collections import namedtuple
from utils.config import (ldo_token_address)
from brownie import (interface)


@pytest.fixture(scope='module')
def ldo():
    return interface.ERC20(ldo_token_address)


Payout = namedtuple(
    'Payout', ['address', 'amount', 'reference']
)

def test_2021_10_21(ldo_holder, helpers, accounts, dao_voting, ldo):

    referral_payout_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'
    referral_payout_balance_before = ldo.balanceOf(referral_payout_address)
    one_inch_address = '0xf5436129cf9d8fa2a1cb6e591347155276550635'
    one_inch_balance_before = ldo.balanceOf(one_inch_address)

    vote_id, _ = start_vote({
        'from': ldo_holder
    }, silent=True)

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    referral_payout_balance_after = ldo.balanceOf(referral_payout_address)
    one_inch_balance_after = ldo.balanceOf(one_inch_address)

    assert referral_payout_balance_after - referral_payout_balance_before == 5_500 * 10**18
    assert one_inch_balance_after - one_inch_balance_before == 200_000 * 10**18
