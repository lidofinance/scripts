"""
Tests for voting 08/10/2024
"""
from scripts.upgrade_2024_10_08 import start_vote, encode_l2_upgrade_call
from brownie import interface
from brownie.exceptions import VirtualMachineError
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.common import validate_events_chain
from utils.config import (
    contracts,
    AGENT,
)

LIDO_LOCATOR = "0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb"
LIDO_LOCATOR_IMPL = "0x1D920cc5bACf7eE506a271a5259f2417CaDeCE1d"
LIDO_LOCATOR_IMPL_NEW = "0x39aFE23cE59e8Ef196b81F0DCb165E9aD38b9463"

DEPOSITS_ENABLER_ROLE = "0x4b43b36766bde12c5e9cbbc37d15f8d1f769f08f54720ab370faeb4ce893753a"
L1_EMERGENCY_BRAKES_MULTISIG = "0x73b047fe6337183A454c5217241D780a932777bD"
L2_OPTIMISM_GOVERNANCE_EXECUTOR = "0xefa0db536d2c8089685630fafe88cf7805966fc3"

L1_OPTIMISM_TOKENS_BRIDGE = "0x76943C0D61395d8F2edF9060e1533529cAe05dE6"
L1_OPTIMISM_TOKENS_BRIDGE_IMPL = "0x29C5c51A031165CE62F964966A6399b81165EFA4"
L1_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW = "0x168Cfea1Ad879d7032B3936eF3b0E90790b6B6D4"

L2_OPTIMISM_TOKENS_BRIDGE = "0x8E01013243a96601a86eb3153F0d9Fa4fbFb6957"
L2_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW = "0x2734602C0CEbbA68662552CacD5553370B283E2E"
L2_OPTIMISM_WSTETH_TOKEN = "0x1F32b1c2345538c0c6f582fCB022739c4A194Ebb"
L2_OPTIMISM_WSTETH_TOKEN_IMPL_NEW = "0xFe57042De76c8D6B1DF0E9E2047329fd3e2B7334"

def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env):

    l1_token_bridge = interface.L1LidoTokensBridge(L1_OPTIMISM_TOKENS_BRIDGE)

    # Prepare required state for the voting
    if l1_token_bridge.isDepositsEnabled():
        agent = accounts.at(AGENT, force=True)
        l1_token_bridge.disableDeposits({"from": agent})

    check_pre_upgrade_state()
    wsteth_bridge_balance_before = contracts.wsteth.balanceOf(L1_OPTIMISM_TOKENS_BRIDGE)

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        vote_id, _ = start_vote({"from": ldo_holder}, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 5, "Incorrect voting items count"

    check_post_upgrade_state(vote_tx)
    assert wsteth_bridge_balance_before == contracts.wsteth.balanceOf(L1_OPTIMISM_TOKENS_BRIDGE)

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

    display_voting_events(vote_tx)
    evs = group_voting_events(vote_tx)

    validate_contract_upgrade(evs[0], L1_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW)
    validate_contract_finalization(evs[1], 2)
    validate_contract_upgrade(evs[2], LIDO_LOCATOR_IMPL_NEW)
    validate_contract_role_granting(evs[3], DEPOSITS_ENABLER_ROLE, L1_EMERGENCY_BRAKES_MULTISIG, AGENT)
    validate_optimism_upgrade_call(
        evs[4],
        L2_OPTIMISM_GOVERNANCE_EXECUTOR,
        AGENT,
        L2_OPTIMISM_TOKENS_BRIDGE,
        L2_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW,
        L2_OPTIMISM_WSTETH_TOKEN,
        L2_OPTIMISM_WSTETH_TOKEN_IMPL_NEW
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

def validate_contract_role_granting(events: EventDict, role: str, account: str, sender: str):
    _events_chain = ["LogScriptCall", "LogScriptCall", "RoleGranted", "ScriptResult"]
    validate_events_chain([e.name for e in events], _events_chain)
    assert events.count("RoleGranted") == 1
    assert events["RoleGranted"]["role"] == role
    assert events["RoleGranted"]["account"] == account
    assert events["RoleGranted"]["sender"] == sender

def validate_optimism_upgrade_call(
        events: EventDict,
        target: str,
        sender: str,
        l2_bridge_proxy: str,
        l2_bridge_impl: str,
        l2_wst_proxy: str,
        l2_wst_impl: str):
    _events_chain = ["LogScriptCall", "LogScriptCall", "TransactionDeposited", "SentMessage", "SentMessageExtension1", "ScriptResult"]
    validate_events_chain([e.name for e in events], _events_chain)
    assert events.count("SentMessage") == 1
    # Check bytecode that was sent to messenger to update L2 bridge and wstETH token
    encoded_l2_upgrade_call = encode_l2_upgrade_call(l2_bridge_proxy, l2_bridge_impl, l2_wst_proxy, l2_wst_impl)
    assert events["SentMessage"]["message"] == encoded_l2_upgrade_call
    assert events["SentMessage"]["target"] == target
    assert events["SentMessage"]["sender"] == sender


