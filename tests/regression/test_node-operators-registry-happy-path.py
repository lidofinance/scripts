import pytest
from web3 import Web3
from brownie import chain, ZERO_ADDRESS
from typing import NewType, Tuple

from utils.test.extra_data import (
    ExtraDataService,
)
from utils.test.helpers import shares_balance, ETH, almostEqWithDiff
from utils.test.oracle_report_helpers import (
    oracle_report,
)
from utils.config import contracts, lido_dao_staking_router


@pytest.fixture()
def extra_data_service():
    return ExtraDataService()


@pytest.fixture(scope="module")
def impersonated_voting(accounts):
    return accounts.at(contracts.voting.address, force=True)


StakingModuleId = NewType("StakingModuleId", int)
NodeOperatorId = NewType("NodeOperatorId", int)
NodeOperatorGlobalIndex = Tuple[StakingModuleId, NodeOperatorId]


def node_operator_gindex(module_id, node_operator_id) -> NodeOperatorGlobalIndex:
    return module_id, node_operator_id


@pytest.fixture(scope="module")
def nor(interface):
    return interface.NodeOperatorsRegistry(contracts.node_operators_registry.address)


def calc_no_rewards(nor, no_id, shares_minted_as_fees):
    operator_summary = nor.getNodeOperatorSummary(no_id)
    module_summary = nor.getStakingModuleSummary()

    operator_total_active_keys = (
        operator_summary["totalDepositedValidators"] - operator_summary["totalExitedValidators"]
    )
    module_total_active_keys = module_summary["totalDepositedValidators"] - module_summary["totalExitedValidators"]

    nor_shares = shares_minted_as_fees // 2

    return nor_shares * operator_total_active_keys // module_total_active_keys


def increase_limit(nor, first_id, second_id, base_id, keys_count, impersonated_voting):
    first_no = nor.getNodeOperator(first_id, True)
    second_no = nor.getNodeOperator(second_id, True)
    base_no = nor.getNodeOperator(base_id, True)

    current_first_keys = first_no["totalVettedValidators"] - first_no["totalExitedValidators"]
    current_second_keys = second_no["totalVettedValidators"] - second_no["totalExitedValidators"]
    current_base_keys = base_no["totalVettedValidators"] - base_no["totalExitedValidators"]

    nor.setNodeOperatorStakingLimit(first_id, current_first_keys + keys_count, {"from": impersonated_voting})
    nor.setNodeOperatorStakingLimit(second_id, current_second_keys + keys_count, {"from": impersonated_voting})
    nor.setNodeOperatorStakingLimit(base_id, current_base_keys + keys_count, {"from": impersonated_voting})


def deposit_and_check_keys(nor, first_no_id, second_no_id, base_no_id, keys_count):

    deposited_keys_first_before = nor.getNodeOperatorSummary(first_no_id)["totalDepositedValidators"]
    deposited_keys_second_before = nor.getNodeOperatorSummary(second_no_id)["totalDepositedValidators"]
    deposited_keys_base_before = nor.getNodeOperatorSummary(base_no_id)["totalDepositedValidators"]
    validators_before = contracts.lido.getBeaconStat().dict()["depositedValidators"]

    module_total_deposited_keys_before = nor.getStakingModuleSummary()["totalDepositedValidators"]

    tx = contracts.lido.deposit(keys_count, 1, "0x", {"from": contracts.deposit_security_module.address})

    validators_after = contracts.lido.getBeaconStat().dict()["depositedValidators"]
    module_total_deposited_keys_after = nor.getStakingModuleSummary()["totalDepositedValidators"]

    just_deposited = validators_after - validators_before
    print("---------", just_deposited)
    if just_deposited:
        assert tx.events["DepositedValidatorsChanged"]["depositedValidators"] == validators_after
        assert tx.events["Unbuffered"]["amount"] == just_deposited * ETH(32)
        assert module_total_deposited_keys_before + just_deposited == module_total_deposited_keys_after

    deposited_keys_first_after = nor.getNodeOperatorSummary(first_no_id)["totalDepositedValidators"]
    deposited_keys_second_after = nor.getNodeOperatorSummary(second_no_id)["totalDepositedValidators"]
    deposited_keys_base_after = nor.getNodeOperatorSummary(base_no_id)["totalDepositedValidators"]

    return (
        deposited_keys_first_before,
        deposited_keys_second_before,
        deposited_keys_base_before,
        deposited_keys_first_after,
        deposited_keys_second_after,
        deposited_keys_base_after,
    )


