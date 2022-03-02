"""
Tests for voting 03/03/2022.
"""

from event_validators.payout import Payout, validate_payout_event

from scripts.vote_2022_03_03 import start_vote
from tx_tracing_helpers import *


dao_agent_address = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'
finance_multisig_address = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'
lido_dao_token = '0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'

referral_payout = Payout(
    token_addr=lido_dao_token,
    from_addr=dao_agent_address,
    to_addr=finance_multisig_address,
    amount=412_082 * (10 ** 18)
)


def test_2022_03_03(
        helpers, accounts, ldo_holder, dao_voting, ldo_token,
        vote_id_from_env, bypass_events_decoding
):
    multisig_balance_before = ldo_token.balanceOf(finance_multisig_address)
    dao_balance_before = ldo_token.balanceOf(dao_agent_address)

    ##
    ## START VOTE
    ##
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='0.37 ether'
    )

    multisig_balance_after = ldo_token.balanceOf(finance_multisig_address)
    dao_balance_after = ldo_token.balanceOf(dao_agent_address)

    assert multisig_balance_after - multisig_balance_before == referral_payout.amount
    assert dao_balance_before - dao_balance_after == referral_payout.amount

    ### validate vote events
    assert count_vote_items_by_events(tx) == 1, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding:
        return

    evs = group_voting_events(tx)

    # asserts on vote item 1
    validate_payout_event(evs[0], referral_payout)
