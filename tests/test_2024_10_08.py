"""
Tests for voting 08/10/2024
"""

from scripts.upgrade_2024_10_08 import start_vote, encode_l2_upgrade_call
from brownie import interface, reverts
from brownie.exceptions import VirtualMachineError
from utils.test.event_validators.common import validate_events_chain
from utils.test.tx_tracing_helpers import *
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.config import contracts
from utils.easy_track import create_permissions
from utils.test.easy_track_helpers import create_and_enact_payment_motion, check_add_and_remove_recipient_with_voting
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
)
from utils.test.event_validators.permission import validate_grant_role_event

AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"

LIDO_LOCATOR = "0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb"
LIDO_LOCATOR_IMPL = "0x1D920cc5bACf7eE506a271a5259f2417CaDeCE1d"
LIDO_LOCATOR_IMPL_NEW = "0x39aFE23cE59e8Ef196b81F0DCb165E9aD38b9463"

DEPOSITS_ENABLER_ROLE = "0x4b43b36766bde12c5e9cbbc37d15f8d1f769f08f54720ab370faeb4ce893753a"
L1_EMERGENCY_BRAKES_MULTISIG = "0x73b047fe6337183A454c5217241D780a932777bD"
L2_OPTIMISM_GOVERNANCE_EXECUTOR = "0xefa0db536d2c8089685630fafe88cf7805966fc3"
L1_OPTIMISM_PORTAL_2 = "0xbEb5Fc579115071764c7423A4f12eDde41f106Ed"

L1_OPTIMISM_TOKENS_BRIDGE = "0x76943C0D61395d8F2edF9060e1533529cAe05dE6"
L1_OPTIMISM_TOKENS_BRIDGE_IMPL = "0x29C5c51A031165CE62F964966A6399b81165EFA4"
L1_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW = "0x168Cfea1Ad879d7032B3936eF3b0E90790b6B6D4"

L2_OPTIMISM_TOKENS_BRIDGE = "0x8E01013243a96601a86eb3153F0d9Fa4fbFb6957"
L2_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW = "0x2734602C0CEbbA68662552CacD5553370B283E2E"
L2_OPTIMISM_WSTETH_TOKEN = "0x1F32b1c2345538c0c6f582fCB022739c4A194Ebb"
L2_OPTIMISM_WSTETH_TOKEN_IMPL_NEW = "0xFe57042De76c8D6B1DF0E9E2047329fd3e2B7334"

DAI_TOKEN = "0x6b175474e89094c44da98b954eedeac495271d0f"
USDT_TOKEN = "0xdac17f958d2ee523a2206206994597c13d831ec7"
USDC_TOKEN = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"


