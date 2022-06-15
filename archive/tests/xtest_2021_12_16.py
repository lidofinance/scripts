"""
Tests for voting 16/12/2021.
"""

from scripts.vote_2021_12_16 import start_vote
from tx_tracing_helpers import *


def test_2021_12_16(
        helpers, accounts, ldo_holder, dao_voting, lido
):
    aragonAgentAddr = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'

    totalSharesBefore = lido.getTotalShares()
    sharesAragonAgentBefore = lido.sharesOf(aragonAgentAddr)

    sharesToBurn = 32145684728326685744

    vote_id, _ = start_vote({'from': ldo_holder}, silent=True)
    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    display_voting_events(tx)

    ### validate vote events
    assert count_vote_items_by_events(tx) == 1, "Incorrect voting items count"

    # check burned shares
    totalSharesAfter = lido.getTotalShares()
    sharesAragonAgentAfter = lido.sharesOf(aragonAgentAddr)

    assert totalSharesBefore - totalSharesAfter == sharesToBurn
    assert sharesAragonAgentBefore - sharesAragonAgentAfter == sharesToBurn