def test_node_operators(nor, extra_data_service, impersonated_voting, eth_whale):
    contracts.staking_router.grantRole(
        Web3.keccak(text="STAKING_MODULE_MANAGE_ROLE"),
        impersonated_voting,
        {"from": contracts.agent.address},
    )

    contracts.acl.grantPermission(
        impersonated_voting,
        nor,
        Web3.keccak(text="STAKING_ROUTER_ROLE"),
        {"from": impersonated_voting},
    )

    contracts.lido.submit(ZERO_ADDRESS, {"from": eth_whale, "amount": ETH(1000)})

    tested_no_id_first = 21
    tested_no_id_second = 22
    base_no_id = 23

    nor.setNodeOperatorStakingLimit(tested_no_id_first, 10000, {"from": impersonated_voting})
    nor.setNodeOperatorStakingLimit(tested_no_id_second, 10000, {"from": impersonated_voting})
    nor.setNodeOperatorStakingLimit(base_no_id, 10000, {"from": impersonated_voting})

    for op_index in range(20):
        nor.setNodeOperatorStakingLimit(op_index, 0, {"from": impersonated_voting})

    for op_index in range(24, 29):
        nor.setNodeOperatorStakingLimit(op_index, 0, {"from": impersonated_voting})

    increase_limit(nor, tested_no_id_first, tested_no_id_second, base_no_id, 3, impersonated_voting)

    penalty_delay = nor.getStuckPenaltyDelay()

    node_operator_first = nor.getNodeOperatorSummary(tested_no_id_first)
    address_first = nor.getNodeOperator(tested_no_id_first, False)["rewardAddress"]
    node_operator_first_balance_shares_before = shares_balance(address_first)

    node_operator_second = nor.getNodeOperatorSummary(tested_no_id_second)
    address_second = nor.getNodeOperator(tested_no_id_second, False)["rewardAddress"]
    node_operator_second_balance_shares_before = shares_balance(address_second)

    node_operator_base = nor.getNodeOperatorSummary(base_no_id)
    address_base_no = nor.getNodeOperator(base_no_id, False)["rewardAddress"]
    node_operator_base_balance_shares_before = shares_balance(address_base_no)

    # First report - base empty report
    (report_tx, extra_report_tx) = oracle_report(exclude_vaults_balances=True)

    node_operator_first_balance_shares_after = shares_balance(address_first)
    node_operator_second_balance_shares_after = shares_balance(address_second)
    node_operator_base_balance_shares_after = shares_balance(address_base_no)

    # expected shares
    node_operator_first_rewards_after_first_report = calc_no_rewards(
        nor, no_id=tested_no_id_first, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_second_rewards_after_first_report = calc_no_rewards(
        nor, no_id=tested_no_id_second, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_base_rewards_after_first_report = calc_no_rewards(
        nor, no_id=base_no_id, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )

    # check shares by empty report
    assert (
        node_operator_first_balance_shares_after - node_operator_first_balance_shares_before
        == node_operator_first_rewards_after_first_report
    )
    assert (
        node_operator_second_balance_shares_after - node_operator_second_balance_shares_before
        == node_operator_second_rewards_after_first_report
    )
    assert (
        node_operator_base_balance_shares_after - node_operator_base_balance_shares_before
        == node_operator_base_rewards_after_first_report
    )

    # Case 1
    # --- operator "First" had 5 keys (exited), and 2 keys got stuck (stuck)
    # --- operator "Second" had 5 keys (exited), and 2 keys got stuck (stuck)
    # - Send report
    # - Check rewards shares for base NO and tested NO (should be half of expected)
    # - Check deposits (should be 0 for penalized NOs)
    # - Check burned shares
    # - Check NOs stats
    # - Check Report events

    # Prepare extra data
    vals_stuck_non_zero = {
        node_operator_gindex(1, tested_no_id_first): 2,
        node_operator_gindex(1, tested_no_id_second): 2,
    }
    vals_exited_non_zero = {
        node_operator_gindex(1, tested_no_id_first): 5,
        node_operator_gindex(1, tested_no_id_second): 5,
    }
    extra_data = extra_data_service.collect(vals_stuck_non_zero, vals_exited_non_zero, 10, 10)

    # shares before report
    node_operator_first_balance_shares_before = shares_balance(address_first)
    node_operator_second_balance_shares_before = shares_balance(address_second)
    node_operator_base_balance_shares_before = shares_balance(address_base_no)

    # Second report - first NO and second NO has stuck/exited
    (report_tx, extra_report_tx) = oracle_report(
        exclude_vaults_balances=True,
        extraDataFormat=1,
        extraDataHash=extra_data.data_hash,
        extraDataItemsCount=2,
        extraDataList=extra_data.extra_data,
        numExitedValidatorsByStakingModule=[10],
        stakingModuleIdsWithNewlyExitedValidators=[1],
    )

    # shares after report
    node_operator_first = nor.getNodeOperatorSummary(tested_no_id_first)
    node_operator_second = nor.getNodeOperatorSummary(tested_no_id_second)
    node_operator_base = nor.getNodeOperatorSummary(base_no_id)

    # expected shares
    node_operator_first_rewards_after_second_report = calc_no_rewards(
        nor, no_id=tested_no_id_first, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_second_rewards_after_second_report = calc_no_rewards(
        nor, no_id=tested_no_id_second, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_base_rewards_after_second_report = calc_no_rewards(
        nor, no_id=base_no_id, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )

    node_operator_first_balance_shares_after = shares_balance(address_first)
    node_operator_second_balance_shares_after = shares_balance(address_second)
    node_operator_base_balance_shares_after = shares_balance(address_base_no)

    # check shares by report with penalty
    assert almostEqWithDiff(
        node_operator_first_balance_shares_after - node_operator_first_balance_shares_before,
        node_operator_first_rewards_after_second_report // 2,
        1,
    )
    assert almostEqWithDiff(
        node_operator_second_balance_shares_after - node_operator_second_balance_shares_before,
        node_operator_second_rewards_after_second_report // 2,
        1,
    )
    assert almostEqWithDiff(
        node_operator_base_balance_shares_after - node_operator_base_balance_shares_before,
        node_operator_base_rewards_after_second_report,
        1,
    )

    # Check burn shares
    amount_penalty_first_no = node_operator_first_rewards_after_second_report // 2
    amount_penalty_second_no = node_operator_second_rewards_after_second_report // 2
    penalty_shares = amount_penalty_first_no + amount_penalty_second_no
    assert almostEqWithDiff(extra_report_tx.events["StETHBurnRequested"]["amountOfShares"], penalty_shares, 2)

    # NO stats
    assert node_operator_first["stuckValidatorsCount"] == 2
    assert node_operator_first["totalExitedValidators"] == 5
    assert node_operator_first["refundedValidatorsCount"] == 0
    assert node_operator_first["stuckPenaltyEndTimestamp"] == 0

    assert node_operator_second["stuckValidatorsCount"] == 2
    assert node_operator_second["totalExitedValidators"] == 5
    assert node_operator_second["refundedValidatorsCount"] == 0
    assert node_operator_second["stuckPenaltyEndTimestamp"] == 0

    assert node_operator_base["stuckValidatorsCount"] == 0
    assert node_operator_base["totalExitedValidators"] == 0
    assert node_operator_base["refundedValidatorsCount"] == 0
    assert node_operator_base["stuckPenaltyEndTimestamp"] == 0

    assert nor.isOperatorPenalized(tested_no_id_first) == True
    assert nor.isOperatorPenalized(tested_no_id_second) == True
    assert nor.isOperatorPenalized(base_no_id) == False

    # Events
    assert extra_report_tx.events["ExitedSigningKeysCountChanged"][0]["nodeOperatorId"] == tested_no_id_first
    assert extra_report_tx.events["ExitedSigningKeysCountChanged"][0]["exitedValidatorsCount"] == 5

    assert extra_report_tx.events["ExitedSigningKeysCountChanged"][1]["nodeOperatorId"] == tested_no_id_second
    assert extra_report_tx.events["ExitedSigningKeysCountChanged"][1]["exitedValidatorsCount"] == 5

    assert extra_report_tx.events["StuckPenaltyStateChanged"][0]["nodeOperatorId"] == tested_no_id_first
    assert extra_report_tx.events["StuckPenaltyStateChanged"][0]["stuckValidatorsCount"] == 2

    assert extra_report_tx.events["StuckPenaltyStateChanged"][1]["nodeOperatorId"] == tested_no_id_second
    assert extra_report_tx.events["StuckPenaltyStateChanged"][1]["stuckValidatorsCount"] == 2

    # Deposit keys
    (
        deposited_keys_first_before,
        deposited_keys_second_before,
        deposited_keys_base_before,
        deposited_keys_first_after,
        deposited_keys_second_after,
        deposited_keys_base_after,
    ) = deposit_and_check_keys(nor, tested_no_id_first, tested_no_id_second, base_no_id, 10)

    # check don't change deposited keys for penalized NO
    assert deposited_keys_first_before == deposited_keys_first_after
    assert deposited_keys_second_before == deposited_keys_second_after
    assert deposited_keys_base_before != deposited_keys_base_after

    # Case 2
    # --- "First" NO exited the keys (stuck == 0, exited increased by the number of stacks)
    # --- BUT the penalty still affects both
    # - Send report
    # - Check rewards shares for base NO and tested NO (should be half of expected)
    # - Check burned shares
    # - Check NOs stats
    # - Check Report events

    # Prepare extra data - first node operator has exited 2 + 5 keys an stuck 0
    vals_stuck_non_zero = {
        node_operator_gindex(1, tested_no_id_first): 0,
    }
    vals_exited_non_zero = {
        node_operator_gindex(1, tested_no_id_first): 7,
    }
    extra_data = extra_data_service.collect(vals_stuck_non_zero, vals_exited_non_zero, 10, 10)

    # shares before report
    node_operator_first_balance_shares_before = shares_balance(address_first)
    node_operator_second_balance_shares_before = shares_balance(address_second)
    node_operator_base_balance_shares_before = shares_balance(address_base_no)

    # Third report - first NO: increase stuck to 0, desc exited to 7 = 5 + 2
    # Second NO: same as prev report
    (report_tx, extra_report_tx) = oracle_report(
        cl_diff=ETH(10),
        exclude_vaults_balances=True,
        extraDataFormat=1,
        extraDataHash=extra_data.data_hash,
        extraDataItemsCount=2,
        extraDataList=extra_data.extra_data,
        numExitedValidatorsByStakingModule=[12],
        stakingModuleIdsWithNewlyExitedValidators=[1],
    )

    node_operator_first = nor.getNodeOperatorSummary(tested_no_id_first)
    node_operator_second = nor.getNodeOperatorSummary(tested_no_id_second)
    node_operator_base = nor.getNodeOperatorSummary(base_no_id)

    # shares after report
    node_operator_first_balance_shares_after = shares_balance(address_first)
    node_operator_second_balance_shares_after = shares_balance(address_second)
    node_operator_base_balance_shares_after = shares_balance(address_base_no)

    # expected shares
    node_operator_first_rewards_after_third_report = calc_no_rewards(
        nor, no_id=tested_no_id_first, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_second_rewards_after__third_report = calc_no_rewards(
        nor, no_id=tested_no_id_second, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_base_rewards_after__third_report = calc_no_rewards(
        nor, no_id=base_no_id, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )

    # first NO has penalty has a penalty until stuckPenaltyEndTimestamp
    # check shares by report with penalty
    # diff by 1 share because of rounding
    assert almostEqWithDiff(
        node_operator_first_balance_shares_after - node_operator_first_balance_shares_before,
        node_operator_first_rewards_after_third_report // 2,
        1,
    )
    assert almostEqWithDiff(
        node_operator_second_balance_shares_after - node_operator_second_balance_shares_before,
        node_operator_second_rewards_after__third_report // 2,
        1,
    )
    assert almostEqWithDiff(
        node_operator_base_balance_shares_after - node_operator_base_balance_shares_before,
        node_operator_base_rewards_after__third_report,
        1,
    )

    # Check burn shares
    amount_penalty_first_no = node_operator_first_rewards_after_third_report // 2
    amount_penalty_second_no = node_operator_second_rewards_after__third_report // 2
    penalty_shares = amount_penalty_first_no + amount_penalty_second_no
    # diff by 2 share because of rounding
    assert almostEqWithDiff(extra_report_tx.events["StETHBurnRequested"]["amountOfShares"], penalty_shares, 2)

    # NO stats
    assert node_operator_base["stuckPenaltyEndTimestamp"] == 0

    assert node_operator_first["stuckValidatorsCount"] == 0
    assert node_operator_first["totalExitedValidators"] == 7
    assert node_operator_first["refundedValidatorsCount"] == 0
    # first NO has penalty has a penalty until stuckPenaltyEndTimestamp
    assert node_operator_first["stuckPenaltyEndTimestamp"] > chain.time()

    assert node_operator_second["stuckValidatorsCount"] == 2
    assert node_operator_second["totalExitedValidators"] == 5
    assert node_operator_second["refundedValidatorsCount"] == 0
    assert node_operator_second["stuckPenaltyEndTimestamp"] == 0

    assert nor.isOperatorPenalized(tested_no_id_first) == True
    assert nor.isOperatorPenalized(tested_no_id_second) == True
    assert nor.isOperatorPenalized(base_no_id) == False

    # events
    assert extra_report_tx.events["ExitedSigningKeysCountChanged"][0]["nodeOperatorId"] == tested_no_id_first
    assert extra_report_tx.events["ExitedSigningKeysCountChanged"][0]["exitedValidatorsCount"] == 7

    assert extra_report_tx.events["StuckPenaltyStateChanged"][0]["nodeOperatorId"] == tested_no_id_first
    assert extra_report_tx.events["StuckPenaltyStateChanged"][0]["stuckValidatorsCount"] == 0

    # Case 3
    # -- PENALTY_DELAY time passes
    # -- A new report comes in and says "Second" NO still has a stuck of keys
    # -- "First" NO is fine
    # - Wait PENALTY_DELAY time
    # - Send report
    # - Check rewards shares for base NO and tested NO (should be half for "Second" NO)
    # - Check deposits (should be 0 for "Second" NO)
    # - Check burned shares
    # - Check NOs stats

    # sleep PENALTY_DELAY time
    chain.sleep(penalty_delay + 1)
    chain.mine()

    # Clear penalty for first NO after penalty delay
    nor.clearNodeOperatorPenalty(tested_no_id_first, {"from": impersonated_voting})

    # Prepare extra data for report by second NO
    vals_stuck_non_zero = {
        node_operator_gindex(1, tested_no_id_second): 2,
    }
    vals_exited_non_zero = {
        node_operator_gindex(1, tested_no_id_second): 5,
    }
    extra_data = extra_data_service.collect(vals_stuck_non_zero, vals_exited_non_zero, 10, 10)

    # shares before report
    node_operator_first_balance_shares_before = shares_balance(address_first)
    node_operator_second_balance_shares_before = shares_balance(address_second)
    node_operator_base_balance_shares_before = shares_balance(address_base_no)

    # Fourth report - second NO: has stuck 2 keys
    (report_tx, extra_report_tx) = oracle_report(
        exclude_vaults_balances=True,
        extraDataFormat=1,
        extraDataHash=extra_data.data_hash,
        extraDataItemsCount=2,
        extraDataList=extra_data.extra_data,
        numExitedValidatorsByStakingModule=[12],
        stakingModuleIdsWithNewlyExitedValidators=[1],
    )

    node_operator_first = nor.getNodeOperatorSummary(tested_no_id_first)
    node_operator_second = nor.getNodeOperatorSummary(tested_no_id_second)
    node_operator_base = nor.getNodeOperatorSummary(base_no_id)

    # shares after report
    node_operator_first_balance_shares_after = shares_balance(address_first)
    node_operator_second_balance_shares_after = shares_balance(address_second)
    node_operator_base_balance_shares_after = shares_balance(address_base_no)

    # expected shares
    node_operator_first_rewards_after_fourth_report = calc_no_rewards(
        nor, no_id=tested_no_id_first, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_second_rewards_after__fourth_report = calc_no_rewards(
        nor, no_id=tested_no_id_second, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_base_rewards_after__fourth_report = calc_no_rewards(
        nor, no_id=base_no_id, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )

    # Penalty ended for first operator
    # check shares by report with penalty for second NO
    # diff by 1 share because of rounding
    assert almostEqWithDiff(
        node_operator_first_balance_shares_after - node_operator_first_balance_shares_before,
        node_operator_first_rewards_after_fourth_report,
        1,
    )
    assert almostEqWithDiff(
        node_operator_second_balance_shares_after - node_operator_second_balance_shares_before,
        node_operator_second_rewards_after__fourth_report // 2,
        1,
    )
    assert almostEqWithDiff(
        node_operator_base_balance_shares_after - node_operator_base_balance_shares_before,
        node_operator_base_rewards_after__fourth_report,
        1,
    )

    # Check burn shares
    amount_penalty_second_no = node_operator_second_rewards_after__fourth_report // 2
    # diff by 2 share because of rounding
    assert almostEqWithDiff(extra_report_tx.events["StETHBurnRequested"]["amountOfShares"], amount_penalty_second_no, 1)

    assert node_operator_base["stuckPenaltyEndTimestamp"] == 0

    assert node_operator_first["stuckValidatorsCount"] == 0
    assert node_operator_first["totalExitedValidators"] == 7
    assert node_operator_first["refundedValidatorsCount"] == 0
    # Penalty ended for first operator
    assert node_operator_first["stuckPenaltyEndTimestamp"] < chain.time()

    assert node_operator_second["stuckValidatorsCount"] == 2
    assert node_operator_second["totalExitedValidators"] == 5
    assert node_operator_second["refundedValidatorsCount"] == 0
    assert node_operator_second["stuckPenaltyEndTimestamp"] == 0

    assert nor.isOperatorPenalized(tested_no_id_first) == False
    assert nor.isOperatorPenalized(tested_no_id_second) == True
    assert nor.isOperatorPenalized(base_no_id) == False

    # Deposit
    (
        deposited_keys_first_before,
        deposited_keys_second_before,
        deposited_keys_base_before,
        deposited_keys_first_after,
        deposited_keys_second_after,
        deposited_keys_base_after,
    ) = deposit_and_check_keys(nor, tested_no_id_first, tested_no_id_second, base_no_id, 20)

    # check don't change deposited keys for penalized NO (only second NO)
    assert deposited_keys_first_before != deposited_keys_first_after
    assert deposited_keys_second_before == deposited_keys_second_after
    assert deposited_keys_base_before != deposited_keys_base_after

    # Case 4
    # -- Do key refend (redunded == stuck) for X2
    # -- A new report arrives and says that everything remains the same
    # _ Refund 2 keys Second NO
    # - Send report
    # - Check rewards shares for base NO and tested NO (should be half for "Second" NO)
    # - Check burned shares
    # - Check NOs stats

    # # Refund 2 keys Second NO
    contracts.staking_router.updateRefundedValidatorsCount(1, tested_no_id_second, 2, {"from": impersonated_voting})

    # shares before report
    node_operator_first_balance_shares_before = shares_balance(address_first)
    node_operator_second_balance_shares_before = shares_balance(address_second)
    node_operator_base_balance_shares_before = shares_balance(address_base_no)

    # Fifth report
    (report_tx, extra_report_tx) = oracle_report(exclude_vaults_balances=True)

    # shares after report
    node_operator_first_balance_shares_after = shares_balance(address_first)
    node_operator_second_balance_shares_after = shares_balance(address_second)
    node_operator_base_balance_shares_after = shares_balance(address_base_no)

    node_operator_first = nor.getNodeOperatorSummary(tested_no_id_first)
    node_operator_second = nor.getNodeOperatorSummary(tested_no_id_second)
    node_operator_base = nor.getNodeOperatorSummary(base_no_id)

    # expected shares
    node_operator_first_rewards_after_fifth_report = calc_no_rewards(
        nor, no_id=tested_no_id_first, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_second_rewards_after_fifth_report = calc_no_rewards(
        nor, no_id=tested_no_id_second, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_base_rewards_after_fifth_report = calc_no_rewards(
        nor, no_id=base_no_id, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )

    # Penalty only for second operator
    # diff by 1 share because of rounding
    assert almostEqWithDiff(
        node_operator_first_balance_shares_after - node_operator_first_balance_shares_before,
        node_operator_first_rewards_after_fifth_report,
        1,
    )
    assert almostEqWithDiff(
        node_operator_second_balance_shares_after - node_operator_second_balance_shares_before,
        node_operator_second_rewards_after_fifth_report // 2,
        1,
    )
    assert almostEqWithDiff(
        node_operator_base_balance_shares_after - node_operator_base_balance_shares_before,
        node_operator_base_rewards_after_fifth_report,
        1,
    )

    # Check burn shares
    amount_penalty_second_no = node_operator_second_rewards_after_fifth_report // 2
    # diff by 2 share because of rounding
    assert almostEqWithDiff(extra_report_tx.events["StETHBurnRequested"]["amountOfShares"], amount_penalty_second_no, 1)

    assert node_operator_base["stuckPenaltyEndTimestamp"] == 0

    assert node_operator_first["stuckValidatorsCount"] == 0
    assert node_operator_first["totalExitedValidators"] == 7
    assert node_operator_first["refundedValidatorsCount"] == 0
    assert node_operator_first["stuckPenaltyEndTimestamp"] < chain.time()

    assert node_operator_second["stuckValidatorsCount"] == 2
    assert node_operator_second["totalExitedValidators"] == 5
    assert node_operator_second["refundedValidatorsCount"] == 2
    assert node_operator_second["stuckPenaltyEndTimestamp"] > chain.time()

    assert nor.isOperatorPenaltyCleared(tested_no_id_first) == True
    assert nor.isOperatorPenaltyCleared(tested_no_id_second) == False

    # Case 5
    # -- PENALTY_DELAY time passes
    # -- A new report arrives
    # - Wait for penalty delay time
    # - Send report
    # - Check rewards shares for base NO and tested NO (should be full for all NOs)
    # - Check deposits (should be full for all NOs)
    # - Check NOs stats

    # Wait for penalty delay time
    chain.sleep(penalty_delay + 1)
    chain.mine()

    # Clear penalty for second NO after penalty delay
    nor.clearNodeOperatorPenalty(tested_no_id_second, {"from": impersonated_voting})

    # shares before report
    node_operator_first_balance_shares_before = shares_balance(address_first)
    node_operator_second_balance_shares_before = shares_balance(address_second)
    node_operator_base_balance_shares_before = shares_balance(address_base_no)

    # Seventh report
    (report_tx, extra_report_tx) = oracle_report()

    assert nor.isOperatorPenalized(tested_no_id_first) == False
    assert nor.isOperatorPenalized(tested_no_id_second) == False
    assert nor.isOperatorPenalized(base_no_id) == False

    # shares after report
    node_operator_first_balance_shares_after = shares_balance(address_first)
    node_operator_second_balance_shares_after = shares_balance(address_second)
    node_operator_base_balance_shares_after = shares_balance(address_base_no)

    assert nor.isOperatorPenaltyCleared(tested_no_id_first) == True
    assert nor.isOperatorPenaltyCleared(tested_no_id_second) == True

    node_operator_first = nor.getNodeOperatorSummary(tested_no_id_first)
    node_operator_second = nor.getNodeOperatorSummary(tested_no_id_second)

    # expected shares
    node_operator_first_rewards_after_seventh_report = calc_no_rewards(
        nor, no_id=tested_no_id_first, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_second_rewards_after_seventh_report = calc_no_rewards(
        nor, no_id=tested_no_id_second, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_base_rewards_after_seventh_report = calc_no_rewards(
        nor, no_id=base_no_id, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )

    # No penalty
    # diff by 1 share because of rounding
    assert almostEqWithDiff(
        node_operator_first_balance_shares_after - node_operator_first_balance_shares_before,
        node_operator_first_rewards_after_seventh_report,
        1,
    )
    assert almostEqWithDiff(
        node_operator_second_balance_shares_after - node_operator_second_balance_shares_before,
        node_operator_second_rewards_after_seventh_report,
        1,
    )
    assert almostEqWithDiff(
        node_operator_base_balance_shares_after - node_operator_base_balance_shares_before,
        node_operator_base_rewards_after_seventh_report,
        1,
    )

    assert node_operator_first["stuckValidatorsCount"] == 0
    assert node_operator_first["totalExitedValidators"] == 7
    assert node_operator_first["refundedValidatorsCount"] == 0
    assert node_operator_first["stuckPenaltyEndTimestamp"] < chain.time()

    assert node_operator_second["stuckValidatorsCount"] == 2
    assert node_operator_second["totalExitedValidators"] == 5
    assert node_operator_second["refundedValidatorsCount"] == 2
    assert node_operator_second["stuckPenaltyEndTimestamp"] < chain.time()

    # Deposit
    (
        deposited_keys_first_before,
        deposited_keys_second_before,
        deposited_keys_base_before,
        deposited_keys_first_after,
        deposited_keys_second_after,
        deposited_keys_base_after,
    ) = deposit_and_check_keys(nor, tested_no_id_first, tested_no_id_second, base_no_id, 80)

    # check deposit is applied for all NOs
    assert deposited_keys_first_before != deposited_keys_first_after
    assert deposited_keys_second_before != deposited_keys_second_after
    assert deposited_keys_base_before != deposited_keys_base_after

    # Case 6
    # -- SActivate target limit for "First" NO
    # -- Check deposits
    # -- Disable target limit for "First" NO
    # - Set target limit for "First" NO with 0 validators
    # - Check events
    # - Check NO stats
    # - Check deposits (should be 0 for "First" NO)
    # - Disable target limit for "First" NO
    # - Check events
    # - Check NO stats
    # - Check deposits (should be not 0 for "First" NO)

    # Activate target limit
    first_no_summary_before = nor.getNodeOperatorSummary(tested_no_id_first)

    assert first_no_summary_before["depositableValidatorsCount"] > 0

    target_limit_tx = nor.updateTargetValidatorsLimits(tested_no_id_first, True, 0, {"from": lido_dao_staking_router})

    assert target_limit_tx.events["TargetValidatorsCountChanged"][0]["nodeOperatorId"] == tested_no_id_first
    assert target_limit_tx.events["TargetValidatorsCountChanged"][0]["targetValidatorsCount"] == 0

    first_no_summary_after = nor.getNodeOperatorSummary(tested_no_id_first)

    assert first_no_summary_after["depositableValidatorsCount"] == 0
    assert first_no_summary_after["isTargetLimitActive"] == True

    # Deposit
    (
        deposited_keys_first_before,
        deposited_keys_second_before,
        deposited_keys_base_before,
        deposited_keys_first_after,
        deposited_keys_second_after,
        deposited_keys_base_after,
    ) = deposit_and_check_keys(nor, tested_no_id_first, tested_no_id_second, base_no_id, 20)

    # check deposit is not applied for first NO
    assert deposited_keys_first_before == deposited_keys_first_after
    assert deposited_keys_second_before != deposited_keys_second_after
    assert deposited_keys_base_before != deposited_keys_base_after

    # Disable target limit
    target_limit_tx = nor.updateTargetValidatorsLimits(tested_no_id_first, False, 0, {"from": lido_dao_staking_router})

    assert target_limit_tx.events["TargetValidatorsCountChanged"][0]["nodeOperatorId"] == tested_no_id_first

    first_no_summary_after = nor.getNodeOperatorSummary(tested_no_id_first)

    assert first_no_summary_after["depositableValidatorsCount"] > 0
    assert first_no_summary_after["isTargetLimitActive"] == False

    # Deposit
    (
        deposited_keys_first_before,
        deposited_keys_second_before,
        deposited_keys_base_before,
        deposited_keys_first_after,
        deposited_keys_second_after,
        deposited_keys_base_after,
    ) = deposit_and_check_keys(nor, tested_no_id_first, tested_no_id_second, base_no_id, 100)

    # check - deposit not applied to NOs.
    assert deposited_keys_first_before != deposited_keys_first_after
    assert deposited_keys_second_before != deposited_keys_second_after
    assert deposited_keys_base_before != deposited_keys_base_after
