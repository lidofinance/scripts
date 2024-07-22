"""
Tests for voting 24/01/2023.
"""

import math
import time

from brownie.network.account import LocalAccount

from scripts.vote_2024_07_23 import start_vote
from utils.config import contracts
from utils.test.deposits_helpers import fill_deposit_buffer, drain_buffered_ether
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
    name="Simple DVT Module",
    address=None,
    target_share=400,
    module_fee=800,
    treasury_fee=200,
)

expected_payout = Payout(
    token_addr="0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32",
    from_addr=agent_addr,
    to_addr="0x17F6b2C738a63a8D3A113a228cfd0b373244633D",
    # https://docs.lido.fi/multisigs/lido-contributors-group#41-pool-maintenance-labs-ltd-pml
    amount=96_666_62 * (10**16),  # 96,666.62 LDO in wei,
)


def test_hh_cache(helpers, accounts):
    start_time = time.time()
    evm_script_executor: LocalAccount = accounts.at(contracts.easy_track.evmScriptExecutor(), force=True)
    last_nop_id = fill_sdvt_module_with_keys(evm_script_executor=evm_script_executor, total_keys=100)
    print("--- %s seconds ---" % (time.time() - start_time))


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, bypass_events_decoding):
    dao_voting = contracts.voting
    ldo_token = contracts.ldo_token

    agent_ldo_before = ldo_token.balanceOf(agent_addr)
    pml_balance_before = ldo_token.balanceOf(expected_payout.to_addr)
    sdvt_module_before = contracts.staking_router.getStakingModule(SIMPLE_DVT_ID)
    assert sdvt_module_before["targetShare"] == 50, "Simple DVT Module target share must be 0.5% before vote"

    # START VOTE
    vote_id = vote_ids_from_env[0] if vote_ids_from_env else start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # Validate vote events
    if not bypass_events_decoding:
        assert count_vote_items_by_events(tx, dao_voting) == 2, "Incorrect voting items count"

    # Check that Simple DVT Module target share changed correctly
    sdvt_module_after = contracts.staking_router.getStakingModule(SIMPLE_DVT_ID)
    assert (
        sdvt_module_after["targetShare"] == expected_sdvt_module.target_share
    ), "Simple DVT Module target share must be updated correctly"

    # Check that other values left unchanged
    assert sdvt_module_after["stakingModuleFee"] == sdvt_module_before["stakingModuleFee"]
    assert sdvt_module_after["treasuryFee"] == sdvt_module_before["treasuryFee"]

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


def test_stake_allocation_after_voting(accounts, helpers, ldo_holder, vote_ids_from_env):
    evm_script_executor: LocalAccount = accounts.at(contracts.easy_track.evmScriptExecutor(), force=True)
    sdvt_remaining_cap_before: int = get_staking_module_remaining_cap(SIMPLE_DVT_ID)
    check_alloc_keys = sdvt_remaining_cap_before

    # Fill the module with keys. Keep last nop_id to add more keys to other node operators later
    last_nop_id = fill_sdvt_module_with_keys(
        evm_script_executor=evm_script_executor, total_keys=sdvt_remaining_cap_before
    )

    _, sdvt_allocation_percentage_after_filling = get_allocation_percentage(check_alloc_keys)

    assert sdvt_allocation_percentage_after_filling == 0.5  # 0.5% of total allocated keys — current target share

    # add more keys to the module to check that percentage wasn't changed
    last_nop_id = fill_sdvt_module_with_keys(
        evm_script_executor=evm_script_executor, total_keys=200, start_nop_id=last_nop_id - 1
    )

    _, sdvt_allocation_percentage_after = get_allocation_percentage(check_alloc_keys + 200)

    assert (
        sdvt_allocation_percentage_after == sdvt_allocation_percentage_after_filling
    )  # share percentage should not change after second filling

    # VOTE!
    vote_id = vote_ids_from_env[0] if vote_ids_from_env else start_vote({"from": ldo_holder}, silent=True)[0]
    helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=contracts.voting, skip_time=3 * 60 * 60 * 24)

    # add more keys to the module
    fill_sdvt_module_with_keys(evm_script_executor=evm_script_executor, total_keys=300, start_nop_id=last_nop_id - 1)

    sdvt_remaining_cap_after_vote = get_staking_module_remaining_cap(SIMPLE_DVT_ID)

    assert sdvt_remaining_cap_after_vote > sdvt_remaining_cap_before  # remaining cap should increase after the vote

    _, sdvt_allocation_percentage_after_vote = get_allocation_percentage(sdvt_remaining_cap_after_vote)

    assert (
        sdvt_allocation_percentage_after_vote > sdvt_allocation_percentage_after_filling
    )  # allocation percentage should increase after the vote


