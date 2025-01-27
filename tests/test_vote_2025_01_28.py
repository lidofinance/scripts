"""
Tests for voting 28/01/2025.
"""

from typing import Dict, Tuple, List, NamedTuple
from scripts.vote_2025_01_28 import start_vote
from brownie import interface
from utils.test.tx_tracing_helpers import *
from utils.config import contracts, LDO_HOLDER_ADDRESS_FOR_TESTS
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.test.event_validators.csm import validate_public_release_event
from utils.test.event_validators.staking_router import validate_staking_module_update_event, StakingModuleItem
from utils.test.event_validators.node_operators_registry import validate_node_operator_name_set_event, NodeOperatorNameSetItem
from utils.test.event_validators.permission import validate_grant_role_event, validate_revoke_role_event

def test_vote(helpers, accounts, vote_ids_from_env, stranger):

    csm = interface.CSModule("0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F")
    staking_router = interface.StakingRouter("0xFdDf38947aFB03C621C71b06C9C70bce73f12999")
    node_operators_registry = interface.NodeOperatorsRegistry("0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5")
    agent = interface.Agent("0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c")
    module_manager_role = "0x79dfcec784e591aafcf60db7db7b029a5c8b12aac4afd4e8c4eb740430405fa6"
    csm_module_id = 3
    new_stake_share_limit = 200 #2%
    new_priority_exit_share_threshold = 250
    new_name = "Solstice"
    old_name = "BridgeTower"
    old_stake_share_limit = 100 #1%
    old_priority_exit_share_threshold = 125
    old_staking_module_fee = 600
    old_treasury_fee = 400
    old_max_deposits_per_block = 30
    old_min_deposit_block_distance = 25

    # Agent doesn't have MODULE_MANAGER_ROLE
    assert csm.hasRole(module_manager_role, agent) is False

    # Public release mode is not active
    assert csm.publicRelease() is False

    # Check old data
    assert staking_router.getStakingModule(csm_module_id)["stakeShareLimit"] == old_stake_share_limit
    assert staking_router.getStakingModule(csm_module_id)["priorityExitShareThreshold"] == old_priority_exit_share_threshold
    assert staking_router.getStakingModule(csm_module_id)["stakingModuleFee"] == old_staking_module_fee
    assert staking_router.getStakingModule(csm_module_id)["treasuryFee"] == old_treasury_fee
    assert staking_router.getStakingModule(csm_module_id)["maxDepositsPerBlock"] == old_max_deposits_per_block
    assert staking_router.getStakingModule(csm_module_id)["minDepositBlockDistance"] == old_min_deposit_block_distance

    # Check old name
    assert node_operators_registry.getNodeOperator(17, True)["name"] == old_name

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)
    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)
    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    #
    # I. CSM: Enable Permissionless Phase and Increase the Share Limit
    #
    # 2. Activate public release mode on CS Module
    assert csm.publicRelease() is True

    # 3. Increase stake share limit from 1% to 2% on CS Module
    assert staking_router.getStakingModule(csm_module_id)["stakeShareLimit"] == new_stake_share_limit
    assert staking_router.getStakingModule(csm_module_id)["priorityExitShareThreshold"] == new_priority_exit_share_threshold
    assert staking_router.getStakingModule(csm_module_id)["stakingModuleFee"] == old_staking_module_fee
    assert staking_router.getStakingModule(csm_module_id)["treasuryFee"] == old_treasury_fee
    assert staking_router.getStakingModule(csm_module_id)["maxDepositsPerBlock"] == old_max_deposits_per_block
    assert staking_router.getStakingModule(csm_module_id)["minDepositBlockDistance"] == old_min_deposit_block_distance

    # 4. Revoke MODULE_MANAGER_ROLE on CS Module from Aragon Agent
    assert csm.hasRole(module_manager_role, agent) is False

    #
    # II. NO Acquisitions:  Bridgetower is now part of Solstice Staking
    #
    # 5. Rename Node Operator ID 17 from BridgeTower to Solstice
    assert node_operators_registry.getNodeOperator(17, True)["name"] == new_name

    # events
    display_voting_events(vote_tx)
    evs = group_voting_events(vote_tx)

    metadata = find_metadata_by_vote_id(vote_id)
    assert get_lido_vote_cid_from_str(metadata) == "bafkreierrixpk7pszth7pkgau7iyhb4mxolskst62oyfat3ltfrnh355ty"

    assert count_vote_items_by_events(vote_tx, contracts.voting) == 5, "Incorrect voting items count"

    # validate events
    validate_grant_role_event(evs[0], module_manager_role, agent.address, agent.address)

    validate_public_release_event(evs[1])

    expected_staking_module_item = StakingModuleItem(
        id=csm_module_id,
        name="Community Staking",
        address=None,
        target_share=new_stake_share_limit,
        module_fee=old_staking_module_fee,
        treasury_fee=old_treasury_fee,
    )

    validate_staking_module_update_event(evs[2], expected_staking_module_item)

    validate_revoke_role_event(evs[3], module_manager_role, agent.address, agent.address)

    expected_node_operator_item = NodeOperatorNameSetItem(
        nodeOperatorId=17,
        name="Solstice",
    )
    validate_node_operator_name_set_event(evs[4], expected_node_operator_item)
