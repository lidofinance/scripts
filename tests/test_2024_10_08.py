"""
Tests for voting 08/10/2024
"""
from scripts.upgrade_2024_10_08 import start_vote, encode_l2_upgrade_call
from brownie import interface, ZERO_ADDRESS, reverts, web3, accounts, convert
from brownie.exceptions import VirtualMachineError
from utils.test.tx_tracing_helpers import *
from utils.config import (
    contracts,
    AGENT,
)
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

LIDO_LOCATOR="0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb"
LIDO_LOCATOR_IMPL="0x1D920cc5bACf7eE506a271a5259f2417CaDeCE1d"
LIDO_LOCATOR_IMPL_NEW="0x39aFE23cE59e8Ef196b81F0DCb165E9aD38b9463"

DEPOSITS_ENABLER_ROLE="0x4b43b36766bde12c5e9cbbc37d15f8d1f769f08f54720ab370faeb4ce893753a"
L1_EMERGENCY_BRAKES_MULTISIG="0x73b047fe6337183A454c5217241D780a932777bD"

L1_OPTIMISM_TOKENS_BRIDGE="0x76943C0D61395d8F2edF9060e1533529cAe05dE6"
L1_OPTIMISM_TOKENS_BRIDGE_IMPL="0x29C5c51A031165CE62F964966A6399b81165EFA4"
L1_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW="0x168Cfea1Ad879d7032B3936eF3b0E90790b6B6D4"

L2_OPTIMISM_TOKENS_BRIDGE="0x8E01013243a96601a86eb3153F0d9Fa4fbFb6957"
L2_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW="0x2734602C0CEbbA68662552CacD5553370B283E2E"
L2_OPTIMISM_WSTETH_TOKEN="0x1F32b1c2345538c0c6f582fCB022739c4A194Ebb"
L2_OPTIMISM_WSTETH_TOKEN_IMPL_NEW="0xFe57042De76c8D6B1DF0E9E2047329fd3e2B7334"

def test_vote(helpers, accounts, vote_ids_from_env, stranger, ldo_holder, bypass_events_decoding):

    l1_token_bridge = interface.L1LidoTokensBridge(L1_OPTIMISM_TOKENS_BRIDGE)

    # 1-5. Prepare required state for the voting
    if l1_token_bridge.isDepositsEnabled():
        agent = accounts.at(AGENT, force=True)
        l1_token_bridge.disableDeposits({"from": agent})

    check_pre_upgrade_state()
    wsteth_bridge_balance_before = contracts.wsteth.balanceOf(L1_OPTIMISM_TOKENS_BRIDGE)

    # 6. Prepare data before the voting
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
        vote_id, _ = start_vote({"from": ldo_holder}, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 6, "Incorrect voting items count"

    # 1-5 validation
    check_post_upgrade_state(vote_tx)
    assert wsteth_bridge_balance_before == contracts.wsteth.balanceOf(L1_OPTIMISM_TOKENS_BRIDGE)

    # 6 validation
    evm_script_factories_after = easy_track.getEVMScriptFactories()
    assert alliance_ops_top_up_evm_script_factory_new in evm_script_factories_after

    dai_transfer_amount = 1_000 * 10 ** 18
    usdc_transfer_amount = 1_000 * 10 ** 6
    usdt_transfer_amount = 1_000 * 10 ** 6

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

    metadata = find_metadata_by_vote_id(vote_id)
    assert get_lido_vote_cid_from_str(metadata) == "bafkreibbrlprupitulahcrl57uda4nkzrbfajtrhhsaa3cbx5of4t2huoa"

    display_voting_events(vote_tx)
    evs = group_voting_events(vote_tx)

    validate_evmscript_factory_added_event(
        evs[5],
        EVMScriptFactoryAdded(
            factory_addr=alliance_ops_top_up_evm_script_factory_new,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
                        + create_permissions(alliance_ops_allowed_recipients_registry, "updateSpentAmount")[2:],
        ),
    )

def check_pre_upgrade_state():
    l1_token_bridge_proxy = interface.OssifiableProxy(L1_OPTIMISM_TOKENS_BRIDGE)
    l1_token_bridge = interface.L1LidoTokensBridge(L1_OPTIMISM_TOKENS_BRIDGE)
    lido_locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)

    # Disabled deposits is the starting condition for the vote
    assert not l1_token_bridge.isDepositsEnabled()

    # L1 Bridge has old implementation
    assert l1_token_bridge_proxy.proxy__getImplementation() == L1_OPTIMISM_TOKENS_BRIDGE_IMPL, "Old address is incorrect"

    # L1 Bridge doesn't have version before update
    try:
        l1_token_bridge.getContractVersion()
    except VirtualMachineError:
        pass

    # Upgrade LidoLocator implementation
    assert lido_locator_proxy.proxy__getImplementation() == LIDO_LOCATOR_IMPL, "Old address is incorrect"

    # Multisig hasn't been assigned as deposit enabler
    assert not l1_token_bridge.hasRole(DEPOSITS_ENABLER_ROLE, L1_EMERGENCY_BRAKES_MULTISIG)

def check_post_upgrade_state(vote_tx):
    l1_token_bridge_proxy = interface.OssifiableProxy(L1_OPTIMISM_TOKENS_BRIDGE)
    l1_token_bridge = interface.L1LidoTokensBridge(L1_OPTIMISM_TOKENS_BRIDGE)
    lido_locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)

    # L1 Bridge has new implementation
    assert (
        l1_token_bridge_proxy.proxy__getImplementation() == L1_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW
    ), "New address is incorrect"

    # update L1 Bridge to 2 version
    assert l1_token_bridge.getContractVersion() == 2

    # check deposits are still paused
    assert not l1_token_bridge.isDepositsEnabled()

    # LidoLocator has new implementation
    assert lido_locator_proxy.proxy__getImplementation() == LIDO_LOCATOR_IMPL_NEW, "New LidoLocator address is incorrect"

    # Multisig has been assigned as deposit enabler
    assert l1_token_bridge.hasRole(DEPOSITS_ENABLER_ROLE, L1_EMERGENCY_BRAKES_MULTISIG)

    # Check bytecode that was sent to messenger to update L2 bridge and wstETH token
    sentMessage = vote_tx.events["SentMessage"]["message"]
    encoded_l2_upgrade_call = encode_l2_upgrade_call(
        L2_OPTIMISM_TOKENS_BRIDGE,
        L2_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW,
        L2_OPTIMISM_WSTETH_TOKEN,
        L2_OPTIMISM_WSTETH_TOKEN_IMPL_NEW,
    )
    assert sentMessage == encoded_l2_upgrade_call
