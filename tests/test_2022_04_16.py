"""
Tests for voting 16/04/2021.
"""

from event_validators.unpause import (
    validate_unpause_event
)

from tx_tracing_helpers import *

from scripts.vote_2022_04_16 import start_vote

def test_2021_11_11(ldo_holder, helpers, accounts, dao_voting, deposit_security_module, vote_id_from_env, bypass_events_decoding):
    assert deposit_security_module.isPaused()

    ##
    ## START VOTE
    ##
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='0.5 ether'
    )

    assert not deposit_security_module.isPaused()

    ### validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 1, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding:
        return

    evs = group_voting_events(tx)

    # asserts on vote item 1
    validate_unpause_event(evs[0])
