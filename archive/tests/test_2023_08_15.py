"""
Tests for voting 15/08/2023 — IPFS description upload (test net only)

"""
from archive.scripts.vote_2023_08_15 import start_vote

from utils.config import (
    network_name,
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
)
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.test.tx_tracing_helpers import *

from utils.test.event_validators.easy_track import (
    validate_motions_count_limit_changed_event,
)


def test_vote(
    helpers,
    bypass_events_decoding,
    vote_ids_from_env,
    accounts,
):
    ## parameters
    easy_track = contracts.easy_track

    motions_count_limit_before = easy_track.motionsCountLimit()
    motions_count_limit_expected = motions_count_limit_before
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

    metadata = find_metadata_by_vote_id(vote_id)

    assert get_lido_vote_cid_from_str(metadata) == "bafkreih2p5cofnkwcjt3zivyntfqwghs6zxumgcxmv3uswb4cfl3g3tqui"

    assert easy_track.motionsCountLimit() == motions_count_limit_expected, "Incorrect motions count limit after"
    print(f"motionsCountLimit_expected = {easy_track.motionsCountLimit()}")

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(vote_tx)

    validate_motions_count_limit_changed_event(evs[0], motions_count_limit_expected)
