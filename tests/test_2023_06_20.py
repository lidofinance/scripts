"""
Tests for voting 20/06/2023.

"""
from scripts.vote_2023_06_20 import start_vote

from brownie import chain, accounts, web3
from brownie.network.transaction import TransactionReceipt
from eth_abi.abi import encode_single


from utils.config import (
    network_name,
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
)
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.node_operators_registry import (
    validate_target_validators_count_changed_event,
    TargetValidatorsCountChanged,
)

from utils.test.event_validators.payout import Payout, validate_token_payout_event
from utils.test.event_validators.easy_track import (
    validate_motions_count_limit_changed_event,
)
from utils.test.event_validators.permission import validate_grant_role_event, validate_revoke_role_event
from utils.test.helpers import almostEqWithDiff

#####
# CONSTANTS
#####

STETH_ERROR_MARGIN_WEI = 2

def test_vote(
    helpers,
    bypass_events_decoding,
    vote_ids_from_env,
    accounts,
    interface,
):

    ## parameters

    ## checks before the vote
    # I.
    # II.
    # III.
    # IV.
    # V.
    # VI.
    # VII.
    # VIII.


    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 29, "Incorrect voting items count"

    display_voting_events(vote_tx)

    ## checks after the vote
    # I.
    # II.
    # III.
    # IV.
    # V.
    # VI.
    # VII.
    # VIII.

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(vote_tx)

    ## validate events
