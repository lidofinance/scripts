"""
Tests for voting 08/10/2024
Add ET setup for Alliance

"""

from scripts.vote_limits import start_vote
from brownie import interface, ZERO_ADDRESS, reverts, web3, accounts, convert
from utils.test.tx_tracing_helpers import *
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.config import contracts, LDO_HOLDER_ADDRESS_FOR_TESTS, network_name
from utils.easy_track import create_permissions
from utils.test.easy_track_helpers import create_and_enact_payment_motion, check_add_and_remove_recipient_with_voting
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
    validate_evmscript_factory_removed_event,
)
_
# STETH_TRANSFER_MAX_DELTA = 2

def test_vote(helpers, accounts, vote_ids_from_env, stranger, ldo_holder, bypass_events_decoding):
    steth = "0x3F1c547b21f65e10480dE3ad8E19fAAC46C95034"
    easy_track = "0x1763b9ED3586B08AE796c7787811a2E1bc16163a"

    alliance_ops_allowed_recipients_registry = interface.AllowedRecipientRegistry("0xe1ba8dee84a4df8e99e495419365d979cdb19991")
    alliance_ops_top_up_evm_script_factory = interface.TopUpAllowedRecipients("0x343fa5f0c79277e2d27e440f40420d619f962a23")

    alliance_multisig_acc = accounts.at("0x96d2Ff1C4D30f592B91fd731E218247689a76915", force=True)
    alliance_trusted_caller_acc = accounts.at("0x96d2Ff1C4D30f592B91fd731E218247689a76915", force=True)

    budget_limit_before = interface.AllowedRecipientRegistry(alliance_ops_allowed_recipients_registry).getLimitParameters()
    print('Limit before: ', budget_limit_before)
    '''
    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # 1. Change limits



    # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 1, "Incorrect voting items count"

    metadata = find_metadata_by_vote_id(vote_id)

    assert get_lido_vote_cid_from_str(metadata) == "bafkreibbrlprupitulahcrl57uda4nkzrbfajtrhhsaa3cbx5of4t2huoa" # todo: поменять адрес после тестовой публикации голоосвания на форке

    display_voting_events(vote_tx)

    evs = group_voting_events(vote_tx)

    validate_evmscript_factory_added_event(
        evs[0],
        EVMScriptFactoryAdded(
            factory_addr=alliance_ops_top_up_evm_script_factory,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(alliance_ops_allowed_recipients_registry, "updateSpentAmount")[2:],
        ),
    )
    '''
