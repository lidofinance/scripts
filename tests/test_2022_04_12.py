"""
Tests for voting 12/04/2022.
"""

from event_validators.payout import (
    Payout,
    validate_token_payout_event
)

from scripts.vote_2022_04_12 import start_vote
from tx_tracing_helpers import *

finance_multisig_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'
depositor_multisig_address = '0x5181d5D56Af4f823b96FE05f062D7a09761a5a53'
dao_agent_address = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'
steth_address = '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'

def steth_balance_checker(lhs_value: int, rhs_value: int):
    assert (lhs_value + 9) // 10 == (rhs_value + 9) // 10

refund_payout = Payout(
    token_addr=steth_address,
    from_addr=dao_agent_address,
    to_addr=finance_multisig_address,
    amount=254_684_812_629_886_507_249
)

fund_payout = Payout(
    token_addr=steth_address,
    from_addr=dao_agent_address,
    to_addr=depositor_multisig_address,
    amount=130 * (10 ** 18)
)

def test_2022_04_12(
    helpers, accounts, ldo_holder, dao_voting, lido,
    vote_id_from_env, bypass_events_decoding
):
    finance_multisig_balance_before = lido.balanceOf(finance_multisig_address)
    depositor_multisig_balance_before = lido.balanceOf(depositor_multisig_address)
    dao_balance_before = lido.balanceOf(dao_agent_address)

    ##
    ## START VOTE
    ##
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='0.5 ether'
    )

    finance_multisig_balance_after = lido.balanceOf(finance_multisig_address)
    depositor_multisig_balance_after = lido.balanceOf(depositor_multisig_address)
    dao_balance_after = lido.balanceOf(dao_agent_address)

    steth_balance_checker(finance_multisig_balance_after - finance_multisig_balance_before, refund_payout.amount)
    steth_balance_checker(depositor_multisig_balance_after - depositor_multisig_balance_before, fund_payout.amount)
    steth_balance_checker(dao_balance_before - dao_balance_after, refund_payout.amount + fund_payout.amount)

    ### validate vote events
    assert count_vote_items_by_events(tx) == 2, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding:
        return

    evs = group_voting_events(tx)

    # asserts on vote item 1
    validate_token_payout_event(evs[0], refund_payout)

    # asserts on vote item 2
    validate_token_payout_event(evs[1], fund_payout)
