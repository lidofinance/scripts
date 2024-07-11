"""
Tests for revert Voting Delegation upgrade [in case of emergency]

"""

from brownie import accounts, interface
from scripts.revert_upgrade_voting_delegation_holesky import start_vote
from utils.test.event_validators.vesting_escrow import validate_voting_adapter_upgraded_event
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.config import (
    contracts,
    network_name,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    VOTING,
)
from utils.test.event_validators.aragon import validate_push_to_repo_event, validate_app_update_event
from utils.test.tx_tracing_helpers import *

current_trp_voting_adapter_address = "0x7c94b2A7CF101548B7F28396e789528F4DBD25CE"

current_voting_app = {
    "address": "0xD94437Ba1b653872d6fA7D5bC1873A95e38558b2",
    "content_uri": "0x",
    "id": "0x0abcd104777321a82b010357f20887d61247493d89d2e987ff57bcecbde00e1e",
    "version": (3, 0, 0),
}


downgraded_trp_voting_adapter_address = "0x1dF997832b44b7ED00597f103165920537c980D4"

downgraded_voting_app = {
    "address": "0xcB738a79baeA44C93Ee46c02EF0FA975Bc4d058f",
    "content_uri": "0x",
    "id": "0x0abcd104777321a82b010357f20887d61247493d89d2e987ff57bcecbde00e1e",
    "version": (4, 0, 0),
}


def test_vote(helpers, vote_ids_from_env, bypass_events_decoding):

    # Voting App before
    voting_proxy = interface.AppProxyUpgradeable(contracts.voting.address)
    voting_app_from_repo = contracts.voting_app_repo.getLatest()
    voting_appId = voting_proxy.appId()

    assert voting_app_from_repo[0] == current_voting_app["version"]
    assert voting_app_from_repo[1] == current_voting_app["address"]
    assert voting_proxy.implementation() == current_voting_app["address"]

    # TRP Voting Adapter before
    trp_voting_adapter_address = contracts.trp_escrow_factory.voting_adapter()
    assert trp_voting_adapter_address == current_trp_voting_adapter_address

    trp_voting_adapter = interface.VotingAdapter(trp_voting_adapter_address)
    assert trp_voting_adapter.voting_contract_addr() == VOTING

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # Voting App after
    voting_app_from_repo = contracts.voting_app_repo.getLatest()

    assert voting_app_from_repo[0] == downgraded_voting_app["version"]
    assert voting_app_from_repo[1] == downgraded_voting_app["address"]
    assert voting_proxy.implementation() == downgraded_voting_app["address"]

    # TRP Voting Adapter after
    trp_voting_adapter_address = contracts.trp_escrow_factory.voting_adapter()
    assert trp_voting_adapter_address == downgraded_trp_voting_adapter_address

    # Validating events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 3, "Incorrect voting items count"

    # metadata = find_metadata_by_vote_id(vote_id)
    # assert get_lido_vote_cid_from_str(metadata) == "" TODO: add ipfs cid
    display_voting_events(vote_tx)

    if bypass_events_decoding or network_name() in ("holesky", "holesky-fork"):
        return

    evs = group_voting_events(vote_tx)

    validate_push_to_repo_event(evs[0], downgraded_voting_app["version"])
    validate_app_update_event(evs[1], voting_appId, downgraded_voting_app["address"])
    validate_voting_adapter_upgraded_event(evs[2], downgraded_trp_voting_adapter_address)
