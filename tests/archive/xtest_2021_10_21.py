"""
Tests for voting 10/21/2021.
"""
from collections import namedtuple

from scripts.vote_2021_10_21 import start_vote

Payout = namedtuple(
    'Payout', ['address', 'amount']
)

referral_payout = Payout(
    address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
    amount=5_500 * 10 ** 18
)

one_inch_payout = Payout(
    address='0xf5436129cf9d8fa2a1cb6e591347155276550635',
    amount=200_000 * 10 ** 18
)


def test_2021_10_21(ldo_holder, helpers, accounts, dao_voting, ldo_token):
    referral_payout_balance_before = ldo_token.balanceOf(
        referral_payout.address
    )
    one_inch_balance_before = ldo_token.balanceOf(
        one_inch_payout.address
    )

    vote_id, _ = start_vote({
        'from': ldo_holder
    }, silent=True)

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    referral_payout_balance_after = ldo_token.balanceOf(
        referral_payout.address
    )
    one_inch_balance_after = ldo_token.balanceOf(
        one_inch_payout.address
    )

    assert referral_payout_balance_after - referral_payout_balance_before == referral_payout.amount
    assert one_inch_balance_after - one_inch_balance_before == one_inch_payout.amount
