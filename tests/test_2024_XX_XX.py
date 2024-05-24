"""
Tests for voting XX/XX/2024
"""

from scripts.vote_2024_XX_XX import start_vote
from utils.test.tx_tracing_helpers import *
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.config import contracts, LDO_HOLDER_ADDRESS_FOR_TESTS, network_name
from utils.easy_track import create_permissions

from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
)

# TODO: change to the correct address
CSM_EL_REWARDS_STEALING_PENALTY_FACTORY = "0x..."


def test_vote(helpers, accounts, vote_ids_from_env, stranger, ldo_holder, bypass_events_decoding):
    csm = contracts.cs_module
    easy_track = contracts.easy_track

    evm_script_factories_before = easy_track.getEVMScriptFactories()

    assert CSM_EL_REWARDS_STEALING_PENALTY_FACTORY not in evm_script_factories_before

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

    # TODO: change to the correct CID
    assert get_lido_vote_cid_from_str(metadata) == ""

    display_voting_events(vote_tx)

    # TODO: remove
    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(vote_tx)
    assert len(evs) == 1, "Incorrect voting events count"
    (event, *_) = evs

    validate_evmscript_factory_added_event(
        event,
        EVMScriptFactoryAdded(
            factory_addr=CSM_EL_REWARDS_STEALING_PENALTY_FACTORY,
            permissions=create_permissions(csm, "settleELRewardsStealingPenalty"),
        ),
    )
