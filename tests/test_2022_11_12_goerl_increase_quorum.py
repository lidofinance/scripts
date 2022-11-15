"""
Tests for voting 12/11/2022.

!!! Görli network only

"""

from scripts.vote_2022_11_12_goerli_increase_quorum import start_vote
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.oracle import validate_oracle_member_added, validate_oracle_quorum_changed
from utils.config import network_name
from brownie.network.transaction import TransactionReceipt
from brownie import interface
import time

pre_vote_quorum: int = 1
post_vote_quorum: int = 2


def test_vote_2022_11_12(helpers, accounts, ldo_holder, dao_voting, vote_id_from_env, bypass_events_decoding, oracle):
    old_quorum: int = oracle.getQuorum()

    assert old_quorum == pre_vote_quorum, "wrong old quorum"

    # START VOTE
    vote_id: int = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )
    tx.wait(1)
    time.sleep(1)

    # Validate vote events
    if not bypass_events_decoding:
        assert count_vote_items_by_events(tx, dao_voting) == 1, "Incorrect voting items count"

    new_quorum: int = oracle.getQuorum()

    assert new_quorum == post_vote_quorum, "wrong new quorum"

    # Check events if their decoding is available
    if bypass_events_decoding:
        return

    display_voting_events(tx)

    if network_name() in ("goerli", "goerli-fork"):
        return  # can't validate the events precisely due to some onverified contracts on Goerli

    evs = group_voting_events(tx)
    validate_oracle_quorum_changed(evs[0], post_vote_quorum)
