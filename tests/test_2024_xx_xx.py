"""
Tests for voting xx/xx/2024
"""
from scripts.vote_2024_xx_xx import start_vote, encode_l2_upgrade_call
from brownie import interface, reverts
from utils.test.tx_tracing_helpers import *
from utils.config import (
    contracts,
    LIDO_LOCATOR,
    LIDO_LOCATOR_IMPL,
    LIDO_LOCATOR_IMPL_NEW,
    L1_OPTIMISM_TOKENS_BRIDGE,
    L1_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW,
    L1_EMERGENCY_BRAKES_MULTISIG,
    L2_OPTIMISM_TOKENS_BRIDGE,
    L2_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW,
    L2_OPTIMISM_WSTETH_TOKEN,
    L2_OPTIMISM_WSTETH_IMPL_NEW,
    AGENT,
)

DEPOSITS_ENABLER_ROLE = "0x4b43b36766bde12c5e9cbbc37d15f8d1f769f08f54720ab370faeb4ce893753a"
L1_OPTIMISM_TOKENS_BRIDGE_IMPL_OLD: str = "0x29C5c51A031165CE62F964966A6399b81165EFA4"


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env):
    l1_token_bridge_proxy = interface.OssifiableProxy(L1_OPTIMISM_TOKENS_BRIDGE)
    l1_token_bridge = interface.L1LidoTokensBridge(L1_OPTIMISM_TOKENS_BRIDGE)
    lido_locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)

    # Prepare required state for the voting
    if l1_token_bridge.isDepositsEnabled():
        agent = accounts.at(AGENT, force=True)
        l1_token_bridge.disableDeposits({"from": agent})

    # Disabled deposits is the starting condition for the vote
    assert not l1_token_bridge.isDepositsEnabled()

    # L1 Bridge has old implementation
    l1_token_bridge_implementation_address_before = l1_token_bridge_proxy.proxy__getImplementation()
    assert (
        l1_token_bridge_implementation_address_before == L1_OPTIMISM_TOKENS_BRIDGE_IMPL_OLD
    ), "Old address is incorrect"

    # L1 Bridge doesn't have version before update
    with reverts():
        l1_token_bridge.getContractVersion()

    # Upgrade LidoLocator implementation
    lido_locator_impl_before = lido_locator_proxy.proxy__getImplementation()
    assert lido_locator_impl_before == LIDO_LOCATOR_IMPL, "Old address is incorrect"

    # Multisig hasn't been assigned as deposit enabler
    assert l1_token_bridge.hasRole(DEPOSITS_ENABLER_ROLE, L1_EMERGENCY_BRAKES_MULTISIG) is False

    wsteth_bridge_balance_before = contracts.wsteth.balanceOf(L1_OPTIMISM_TOKENS_BRIDGE)

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        vote_id, _ = start_vote({"from": ldo_holder}, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # validate vote events
    # TODO: this check fails on anvil
    # assert count_vote_items_by_events(vote_tx, contracts.voting) == 5, "Incorrect voting items count"

    # L1 Bridge has new implementation
    l1_token_bridge_implementation_address_after = l1_token_bridge_proxy.proxy__getImplementation()
    assert (
        l1_token_bridge_implementation_address_before != l1_token_bridge_implementation_address_after
    ), "Implementation is not changed"
    assert (
        l1_token_bridge_implementation_address_after == L1_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW
    ), "New address is incorrect"

    # update L1 Bridge to 2 version
    assert l1_token_bridge.getContractVersion() == 2

    # LidoLocator has new implementation
    lido_locator_impl_after = lido_locator_proxy.proxy__getImplementation()
    assert lido_locator_impl_before != lido_locator_impl_after, "Implementation is not changed"
    assert lido_locator_impl_after == LIDO_LOCATOR_IMPL_NEW, "New LidoLocator address is incorrect"

    # Multisig has been assigned as deposit enabler
    assert l1_token_bridge.hasRole(DEPOSITS_ENABLER_ROLE, L1_EMERGENCY_BRAKES_MULTISIG)
    # TODO: check multisig can renounce the role

    # Check bytecode that was send to messenger to update L2 bridge and wstETH token
    sentMessage = vote_tx.events["SentMessage"]["message"]
    encoded_l2_upgrade_call = encode_l2_upgrade_call(
        L2_OPTIMISM_TOKENS_BRIDGE,
        L2_OPTIMISM_TOKENS_BRIDGE_IMPL_NEW,
        L2_OPTIMISM_WSTETH_TOKEN,
        L2_OPTIMISM_WSTETH_IMPL_NEW,
    )
    assert sentMessage == encoded_l2_upgrade_call

    wst_eth_bridge_balance_after = contracts.wsteth.balanceOf(L1_OPTIMISM_TOKENS_BRIDGE)
    assert wsteth_bridge_balance_before == wst_eth_bridge_balance_after
