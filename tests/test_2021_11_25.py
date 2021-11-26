"""
Tests for voting 25/11/2021.
"""
import pytest
from collections import namedtuple

from scripts.vote_2021_11_25 import start_vote

Payout = namedtuple(
    'Payout', ['address', 'amount']
)

dao_agent_address = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'
finance_multisig_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'

isidoros_payout = Payout(
    address=finance_multisig_address,
    amount=3_100 * (10 ** 18)
)

referral_payout = Payout(
    address=finance_multisig_address,
    amount=124_987_5031 * (10 ** 14)
)

def test_2021_11_25(helpers, accounts, lido, ldo_holder, dao_voting, ldo_token):
    multisig_balance_before = ldo_token.balanceOf(finance_multisig_address)
    dao_balance_before = ldo_token.balanceOf(dao_agent_address)

    vote_id, _ = start_vote({
        'from': ldo_holder
    }, silent=True)

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    multisig_balance_after = ldo_token.balanceOf(finance_multisig_address)
    dao_balance_after = ldo_token.balanceOf(dao_agent_address)

    assert multisig_balance_after - multisig_balance_before == isidoros_payout.amount + referral_payout.amount
    assert dao_balance_before - dao_balance_after == isidoros_payout.amount + referral_payout.amount
