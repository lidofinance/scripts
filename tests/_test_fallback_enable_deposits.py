"""
Tests for fallback enable deposits voting xx/xx/2024
"""
from scripts.fallback_enable_deposits import start_vote
from brownie import interface, reverts
from utils.test.tx_tracing_helpers import *
from utils.config import (
    contracts,
    AGENT,
    L1_OPTIMISM_TOKENS_BRIDGE,
)

L1_TOKEN_BRIDGE_OLD_IMPL: str = "0x29C5c51A031165CE62F964966A6399b81165EFA4"


def test_vote(helpers, accounts, vote_ids_from_env, ldo_holder):
    l1_token_bridge_proxy = interface.OssifiableProxy(L1_OPTIMISM_TOKENS_BRIDGE)
    l1_token_bridge = interface.L1LidoTokensBridge(L1_OPTIMISM_TOKENS_BRIDGE)

    # Prepare required state for the voting
    if l1_token_bridge.isDepositsEnabled():
        agent = accounts.at(AGENT, force=True)
        l1_token_bridge.disableDeposits({"from": agent})

    # Disabled deposits is the starting condition for the vote
    assert not l1_token_bridge.isDepositsEnabled()

    # L1 Bridge hasn't been upgraded (just in case check)
    assert l1_token_bridge_proxy.proxy__getImplementation() == L1_TOKEN_BRIDGE_OLD_IMPL

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        vote_id, _ = start_vote({"from": ldo_holder}, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 1, "Incorrect voting items count"

    # Check the deposits are indeed enabled
    assert l1_token_bridge.isDepositsEnabled()
