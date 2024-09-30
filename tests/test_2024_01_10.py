"""
Tests for voting 01/10/2024
"""
from scripts.upgrade_2024_01_10 import start_vote, check_pre_upgrade_state, check_post_upgrade_state
from brownie import interface, reverts, network, accounts
from utils.test.tx_tracing_helpers import *
from utils.config import (
    contracts,
    L1_OPTIMISM_TOKENS_BRIDGE,
    AGENT,
)
from utils.test.helpers import ETH


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
    # TODO: this check fails on anvil
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 5, "Incorrect voting items count"

    check_post_upgrade_state(vote_tx)
    assert wsteth_bridge_balance_before == contracts.wsteth.balanceOf(L1_OPTIMISM_TOKENS_BRIDGE)
