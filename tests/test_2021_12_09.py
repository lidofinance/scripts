"""
Tests for voting 09/12/2021.
"""
import pytest
from collections import namedtuple

from scripts.vote_2021_12_09 import start_vote
from tx_tracing_helpers import *

from event_validators.payout import Payout, validate_payout_event

dao_agent_address = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'
lido_dao_token = '0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'

curve_LP_reward_manager_address = '0x753D5167C31fBEB5b49624314d74A957Eb271709'
balancer_LP_reward_manager_address = '0x1dD909cDdF3dbe61aC08112dC0Fdf2Ab949f79D8'
sushi_LP_reward_manager_address = '0xE5576eB1dD4aA524D67Cf9a32C8742540252b6F4'
finance_multisig_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'

curve_LP_payout = Payout(
    token_addr=lido_dao_token,
    from_addr=dao_agent_address,
    to_addr=curve_LP_reward_manager_address,
    amount=3_550_000 * (10 ** 18)
)

balancer_LP_payout = Payout(
    token_addr=lido_dao_token,
    from_addr=dao_agent_address,
    to_addr=balancer_LP_reward_manager_address,
    amount=300_000 * (10 ** 18)
)

sushi_LP_payout = Payout(
    token_addr=lido_dao_token,
    from_addr=dao_agent_address,
    to_addr=sushi_LP_reward_manager_address,
    amount=50_000 * (10 ** 18)
)

referral_10th_payout = Payout(
    token_addr=lido_dao_token,
    from_addr=dao_agent_address,
    to_addr=finance_multisig_address,
    amount=140_414 * (10 ** 18)
)

def test_2021_12_09(helpers, accounts, ldo_holder, dao_voting, ldo_token, vote_id_from_env, bypass_events_decoding):
    curve_LP_balance_before = ldo_token.balanceOf(curve_LP_reward_manager_address)
    balancer_LP_balance_before = ldo_token.balanceOf(balancer_LP_reward_manager_address)
    sushi_LP_balance_before = ldo_token.balanceOf(sushi_LP_reward_manager_address)
    finance_multisig_balance_before = ldo_token.balanceOf(finance_multisig_address)

    dao_balance_before = ldo_token.balanceOf(dao_agent_address)

    vote_id = vote_id_from_env or start_vote({'from': ldo_holder }, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    dao_balance_after = ldo_token.balanceOf(dao_agent_address)

    curve_LP_balance_after = ldo_token.balanceOf(curve_LP_reward_manager_address)
    balancer_LP_balance_after = ldo_token.balanceOf(balancer_LP_reward_manager_address)
    sushi_LP_balance_after = ldo_token.balanceOf(sushi_LP_reward_manager_address)
    finance_multisig_balance_after = ldo_token.balanceOf(finance_multisig_address)

    assert curve_LP_balance_after - curve_LP_balance_before == curve_LP_payout.amount
    assert balancer_LP_balance_after - balancer_LP_balance_before == balancer_LP_payout.amount
    assert sushi_LP_balance_after - sushi_LP_balance_before == sushi_LP_payout.amount
    assert finance_multisig_balance_after - finance_multisig_balance_before == referral_10th_payout.amount

    assert (dao_balance_before - dao_balance_after ==
        curve_LP_payout.amount + balancer_LP_payout.amount + sushi_LP_payout.amount + referral_10th_payout.amount)

    ### validate vote events

    assert count_vote_items_by_events(tx) == 4, "Incorrect voting items count"

    display_voting_events(tx)
    # display_voting_call_trace(tx) # uncomment for a paranoid mode ON

    if bypass_events_decoding:
        return

    evs = group_voting_events(tx)
    # asserts on vote item 1
    validate_payout_event(evs[0], curve_LP_payout)
    # asserts on vote item 2
    validate_payout_event(evs[1], balancer_LP_payout)
    # asserts on vote item 3
    validate_payout_event(evs[2], sushi_LP_payout)
    # asserts on vote item 4
    validate_payout_event(evs[3], referral_10th_payout)