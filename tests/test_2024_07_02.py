"""
Tests for voting 24/01/2023.
"""

import math

from brownie import Contract
from brownie.network.account import LocalAccount

from scripts.vote_2024_07_02 import start_vote
from utils.config import contracts
from utils.mainnet_fork import chain_snapshot
from utils.test.event_validators.staking_router import validate_staking_module_update_event, StakingModuleItem
from utils.test.simple_dvt_helpers import simple_dvt_add_keys
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.payout import (
    validate_token_payout_event,
    Payout,
)
from brownie.network.transaction import TransactionReceipt

TOTAL_BASIS_POINTS = 10_000
NODE_OPERATORS_REGISTRY_ID = 1
SIMPLE_DVT_ID = 2

agent_addr = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
expected_sdvt_module = StakingModuleItem(
    id=SIMPLE_DVT_ID,
    address="0x7c40c393DC0f283F318791d746d894DdD3693572",
    name="Simple DVT Module",
    target_share=400,
    module_fee=800,
    treasury_fee=200,
)
expected_payout = Payout(
    token_addr="0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32",
    from_addr=agent_addr,
    to_addr="0x17F6b2C738a63a8D3A113a228cfd0b373244633D",
    # https://docs.lido.fi/multisigs/lido-contributors-group#41-pool-maintenance-labs-ltd-pml
    amount=180_000 * (10**18),  # 180K LDO in wei,
)


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, bypass_events_decoding):
    dao_voting = contracts.voting
    ldo_token = contracts.ldo_token

    agent_ldo_before = ldo_token.balanceOf(agent_addr)
    pml_balance_before = ldo_token.balanceOf(expected_payout.to_addr)
    sdvtModuleShareBefore = contracts.staking_router.getStakingModule(expected_sdvt_module.id)["targetShare"]
    assert sdvtModuleShareBefore == 50, "Simple DVT Module target share must be 0.5% before vote"

    with chain_snapshot():
        # START VOTE
        vote_id = vote_ids_from_env[0] if vote_ids_from_env else start_vote({"from": ldo_holder}, silent=True)[0]

        tx: TransactionReceipt = helpers.execute_vote(
            vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
        )

        # Validate vote events
        if not bypass_events_decoding:
            assert count_vote_items_by_events(tx, dao_voting) == 2, "Incorrect voting items count"

        # Check Simple DVT Module target share
        sdvtModule = contracts.staking_router.getStakingModule(expected_sdvt_module.id)
        assert (
            sdvtModule["targetShare"] == expected_sdvt_module.target_share
        ), "Simple DVT Module target share must be updated correctly"

        # Check LDO payment
        assert (
            ldo_token.balanceOf(agent_addr) == agent_ldo_before - expected_payout.amount
        ), "DAO Agent LDO balance must decrease by the correct amount"
        assert (
            ldo_token.balanceOf(expected_payout.to_addr) == pml_balance_before + expected_payout.amount
        ), "Destination address LDO balance must increase by the correct amount"

        # Check events if their decoding is available
        if bypass_events_decoding:
            return

        display_voting_events(tx)

        evs = group_voting_events(tx)
        validate_staking_module_update_event(evs[0], expected_sdvt_module)
        validate_token_payout_event(evs[1], expected_payout)


def test_stake_allocation_after_voting(accounts, helpers, ldo_holder, vote_ids_from_env, eth_whale, stranger):
    dao_voting: Contract = contracts.voting
    evm_script_executor: LocalAccount = accounts.at(contracts.easy_track.evmScriptExecutor(), force=True)
    sdvt_remaining_cap_before: int = get_staking_module_remaining_cap(SIMPLE_DVT_ID)
    check_alloc_keys = sdvt_remaining_cap_before

    with chain_snapshot():
        # Fill the module with keys. Keep last nop_id to add more keys to oter node operators later
        last_nop_id = fill_sdvt_module_with_keys(
            evm_script_executor=evm_script_executor, keys_total_count=sdvt_remaining_cap_before
        )

        _, sdvt_allocation_percentage_after_filling = get_allocation_percentage(check_alloc_keys)

        assert sdvt_allocation_percentage_after_filling == 0.5  # 0.5% of total allocated keys — current target share

        # add more keys to the module to check that percentage wasn't changed
        last_nop_id = fill_sdvt_module_with_keys(
            evm_script_executor=evm_script_executor, keys_total_count=200, start_nop_id=last_nop_id - 1
        )

        _, sdvt_allocation_percentage_after = get_allocation_percentage(check_alloc_keys)

        assert (
            sdvt_allocation_percentage_after == sdvt_allocation_percentage_after_filling
        )  # share percentage should not change after second filling

        # VOTE!
        vote_id = vote_ids_from_env[0] if vote_ids_from_env else start_vote({"from": ldo_holder}, silent=True)[0]
        helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24)

        # add more keys to the module
        fill_sdvt_module_with_keys(
            evm_script_executor=evm_script_executor, keys_total_count=300, start_nop_id=last_nop_id - 1
        )

        sdvt_remaining_cap_after_vote = get_staking_module_remaining_cap(SIMPLE_DVT_ID)

        assert sdvt_remaining_cap_after_vote > sdvt_remaining_cap_before  # remaining cap should increase after the vote

        _, sdvt_allocation_percentage_after_vote = get_allocation_percentage(sdvt_remaining_cap_after_vote)

        assert (
            sdvt_allocation_percentage_after_vote > sdvt_allocation_percentage_after_filling
        )  # allocation percentage should increase after the vote


def fill_sdvt_module_with_keys(evm_script_executor: LocalAccount, keys_total_count: int, start_nop_id: int = 0) -> int:
    keys_to_allocate = 100  # keys to allocate to each node operator
    if start_nop_id == 0:
        start_nop_id = contracts.simple_dvt.getNodeOperatorsCount() - 1
    nop_id = start_nop_id

    steps = (keys_total_count // keys_to_allocate) + 1
    for idx in range(steps):
        nop_id = start_nop_id - idx
        simple_dvt_add_keys(contracts.simple_dvt, nop_id, keys_to_allocate)
        contracts.simple_dvt.setNodeOperatorStakingLimit(nop_id, keys_to_allocate, {"from": evm_script_executor})

    return nop_id


def get_staking_module_remaining_cap(staking_module_id: int) -> int:
    summary = contracts.staking_router.getStakingModuleSummary(staking_module_id)
    active_keys = summary["totalDepositedValidators"] - summary["totalExitedValidators"]
    total_active_keys = sum(
        [
            contracts.staking_router.getStakingModuleSummary(module_id)["totalDepositedValidators"]
            - contracts.staking_router.getStakingModuleSummary(module_id)["totalExitedValidators"]
            for module_id in [NODE_OPERATORS_REGISTRY_ID, SIMPLE_DVT_ID]
        ]
    )
    target_share = contracts.staking_router.getStakingModule(staking_module_id)["targetShare"]
    return math.ceil((target_share * total_active_keys) / TOTAL_BASIS_POINTS) - active_keys


def get_allocation_percentage(keys_to_allocate: int) -> (float, float):
    allocation_from_contract_after_vote = contracts.staking_router.getDepositsAllocation(keys_to_allocate)
    total_allocated_after_vote = sum(allocation_from_contract_after_vote["allocations"])
    return (
        round((allocation_from_contract_after_vote["allocations"][0] / total_allocated_after_vote) * TOTAL_BASIS_POINTS)
        / 100
    ), (
        round((allocation_from_contract_after_vote["allocations"][1] / total_allocated_after_vote) * TOTAL_BASIS_POINTS)
        / 100
    )
