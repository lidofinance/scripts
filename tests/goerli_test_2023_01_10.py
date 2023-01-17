"""
Tests for voting 10/01/2022.
!!! Goerli only

"""

from scripts.goerli_vote_2023_01_10 import start_vote
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.relay_allowed_list import validate_relay_allowed_list_manager_set
from utils.config import network_name
from brownie.network.transaction import TransactionReceipt
from brownie import interface, ZERO_ADDRESS

relay_allowed_list_committee: str = "0xf1A6BD3193F93331C38828a3EBeE2fCa374ABACe"
relay_allowed_list_prev_manager: str = "0xa5F1d7D49F581136Cf6e58B32cBE9a2039C48bA1"

def test_vote_2023_01_10(
    helpers, accounts, ldo_holder, dao_voting, vote_id_from_env, bypass_events_decoding, relay_allowed_list
):
    assert relay_allowed_list.get_manager() == relay_allowed_list_prev_manager, "wrong manager"

    # START VOTE
    vote_id: int = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # Validate vote events
    if not bypass_events_decoding:
        assert count_vote_items_by_events(tx, dao_voting) == 1, "Incorrect voting items count"

    assert relay_allowed_list.get_manager() == relay_allowed_list_committee, "wrong manager"

    # Check events if their decoding is available
    if bypass_events_decoding:
        return

    display_voting_events(tx)

    if network_name() in ("goerli", "goerli-fork"):
        return  # can't validate the events precisely due to some onverified contracts on Goerli

    evs = group_voting_events(tx)
    validate_relay_allowed_list_manager_set(evs[0], relay_allowed_list_committee)
