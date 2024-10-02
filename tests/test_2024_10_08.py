"""
Tests for voting 08/10/2024
Add ET setup for Alliance

"""

from scripts.vote_2024_10_08 import start_vote
from brownie import interface, ZERO_ADDRESS, reverts, web3, accounts, convert
from utils.test.tx_tracing_helpers import *
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.config import contracts, LDO_HOLDER_ADDRESS_FOR_TESTS, network_name
from utils.easy_track import create_permissions
from configs.config_mainnet import (
    DAI_TOKEN,
    USDC_TOKEN,
    USDT_TOKEN,
)
from utils.test.easy_track_helpers import create_and_enact_payment_motion, check_add_and_remove_recipient_with_voting
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
    validate_evmscript_factory_removed_event,
)

# STETH_TRANSFER_MAX_DELTA = 2

def test_vote(helpers, accounts, vote_ids_from_env, stranger, ldo_holder, bypass_events_decoding):
    steth = interface.StETH("0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84")
    easy_track = interface.EasyTrack("0xF0211b7660680B49De1A7E9f25C65660F0a13Fea")

    alliance_ops_allowed_recipients_registry = interface.AllowedRecipientRegistry("0x3B525F4c059F246Ca4aa995D21087204F30c9E2F")
    alliance_ops_top_up_evm_script_factory_new = interface.TopUpAllowedRecipients("0xe5656eEe7eeD02bdE009d77C88247BC8271e26Eb")

    alliance_multisig_acc = accounts.at("0x606f77BF3dd6Ed9790D9771C7003f269a385D942", force=True)
    alliance_trusted_caller_acc = accounts.at("0x606f77BF3dd6Ed9790D9771C7003f269a385D942", force=True)

    evm_script_factories_before = easy_track.getEVMScriptFactories()
    assert alliance_ops_top_up_evm_script_factory_new not in evm_script_factories_before

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    evm_script_factories_after = easy_track.getEVMScriptFactories()

    # 1. Add Alliance top up EVM script factory address 0xe5656eEe7eeD02bdE009d77C88247BC8271e26Eb (AllowedRecipientsRegistry address 0x3B525F4c059F246Ca4aa995D21087204F30c9E2F, AllowedTokensRegistry address 0x4AC40c34f8992bb1e5E856A448792158022551ca)

    assert alliance_ops_top_up_evm_script_factory_new in evm_script_factories_after

    dai_transfer_amount = 1_000 * 10**18
    usdc_transfer_amount = 1_000 * 10**6
    usdt_transfer_amount = 1_000 * 10**6

    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=alliance_trusted_caller_acc,
        factory=alliance_ops_top_up_evm_script_factory_new,
        token=interface.Dai(DAI_TOKEN),
        recievers=[alliance_multisig_acc],
        transfer_amounts=[dai_transfer_amount],
        stranger=stranger,
    )

    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=alliance_trusted_caller_acc,
        factory=alliance_ops_top_up_evm_script_factory_new,
        token=interface.Usdc(USDC_TOKEN),
        recievers=[alliance_multisig_acc],
        transfer_amounts=[usdc_transfer_amount],
        stranger=stranger,
    )

    create_and_enact_payment_motion(
        easy_track,
        trusted_caller=alliance_trusted_caller_acc,
        factory=alliance_ops_top_up_evm_script_factory_new,
        token=interface.Usdt(USDT_TOKEN),
        recievers=[alliance_multisig_acc],
        transfer_amounts=[usdt_transfer_amount],
        stranger=stranger,
    )

    with reverts("TOKEN_NOT_ALLOWED"):
        create_and_enact_payment_motion(
            easy_track,
            trusted_caller=alliance_trusted_caller_acc,
            factory=alliance_ops_top_up_evm_script_factory_new,
            token=steth,
            recievers=[alliance_multisig_acc],
            transfer_amounts=[1],
            stranger=stranger,
        )

    check_add_and_remove_recipient_with_voting(
        registry=alliance_ops_allowed_recipients_registry,
        helpers=helpers,
        ldo_holder=ldo_holder,
        dao_voting=contracts.voting,
    )

    # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 1, "Incorrect voting items count"

    metadata = find_metadata_by_vote_id(vote_id)

    assert get_lido_vote_cid_from_str(metadata) == "bafkreibbrlprupitulahcrl57uda4nkzrbfajtrhhsaa3cbx5of4t2huoa"

    display_voting_events(vote_tx)

    evs = group_voting_events(vote_tx)

    validate_evmscript_factory_added_event(
        evs[0],
        EVMScriptFactoryAdded(
            factory_addr=alliance_ops_top_up_evm_script_factory_new,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(alliance_ops_allowed_recipients_registry, "updateSpentAmount")[2:],
        ),
    )
