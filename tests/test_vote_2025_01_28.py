"""
Tests for voting 28/01/2025.
"""

from typing import Dict, Tuple, List, NamedTuple
from scripts.vote_2025_01_28 import start_vote
from brownie import interface
from utils.test.tx_tracing_helpers import *
from utils.config import contracts, LDO_HOLDER_ADDRESS_FOR_TESTS
from utils.config import contracts

def test_vote(helpers, accounts, vote_ids_from_env, stranger):

    csm: interface.CSModule = contracts.csm
    staking_router: interface.StakingRouter = contracts.staking_router
    node_operators_registry = contracts.node_operators_registry

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)
    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)
    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    #
    # I. Community staking module: limit increase + turn off EA mode
    #
    # 2. Activate public release mode
    assert csm.publicRelease() == True

    # 4. Increase share from 1% to 2%
    assert staking_router.getStakingModule(3)["stakeShareLimit"] == 200

    #
    # II. NO Acquisitions - Bridgetower is now part of Solstice Staking
    #
    # 1. Change name of Bridgetower to Solstice
    assert node_operators_registry.getNodeOperator(17, True)["name"] == "Solstice"

    # events
    display_voting_events(vote_tx)
    evs = group_voting_events(vote_tx)
