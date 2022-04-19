"""
Tests for voting 19/04/2022.
"""

from event_validators.payout import (
    Payout,
    validate_token_payout_event
)

from scripts.vote_2022_04_19 import start_vote
from tx_tracing_helpers import *

rcc_multisig_address = '0xDE06d17Db9295Fa8c4082D4f73Ff81592A3aC437'
dao_agent_address = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'
steth_address = '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'


def steth_balance_checker(lhs_value: int, rhs_value: int):
    assert (lhs_value + 9) // 10 == (rhs_value + 9) // 10


fund_payout = Payout(
    token_addr=steth_address,
    from_addr=dao_agent_address,
    to_addr=rcc_multisig_address,
    amount=1337 * (10 ** 18) # ? TODO
)


def test_2022_04_19(
    helpers, accounts, ldo_holder, dao_voting, lido,
    vote_id_from_env, bypass_events_decoding
):
    rcc_multisig_balance_before = lido.balanceOf(rcc_multisig_address)
    dao_balance_before = lido.balanceOf(dao_agent_address)

    #
    # START VOTE
    #
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='0.5 ether'
    )

    rcc_multisig_balance_after = lido.balanceOf(rcc_multisig_address)
    dao_balance_after = lido.balanceOf(dao_agent_address)

    steth_balance_checker(rcc_multisig_balance_after - rcc_multisig_balance_before, fund_payout.amount)
    steth_balance_checker(dao_balance_before - dao_balance_after, fund_payout.amount)

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 1, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding:
        return

    evs = group_voting_events(tx)

    # asserts on vote item 1
    validate_token_payout_event(evs[0], fund_payout)