def test_vote(helpers, accounts, vote_ids_from_env, stranger, ldo_holder):
    # 1-5. Prepare required state for the voting
    l1_token_bridge = interface.L1LidoTokensBridge(L1_OPTIMISM_TOKENS_BRIDGE)
    if l1_token_bridge.isDepositsEnabled():
        agent = accounts.at(AGENT, force=True)
        l1_token_bridge.disableDeposits({"from": agent})

    # 6. Prepare data before the voting
    steth = interface.StETH("0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84")
    alliance_ops_top_up_evm_script_factory_new = interface.TopUpAllowedRecipients(
        "0xe5656eEe7eeD02bdE009d77C88247BC8271e26Eb"
    )
    alliance_ops_allowed_recipients_registry = interface.AllowedRecipientRegistry(
        "0x3B525F4c059F246Ca4aa995D21087204F30c9E2F"
    )
    alliance_ops_top_up_evm_script_factory_new = interface.TopUpAllowedRecipients(
        "0xe5656eEe7eeD02bdE009d77C88247BC8271e26Eb"
    )
    alliance_multisig_acc = accounts.at("0x606f77BF3dd6Ed9790D9771C7003f269a385D942", force=True)
    alliance_trusted_caller_acc = alliance_multisig_acc

    check_pre_upgrade_state()
    wsteth_bridge_balance_before = contracts.wsteth.balanceOf(L1_OPTIMISM_TOKENS_BRIDGE)

    evm_script_factories_before = contracts.easy_track.getEVMScriptFactories()
    assert alliance_ops_top_up_evm_script_factory_new not in evm_script_factories_before

    dai_token = interface.Dai(DAI_TOKEN)
    dai_balance_before = dai_token.balanceOf(alliance_multisig_acc)
    dai_transfer_amount = 1_000 * 10**18
    usdc_token = interface.Usdc(USDC_TOKEN)
    usdc_balance_before = usdc_token.balanceOf(alliance_multisig_acc)
    usdc_transfer_amount = 1_000 * 10**6
    usdt_token = interface.Usdt(USDT_TOKEN)
    usdt_balance_before = usdt_token.balanceOf(alliance_multisig_acc)
    usdt_transfer_amount = 1_000 * 10**6

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
    assert get_lido_vote_cid_from_str(metadata) == "bafkreiacfthtkgooaeqvfwrlh5rz4betlgvwie7mp6besbhtsev75vyy2y"

    # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 6, "Incorrect voting items count"

    # 1-5 validation
    check_post_upgrade_state(evs)
    assert wsteth_bridge_balance_before == contracts.wsteth.balanceOf(L1_OPTIMISM_TOKENS_BRIDGE)

    # 6 validation
    evm_script_factories_after = contracts.easy_track.getEVMScriptFactories()
    assert alliance_ops_top_up_evm_script_factory_new in evm_script_factories_after

    check_add_and_remove_recipient_with_voting(
        registry=alliance_ops_allowed_recipients_registry,
        helpers=helpers,
        ldo_holder=ldo_holder,
        dao_voting=contracts.voting,
    )

    validate_evmscript_factory_added_event(
        evs[5],
        EVMScriptFactoryAdded(
            factory_addr=alliance_ops_top_up_evm_script_factory_new,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(alliance_ops_allowed_recipients_registry, "updateSpentAmount")[2:],
        ),
    )

    # transfer dai, usdc, usdt to alliance multisig and check that it was successful
    create_and_enact_payment_motion(
        contracts.easy_track,
        trusted_caller=alliance_trusted_caller_acc,
        factory=alliance_ops_top_up_evm_script_factory_new,
        token=dai_token,
        recievers=[alliance_multisig_acc],
        transfer_amounts=[dai_transfer_amount],
        stranger=stranger,
    )

    assert dai_token.balanceOf(alliance_multisig_acc) == dai_balance_before + dai_transfer_amount

    create_and_enact_payment_motion(
        contracts.easy_track,
        trusted_caller=alliance_trusted_caller_acc,
        factory=alliance_ops_top_up_evm_script_factory_new,
        token=usdc_token,
        recievers=[alliance_multisig_acc],
        transfer_amounts=[usdc_transfer_amount],
        stranger=stranger,
    )

    assert usdc_token.balanceOf(alliance_multisig_acc) == usdc_balance_before + usdc_transfer_amount

    create_and_enact_payment_motion(
        contracts.easy_track,
        trusted_caller=alliance_trusted_caller_acc,
        factory=alliance_ops_top_up_evm_script_factory_new,
        token=usdt_token,
        recievers=[alliance_multisig_acc],
        transfer_amounts=[usdt_transfer_amount],
        stranger=stranger,
    )

    assert usdt_token.balanceOf(alliance_multisig_acc) == usdt_balance_before + usdt_transfer_amount

    # check that transfer of steth is not allowed
    with reverts("TOKEN_NOT_ALLOWED"):
        create_and_enact_payment_motion(
            contracts.easy_track,
            trusted_caller=alliance_trusted_caller_acc,
            factory=alliance_ops_top_up_evm_script_factory_new,
            token=steth,
            recievers=[alliance_multisig_acc],
            transfer_amounts=[1],
            stranger=stranger,
        )


def check_pre_upgrade_state():
    l1_token_bridge_proxy = interface.OssifiableProxy(L1_OPTIMISM_TOKENS_BRIDGE)
    l1_token_bridge = interface.L1LidoTokensBridge(L1_OPTIMISM_TOKENS_BRIDGE)
    lido_locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)

    # Disabled deposits is the starting condition for the vote
    assert not l1_token_bridge.isDepositsEnabled()

    # L1 Bridge has old implementation
    assert (
        l1_token_bridge_proxy.proxy__getImplementation() == L1_OPTIMISM_TOKENS_BRIDGE_IMPL
    ), "Old L1ERC20TokenBridge's implementation address is incorrect"

    # L1 Bridge doesn't have version before update
    try:
        l1_token_bridge.getContractVersion()
    except VirtualMachineError:
        pass

    # Upgrade LidoLocator implementation
    assert (
        lido_locator_proxy.proxy__getImplementation() == LIDO_LOCATOR_IMPL
    ), "Old LidoLocator's implementation address is incorrect"

    # Multisig hasn't been assigned as deposit enabler
    assert not l1_token_bridge.hasRole(DEPOSITS_ENABLER_ROLE, L1_EMERGENCY_BRAKES_MULTISIG)


