"""
Tests for voting 25/04/2023.

"""
from scripts.vote_2023_05_23 import start_vote

from brownie.network.transaction import TransactionReceipt

from utils.config import (
    network_name,
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
)
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.node_operators_registry import (
    validate_node_operator_name_set_event,
    validate_node_operator_reward_address_set_event,
    NodeOperatorNameSetItem,
    NodeOperatorRewardAddressSetItem,
)
from utils.test.event_validators.easy_track import (
    validate_motions_count_limit_changed_event
)
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes

def test_vote(
    helpers,
    bypass_events_decoding,
    vote_ids_from_env,
    accounts,
):


    ## parameters
    # 1.
    easy_track = contracts.easy_track
    motionsCountLimit_before = 12
    motionsCountLimit_after = 20

    # 2.

    ## check vote items parameters before voting

    # 1.
    easy_track.motionsCountLimit() == motionsCountLimit_before, "Incorrect motions count limit before"

    # 2.


    factories_list_before_voting = easy_track.getEVMScriptFactories()
    assert len(factories_list_before_voting) == 16

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # 1. check Easy Track motions count limit after
    easy_track.motionsCountLimit() == motionsCountLimit_after, "Incorrect motions count limit after"

    # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 1, "Incorrect voting items count"

    display_voting_events(vote_tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(vote_tx)


    validate_motions_count_limit_changed_event(
        evs[0],
        motionsCountLimit_after
    )
