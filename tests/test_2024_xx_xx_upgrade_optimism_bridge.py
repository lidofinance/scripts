"""
Tests for voting xx/xx/2024
"""

from scripts.vote_2024_xx_xx_upgrade_optimism_bridge import start_vote
from brownie import interface
from utils.test.tx_tracing_helpers import *
from utils.config import (
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    # LIDO,
    # AGENT
)

L1_TOKEN_BRIDGE_PROXY: str = "0x76943C0D61395d8F2edF9060e1533529cAe05dE6"

L1_TOKEN_BRIDGE_OLD_IMPL: str = "0x29C5c51A031165CE62F964966A6399b81165EFA4"
L1_TOKEN_BRIDGE_NEW_IMPL: str = "0xc4E3ff0b5B106f88Fc64c43031BE8b076ee9F21C"

def test_vote(
    helpers,
    accounts,
    vote_ids_from_env
):
    l1_token_bridge_proxy = interface.OssifiableProxy(L1_TOKEN_BRIDGE_PROXY);

    l1_token_bridge_implementation_address_before = l1_token_bridge_proxy.proxy__getImplementation()
    assert l1_token_bridge_implementation_address_before == L1_TOKEN_BRIDGE_OLD_IMPL, "Old address is incorrect"

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # validate vote events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 1, "Incorrect voting items count"


    l1_token_bridge_implementation_address_after = l1_token_bridge_proxy.proxy__getImplementation()
    assert l1_token_bridge_implementation_address_before != l1_token_bridge_implementation_address_after, "Implementation is not changed"
    assert l1_token_bridge_implementation_address_after == L1_TOKEN_BRIDGE_NEW_IMPL, "New address is incorrect"

