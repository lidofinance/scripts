"""
Tests for voting 23/12/2021.
"""

from scripts.vote_2021_12_23 import start_vote
from brownie import interface
from tx_tracing_helpers import *

from utils.config import (
    lido_dao_lido_repo,
    lido_dao_node_operators_registry_repo,
)

from event_validators.payout import Payout, validate_payout_event

dao_agent_address = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'
finance_multisig_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'
lido_dao_token = '0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'

isidoros_payout = Payout(
    token_addr=lido_dao_token,
    from_addr=dao_agent_address,
    to_addr=finance_multisig_address,
    amount=4_200 * (10 ** 18)
)

jacob_payout = Payout(
    token_addr=lido_dao_token,
    from_addr=dao_agent_address,
    to_addr=finance_multisig_address,
    amount=6_900 * (10 ** 18)
)

referral_payout = Payout(
    token_addr=lido_dao_token,
    from_addr=dao_agent_address,
    to_addr=finance_multisig_address,
    amount=235_290 * (10 ** 18)
)

def test_2021_12_16(
    helpers, accounts, ldo_holder, dao_voting, ldo_token
):
    multisig_balance_before = ldo_token.balanceOf(finance_multisig_address)
    dao_balance_before = ldo_token.balanceOf(dao_agent_address)

    ##
    ## START VOTE
    ##
    vote_id, _ = start_vote({ 'from': ldo_holder }, silent=True)
    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='5 ether'
    )

    multisig_balance_after = ldo_token.balanceOf(finance_multisig_address)
    dao_balance_after = ldo_token.balanceOf(dao_agent_address)

    assert multisig_balance_after - multisig_balance_before == isidoros_payout.amount + jacob_payout.amount + referral_payout.amount 
    assert dao_balance_before - dao_balance_after == isidoros_payout.amount +jacob_payout.amount + referral_payout.amount

    ### validate vote events
    assert count_vote_items_by_events(tx) == 3, "Incorrect voting items count"

    display_voting_events(tx)

    evs = group_voting_events(tx)

    # asserts on vote item 1
    validate_payout_event(evs[0], isidoros_payout)

    # asserts on vote item 2
    validate_payout_event(evs[1], jacob_payout)

    # asserts on vote item 3
    validate_payout_event(evs[2], referral_payout)