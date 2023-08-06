"""
Tests for voting 07/07/2023 — IPFS description upload (test net only)

"""
from scripts.vote_2023_07_21 import start_vote

from brownie import chain, accounts, interface, web3
from brownie.network.event import _decode_logs

from utils.config import VOTING

from utils.config import (
    network_name,
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
)
from utils.ipfs import get_lido_vote_cid_from_str
from utils.test.tx_tracing_helpers import *

from utils.test.event_validators.easy_track import (
    validate_motions_count_limit_changed_event,
)

#####
# CONSTANTS
#####

STETH_ERROR_MARGIN = 2


def test_vote(
    helpers,
    bypass_events_decoding,
    vote_ids_from_env,
    accounts,
):
    ## parameters
    easy_track = contracts.easy_track

    motions_count_limit_before = 20
    motions_count_limit_expected = 21
    assert easy_track.motionsCountLimit() == motions_count_limit_before, "Incorrect motions count limit before"
    print(f"motionsCountLimit_before = {easy_track.motionsCountLimit()}")

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 1, "Incorrect voting items count"

    vote = contracts.voting.getVote(vote_id)
    start_vote_signature = web3.keccak(text="StartVote(uint256,address,string)").hex()

    events_after_voting = web3.eth.filter(
        {
            "address": contracts.voting.address,
            "fromBlock": vote[3],
            "toBlock": vote[3] + 1,
            "topics": [start_vote_signature],
        }
    ).get_all_entries()

    events_after_voting = _decode_logs(events_after_voting)
    metadata = str(events_after_voting["StartVote"]["metadata"])

    assert get_lido_vote_cid_from_str(metadata) == "bafkreibyeuz3dihvjy5bk2b2btze7elghglvjngthoef3xdepyoepyrbk4"

    assert easy_track.motionsCountLimit() == motions_count_limit_expected, "Incorrect motions count limit after"
    print(f"motionsCountLimit_expected = {easy_track.motionsCountLimit()}")

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(vote_tx)

    validate_motions_count_limit_changed_event(evs[0], motions_count_limit_expected)
