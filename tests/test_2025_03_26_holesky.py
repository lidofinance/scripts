"""
Tests for voting 27/03/2025
"""

import eth_abi
from scripts.vote_2025_03_26_holesky import start_vote
from brownie import interface, reverts, web3
from brownie.exceptions import VirtualMachineError
from utils.test.tx_tracing_helpers import *
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.config import contracts
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_removed_event,
    EVMScriptFactoryRemoved,
)

def test_vote(helpers, accounts, vote_ids_from_env, stranger, ldo_holder):

    steth = interface.StETH("0x3F1c547b21f65e10480dE3ad8E19fAAC46C95034")

    ecosystem_ops_allowed_recipient_registry = interface.AllowedRecipientRegistry("0x193d0bA65cf3a2726e12c5568c068D1B3ea51740")
    ecosystem_ops_top_up_allowed_recipients = interface.TopUpAllowedRecipients("0x4F2dA002a7bD5F7C63B62d4C9e4b762c689Dd8Ac")
    ecosystem_multisig_acc = accounts.at("0x96d2Ff1C4D30f592B91fd731E218247689a76915", force=True)
    ecosystem_trusted_caller_acc = ecosystem_multisig_acc

    labs_ops_allowed_recipient_registry = interface.AllowedRecipientRegistry("0x02CD05c1cBa16113680648a8B3496A5aE312a935")
    labs_ops_top_up_allowed_recipients = interface.TopUpAllowedRecipients("0xef0Df040B76252cC7fa31a5fc2f36e85c1C8c4f9")
    labs_multisig_acc = accounts.at("0x96d2Ff1C4D30f592B91fd731E218247689a76915", force=True)
    labs_trusted_caller_acc = labs_multisig_acc

    evm_script_factories_before = contracts.easy_track.getEVMScriptFactories()
    assert str(ecosystem_ops_top_up_allowed_recipients) in evm_script_factories_before
    assert str(labs_ops_top_up_allowed_recipients) in evm_script_factories_before

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        vote_id, _ = start_vote({"from": ldo_holder}, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")
    display_voting_events(vote_tx)
    evs = group_voting_events(vote_tx)

    # validate vote metadata
    metadata = find_metadata_by_vote_id(vote_id)
    assert get_lido_vote_cid_from_str(metadata) == "bafkreiconxbneisesoq4qa632lvei2u54h5rpbkdxhqeqtoh5k5xnjsxki"

    # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 2, "Incorrect voting items count"

    # items validation
    evm_script_factories_after = contracts.easy_track.getEVMScriptFactories()
    assert ecosystem_ops_top_up_allowed_recipients not in evm_script_factories_after
    assert labs_ops_top_up_allowed_recipients not in evm_script_factories_after

    validate_evmscript_factory_removed_event(
        evs[0],
        EVMScriptFactoryRemoved(
            factory_addr=ecosystem_ops_top_up_allowed_recipients,
        ),
    )

    validate_evmscript_factory_removed_event(
        evs[1],
        EVMScriptFactoryRemoved(
            factory_addr=labs_ops_top_up_allowed_recipients,
        ),
    )

