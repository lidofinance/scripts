"""
Tests for voting 24/01/2023.
"""
from scripts.vote_2023_01_24 import start_vote
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.payout import (
    Payout,
    validate_token_payout_event,
)
from brownie.network.transaction import TransactionReceipt
from brownie import interface


dao_agent_address = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
lido_dao_token = "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32"

polygon_team_address = "0x9cd7477521B7d7E7F9e2F091D2eA0084e8AaA290"
polygon_team_incentives_amount = 150_000 * 10**18

polygon_team_ldo_payout = Payout(
    token_addr=lido_dao_token,
    from_addr=dao_agent_address,
    to_addr=polygon_team_address,
    amount=polygon_team_incentives_amount,
)

def test_vote(
    helpers,
    accounts,
    ldo_holder,
    dao_voting,
    vote_id_from_env,
    bypass_events_decoding,
    ldo_token,
    dao_agent,
):

    agent_ldo_before = ldo_token.balanceOf(dao_agent.address)
    polygon_team_ldo_before = ldo_token.balanceOf(polygon_team_address)

    # START VOTE
    vote_id: int = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # Validate vote events
    if not bypass_events_decoding:
        assert count_vote_items_by_events(tx, dao_voting) == 1, "Incorrect voting items count"

    # Check LDO payment
    assert (
        agent_ldo_before == ldo_token.balanceOf(dao_agent.address) + polygon_team_ldo_payout.amount
    ), "DAO Agent LDO balance must decrease by the correct amount"
    assert (
        ldo_token.balanceOf(polygon_team_address)
        == polygon_team_ldo_before + polygon_team_ldo_payout.amount
    ), "Destination address LDO balance must increase by the correct amount"

    # Check events if their decoding is available
    if bypass_events_decoding:
        return

    display_voting_events(tx)

    evs = group_voting_events(tx)
    validate_token_payout_event(evs[0], polygon_team_ldo_payout)
