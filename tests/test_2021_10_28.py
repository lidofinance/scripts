"""
Tests for voting 10/28/2021.
"""
from collections import namedtuple

from scripts.vote_2021_10_28 import start_vote

Payout = namedtuple(
    'Payout', ['address', 'amount']
)

referral_payout = Payout(
    address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
    amount=138_162_5642 * 10 ** 14
)

def test_2021_10_21(ldo_holder, helpers, accounts, dao_voting, ldo_token, deposit_security_module):
    referral_payout_balance_before = ldo_token.balanceOf(
        referral_payout.address
    )
    assert deposit_security_module.isPaused() == True

    vote_id, _ = start_vote({
        'from': ldo_holder
    }, silent=True)

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    referral_payout_balance_after = ldo_token.balanceOf(
        referral_payout.address
    )

    assert deposit_security_module.isPaused() == False
    assert referral_payout_balance_after - referral_payout_balance_before == referral_payout.amount
