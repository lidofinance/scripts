"""
Tests for voting 26/11/2021.
"""
import pytest
from collections import namedtuple

from scripts.vote_2021_11_26 import start_vote

Payout = namedtuple(
    'Payout', ['address', 'amount']
)

dao_agent_address = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'
finance_multisig_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'

isidoros_payout = Payout(
    address=finance_multisig_address,
    amount=3_500 * (10 ** 18)
)

referral_payout = Payout(
    address=finance_multisig_address,
    amount=124_987_5031 * (10 ** 14)
)

def test_2021_11_26(helpers, accounts, ldo_holder, dao_voting, ldo_token):
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

    assert helpers.count_vote_items_by_events() == 2, "Incorrect voting items count"

    helpers.display_voting_events()
    # helpers.display_voting_call_trace() # uncomment for a paranoid mode ON

    evs = helpers.group_voting_events()

    # asserts on item 1
    vote_item1_events = evs[0]
    assert vote_item1_events.count('VaultTransfer') == 1, "Incorrect vault transfers occurred"
    assert vote_item1_events.count('Transfer') == 1, "Incorrect LDO transfers occurred"
    assert vote_item1_events['VaultTransfer']['to'] == isidoros_payout.address
    assert vote_item1_events['VaultTransfer']['amount'] == isidoros_payout.amount

    expected_events_sequence1 = ['LogScriptCall', 'NewTransaction', 'Transfer', 'VaultTransfer']
    assert expected_events_sequence1 == [i.name for i in vote_item1_events]

    # asserts on item 2
    vote_item2_events = evs[1]
    assert vote_item2_events.count('VaultTransfer') == 1, "Incorrect vault transfers occurred"
    assert vote_item2_events.count('Transfer') == 1, "Incorrect LDO transfers occurred"
    assert vote_item2_events['VaultTransfer']['to'] == referral_payout.address
    assert vote_item2_events['VaultTransfer']['amount'] == referral_payout.amount

    expected_events_sequence2 = ['LogScriptCall', 'NewTransaction', 'Transfer', 'VaultTransfer']
    assert expected_events_sequence2 == [i.name for i in vote_item2_events]
