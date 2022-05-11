"""
Tests for voting 10/05/2022.
"""
from scripts.vote_2022_05_10 import start_vote
from tx_tracing_helpers import *
from event_validators.payout import Payout, validate_token_payout_event

ldo_amount: int = 2_000_000 * 10 ** 18

lido_dao_token = '0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'
dao_agent_address = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'  # from
protocol_guild_address = '0xF29Ff96aaEa6C9A1fBa851f74737f3c069d4f1a9'  # to

protocol_guild_payout = Payout(
    token_addr=lido_dao_token,
    from_addr=dao_agent_address,
    to_addr=protocol_guild_address,
    amount=ldo_amount
)


def test_2022_04_26(
    helpers, accounts, ldo_holder, dao_voting,
    ldo_token, dao_token_manager,
    vote_id_from_env, bypass_events_decoding
):
    dao_agent_balance_before = ldo_token.balanceOf(dao_agent_address)
    protocol_guild_balance_before = ldo_token.balanceOf(protocol_guild_address)

    #
    # START VOTE
    #
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    dao_agent_balance_after = ldo_token.balanceOf(dao_agent_address)
    protocol_guild_balance_after = ldo_token.balanceOf(protocol_guild_address)

    assert protocol_guild_balance_after == protocol_guild_balance_before + ldo_amount, "Incorrect LDO amount"
    assert dao_agent_balance_after == dao_agent_balance_before - ldo_amount, "Incorrect LDO amount"

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 1, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding:
        return

    evs = group_voting_events(tx)

    # asserts on vote item 1
    validate_token_payout_event(evs[0], protocol_guild_payout)
