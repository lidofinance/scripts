"""
Tests for voting 10/05/2022.
"""
from scripts.vote_2022_05_17 import start_vote
from tx_tracing_helpers import *


def test_2022_05_17(
    helpers, accounts, ldo_holder, dao_voting,
    vote_id_from_env, bypass_events_decoding
):

    #
    # START VOTE
    #
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 13, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding:
        return

    evs = group_voting_events(tx)
