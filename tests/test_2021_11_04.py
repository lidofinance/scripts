"""
Tests for voting 11/04/2021.
"""
import pytest
from collections import namedtuple

from scripts.vote_2021_11_04 import start_vote

Payout = namedtuple(
    'Payout', ['address', 'amount']
)

payout_curve = Payout(
    address='0x753D5167C31fBEB5b49624314d74A957Eb271709',
    amount=3_550_000 * 10 ** 18
)
payout_balancer = Payout(
    address='0x1dD909cDdF3dbe61aC08112dC0Fdf2Ab949f79D8',
    amount=300_000 * 10 ** 18
)
payout_stsol = Payout(
    address='0xaE49a2C1e2CD3D8f2679a4A49db58983B8de343E',
    amount=400_000 * 10 ** 18
)


def test_2021_11_04(ldo_holder, helpers, accounts, dao_voting, ldo_token, deposit_security_module):
    curve_balance_before = ldo_token.balanceOf(payout_curve.address)
    balancer_balance_before = ldo_token.balanceOf(payout_balancer.address)
    stsol_balance_before = ldo_token.balanceOf(payout_stsol.address)

    vote_id, _ = start_vote({
        'from': ldo_holder
    }, silent=True)

    helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    curve_balance_after = ldo_token.balanceOf(payout_curve.address)
    balancer_balance_after = ldo_token.balanceOf(payout_balancer.address)
    stsol_balance_after = ldo_token.balanceOf(payout_stsol.address)

    assert curve_balance_after - curve_balance_before == payout_curve.amount
    assert balancer_balance_after - balancer_balance_before == payout_balancer.amount
    assert stsol_balance_after - stsol_balance_before == payout_stsol.amount
