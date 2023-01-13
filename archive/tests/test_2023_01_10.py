"""
Tests for voting 10/01/2022.
"""

from scripts.vote_2023_01_10 import start_vote
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.oracle import validate_oracle_member_added, validate_oracle_quorum_changed
from utils.test.event_validators.relay_allowed_list import validate_relay_allowed_list_manager_set
from utils.config import network_name
from brownie.network.transaction import TransactionReceipt
from brownie import interface, ZERO_ADDRESS

pre_vote_oracle_committee: int = 5
post_vote_oracle_committee: int = pre_vote_oracle_committee + 4

post_vote_oracle_committee_member_addrs: List[str] = [
    "0xec4bfbaf681eb505b94e4a7849877dc6c600ca3a",
    "0x61c91ECd902EB56e314bB2D5c5C07785444Ea1c8",
    "0x1ca0fec59b86f549e1f1184d97cb47794c8af58d",
    "0xA7410857ABbf75043d61ea54e07D57A6EB6EF186",
]

pre_vote_quorum: int = 3
post_vote_quorum: int = 5

relay_allowed_list_committee: str = "0x98be4a407Bff0c125e25fBE9Eb1165504349c37d"

def test_vote_2023_01_10(
    helpers, accounts, ldo_holder, dao_voting, vote_id_from_env, bypass_events_decoding, oracle, relay_allowed_list
):
    old_quorum: int = oracle.getQuorum()
    old_oracle_members: List[str] = oracle.getOracleMembers()

    assert old_quorum == pre_vote_quorum, "wrong old quorum"
    assert len(old_oracle_members) == pre_vote_oracle_committee, "wrong old committee size"

    for m in post_vote_oracle_committee_member_addrs:
        assert not m in old_oracle_members, "already in committee"

    assert relay_allowed_list.get_manager() == ZERO_ADDRESS, "wrong manager"

    # START VOTE
    vote_id: int = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # Validate vote events
    if not bypass_events_decoding:
        assert count_vote_items_by_events(tx, dao_voting) == 6, "Incorrect voting items count"

    new_quorum: int = oracle.getQuorum()
    new_oracle_members: List[str] = oracle.getOracleMembers()

    assert new_quorum == post_vote_quorum, "wrong new quorum"
    assert len(new_oracle_members) == post_vote_oracle_committee, "wrong new committee size"

    for old_m in old_oracle_members:
        assert old_m in new_oracle_members, "old member not in the committee"

    for m in post_vote_oracle_committee_member_addrs:
        assert m in new_oracle_members, "must be in committee"

    assert relay_allowed_list.get_manager() == relay_allowed_list_committee, "wrong manager"

    # Check events if their decoding is available
    if bypass_events_decoding:
        return

    display_voting_events(tx)

    if network_name() in ("goerli", "goerli-fork"):
        return  # can't validate the events precisely due to some onverified contracts on Goerli

    evs = group_voting_events(tx)
    validate_oracle_member_added(evs[0], post_vote_oracle_committee_member_addrs[0])
    validate_oracle_member_added(evs[1], post_vote_oracle_committee_member_addrs[1])
    validate_oracle_member_added(evs[2], post_vote_oracle_committee_member_addrs[2])
    validate_oracle_member_added(evs[3], post_vote_oracle_committee_member_addrs[3])
    validate_oracle_quorum_changed(evs[4], post_vote_quorum)
    validate_relay_allowed_list_manager_set(evs[5], relay_allowed_list_committee)