def test_sdvt_stake_allocation(accounts, helpers, ldo_holder, vote_ids_from_env):
    evm_script_executor: LocalAccount = accounts.at(contracts.easy_track.evmScriptExecutor(), force=True)
    nor_module_stats_before = contracts.staking_router.getStakingModuleSummary(NODE_OPERATORS_REGISTRY_ID)
    sdvt_module_stats_before = contracts.staking_router.getStakingModuleSummary(SIMPLE_DVT_ID)

    new_sdvt_keys_amount = 60

    # prepare buffer to accept 200 keys
    drain_buffered_ether()
    fill_deposit_buffer(200)

    # VOTE!
    vote_id = vote_ids_from_env[0] if vote_ids_from_env else start_vote({"from": ldo_holder}, silent=True)[0]
    helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=contracts.voting, skip_time=3 * 60 * 60 * 24)

    # No new keys in the SDVT module
    contracts.lido.deposit(100, NODE_OPERATORS_REGISTRY_ID, "0x0", {"from": contracts.deposit_security_module})
    contracts.lido.deposit(100, SIMPLE_DVT_ID, "0x0", {"from": contracts.deposit_security_module})
    nor_module_stats_after_vote = contracts.staking_router.getStakingModuleSummary(NODE_OPERATORS_REGISTRY_ID)
    sdvt_module_stats_after_vote = contracts.staking_router.getStakingModuleSummary(SIMPLE_DVT_ID)

    assert (
        sdvt_module_stats_after_vote["totalDepositedValidators"] == sdvt_module_stats_before["totalDepositedValidators"]
    ), "No new keys should go to the SDVT module"
    assert (
        nor_module_stats_after_vote["totalDepositedValidators"]
        == nor_module_stats_before["totalDepositedValidators"] + 100
    ), "All keys should go to the NOR module"

    # Add new keys to the SDVT module
    fill_sdvt_module_with_keys(evm_script_executor=evm_script_executor, total_keys=new_sdvt_keys_amount)

    contracts.lido.deposit(100, NODE_OPERATORS_REGISTRY_ID, "0x0", {"from": contracts.deposit_security_module})
    contracts.lido.deposit(100, SIMPLE_DVT_ID, "0x0", {"from": contracts.deposit_security_module})
    nor_module_stats_after = contracts.staking_router.getStakingModuleSummary(NODE_OPERATORS_REGISTRY_ID)
    sdvt_module_stats_after = contracts.staking_router.getStakingModuleSummary(SIMPLE_DVT_ID)

    assert sdvt_module_stats_after["depositableValidatorsCount"] == 0, "All accessible keys should be deposited"
    assert (
        sdvt_module_stats_after["totalDepositedValidators"]
        == sdvt_module_stats_after_vote["totalDepositedValidators"] + new_sdvt_keys_amount
    ), f"{new_sdvt_keys_amount} keys should go to the SDVT module"
    assert nor_module_stats_after["totalDepositedValidators"] == nor_module_stats_after_vote[
        "totalDepositedValidators"
    ] + (100 - new_sdvt_keys_amount), "All other keys should go to the NOR module"


def fill_sdvt_module_with_keys(evm_script_executor: LocalAccount, total_keys: int, start_nop_id: int = 0) -> int:
    if start_nop_id == 0:
        start_nop_id = contracts.simple_dvt.getNodeOperatorsCount() - 1
    nop_id = start_nop_id

    keys_to_allocate = (
        total_keys if total_keys < 100 else 100
    )  # keys to allocate to each node operator, base batch is 100 keys per operator
    steps = 1 if keys_to_allocate == total_keys else (total_keys // keys_to_allocate) + 1
    for idx in range(steps):
        nop_id = start_nop_id - idx
        simple_dvt_add_keys(contracts.simple_dvt, nop_id, keys_to_allocate)
        contracts.simple_dvt.setNodeOperatorStakingLimit(nop_id, keys_to_allocate, {"from": evm_script_executor})

    return nop_id


def get_staking_module_remaining_cap(staking_module_id: int) -> int:
    module_summary = contracts.staking_router.getStakingModuleSummary(staking_module_id)
    module_active_keys = module_summary["totalDepositedValidators"] - module_summary["totalExitedValidators"]

    all_modules_summary = [
        contracts.staking_router.getStakingModuleSummary(module_id)
        for module_id in [NODE_OPERATORS_REGISTRY_ID, SIMPLE_DVT_ID]
    ]
    total_active_keys = sum(
        module_summary["totalDepositedValidators"] - module_summary["totalExitedValidators"]
        for module_summary in all_modules_summary
    )

    target_share = contracts.staking_router.getStakingModule(staking_module_id)["targetShare"]

    return math.ceil((target_share * total_active_keys) / TOTAL_BASIS_POINTS) - module_active_keys


def get_allocation_percentage(keys_to_allocate: int) -> (float, float):
    allocation = contracts.staking_router.getDepositsAllocation(keys_to_allocate)
    total_allocated = sum(allocation["allocations"])
    return (round((allocation["allocations"][0] / total_allocated) * TOTAL_BASIS_POINTS) / 100), (
        round((allocation["allocations"][1] / total_allocated) * TOTAL_BASIS_POINTS) / 100
    )