def check_post_upgrade_state(evs: List[EventDict]):
    l1_token_bridge_proxy = interface.OssifiableProxy(L1_OPTIMISM_TOKENS_BRIDGE)
    l1_token_bridge = interface.L1LidoTokensBridge(L1_OPTIMISM_TOKENS_BRIDGE)
    lido_locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)

    # L1 Bridge has new implementation
    assert (
        l1_token_bridge_proxy.proxy__getImplementation() == L1_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW
    ), "New L1ERC20TokenBridge's implementation address is incorrect"

    # update L1 Bridge to 2 version
    assert l1_token_bridge.getContractVersion() == 2

    # check deposits are still paused
    assert not l1_token_bridge.isDepositsEnabled()

    # LidoLocator has new implementation
    assert (
        lido_locator_proxy.proxy__getImplementation() == LIDO_LOCATOR_IMPL_NEW
    ), "New LidoLocator's implementation address is incorrect"

    # Multisig has been assigned as deposit enabler
    assert l1_token_bridge.hasRole(DEPOSITS_ENABLER_ROLE, L1_EMERGENCY_BRAKES_MULTISIG)

    interface.OptimismPortal2(L1_OPTIMISM_PORTAL_2)  # load OptimismPortal2 contract ABI to see events

    validate_contract_upgrade(evs[0], L1_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW)
    validate_contract_finalization(evs[1], 2)
    validate_contract_upgrade(evs[2], LIDO_LOCATOR_IMPL_NEW)
    validate_grant_role_event(evs[3], DEPOSITS_ENABLER_ROLE, L1_EMERGENCY_BRAKES_MULTISIG, AGENT)
    validate_optimism_upgrade_call(
        evs[4],
        L2_OPTIMISM_GOVERNANCE_EXECUTOR,
        AGENT,
        L2_OPTIMISM_TOKENS_BRIDGE,
        L2_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW,
        L2_OPTIMISM_WSTETH_TOKEN,
        L2_OPTIMISM_WSTETH_TOKEN_IMPL_NEW,
    )


def validate_contract_upgrade(events: EventDict, implementation: str):
    _events_chain = ["LogScriptCall", "LogScriptCall", "Upgraded", "ScriptResult"]
    validate_events_chain([e.name for e in events], _events_chain)
    assert events.count("Upgraded") == 1
    assert events["Upgraded"]["implementation"] == implementation, "Wrong implementation"


def validate_contract_finalization(events: EventDict, version: int):
    _events_chain = ["LogScriptCall", "LogScriptCall", "ContractVersionSet", "ScriptResult"]
    validate_events_chain([e.name for e in events], _events_chain)
    assert events.count("ContractVersionSet") == 1
    assert events["ContractVersionSet"]["version"] == version


def validate_optimism_upgrade_call(
    events: EventDict,
    target: str,
    sender: str,
    l2_bridge_proxy: str,
    l2_bridge_impl: str,
    l2_wst_proxy: str,
    l2_wst_impl: str,
):
    _events_chain = [
        "LogScriptCall",
        "LogScriptCall",
        "TransactionDeposited",
        "SentMessage",
        "SentMessageExtension1",
        "ScriptResult",
    ]
    validate_events_chain([e.name for e in events], _events_chain)
    assert events.count("SentMessage") == 1
    # Check bytecode that was sent to messenger to update L2 bridge and wstETH token
    encoded_l2_upgrade_call = encode_l2_upgrade_call(l2_bridge_proxy, l2_bridge_impl, l2_wst_proxy, l2_wst_impl)
    assert events["SentMessage"]["message"] == encoded_l2_upgrade_call
    assert events["SentMessage"]["target"] == target
    assert events["SentMessage"]["sender"] == sender
