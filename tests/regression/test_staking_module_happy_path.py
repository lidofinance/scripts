import pytest
from web3 import Web3
import eth_abi
from brownie import chain, ZERO_ADDRESS, web3, interface

from utils.test.extra_data import (
    ExtraDataService,
)
from utils.test.helpers import shares_balance, ETH, almostEqWithDiff
from utils.test.oracle_report_helpers import (
    oracle_report,
)
from utils.config import contracts, STAKING_ROUTER, EASYTRACK_EVMSCRIPT_EXECUTOR
from utils.test.node_operators_helpers import node_operator_gindex
from utils.test.simple_dvt_helpers import fill_simple_dvt_ops_vetted_keys


@pytest.fixture(scope="function")
def impersonate_es_executor(accounts):
    return accounts.at(EASYTRACK_EVMSCRIPT_EXECUTOR, force=True)


@pytest.fixture(scope="function")
def impersonated_voting(accounts):
    return accounts.at(contracts.voting.address, force=True)


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


def deposit_and_check_keys(staking_module, first_no_id, second_no_id, base_no_id, keys_count, impersonated_voting):
    for op_index in (first_no_id, second_no_id, base_no_id):
        no = staking_module.getNodeOperator(op_index, True)
        if not no["active"]:
            continue
        staking_module.setNodeOperatorStakingLimit(op_index, no["totalDepositedValidators"] + 10, {"from": impersonated_voting})

    deposited_keys_first_before = staking_module.getNodeOperatorSummary(first_no_id)["totalDepositedValidators"]
    deposited_keys_second_before = staking_module.getNodeOperatorSummary(second_no_id)["totalDepositedValidators"]
    deposited_keys_base_before = staking_module.getNodeOperatorSummary(base_no_id)["totalDepositedValidators"]
    validators_before = contracts.lido.getBeaconStat().dict()["depositedValidators"]

    module_total_deposited_keys_before = staking_module.getStakingModuleSummary()["totalDepositedValidators"]

    tx = contracts.lido.deposit(keys_count, staking_module.module_id, "0x", {"from": contracts.deposit_security_module.address})

    validators_after = contracts.lido.getBeaconStat().dict()["depositedValidators"]
    module_total_deposited_keys_after = staking_module.getStakingModuleSummary()["totalDepositedValidators"]

    just_deposited = validators_after - validators_before
    print("---------", just_deposited)
    if just_deposited:
        assert tx.events["DepositedValidatorsChanged"]["depositedValidators"] == validators_after
        assert tx.events["Unbuffered"]["amount"] == just_deposited * ETH(32)
        assert module_total_deposited_keys_before + just_deposited == module_total_deposited_keys_after

    deposited_keys_first_after = staking_module.getNodeOperatorSummary(first_no_id)["totalDepositedValidators"]
    deposited_keys_second_after = staking_module.getNodeOperatorSummary(second_no_id)["totalDepositedValidators"]
    deposited_keys_base_after = staking_module.getNodeOperatorSummary(base_no_id)["totalDepositedValidators"]

    return (
        deposited_keys_first_before,
        deposited_keys_second_before,
        deposited_keys_base_before,
        deposited_keys_first_after,
        deposited_keys_second_after,
        deposited_keys_base_after,
    )


def filter_transfer_logs(logs, transfer_topic):
    return list(filter(lambda l: l["topics"][0] == transfer_topic, logs))


def parse_exited_signing_keys_count_changed_logs(logs):
    res = []
    for l in logs:
        res.append(
            {
                "nodeOperatorId": eth_abi.decode_abi(["uint256"], l["topics"][1])[0],
                "exitedValidatorsCount": eth_abi.decode_single("uint256", bytes.fromhex(l["data"][2:])),
            }
        )
    return res


def parse_stuck_penalty_state_changed_logs(logs):
    res = []
    for l in logs:
        data = eth_abi.decode(["uint256","uint256","uint256"], bytes.fromhex(l["data"][2:]))
        res.append(
            {
                "nodeOperatorId": eth_abi.decode_abi(["uint256"], l["topics"][1])[0],
                "stuckValidatorsCount": data[0],
                "refundedValidatorsCount": data[1],
                "stuckPenaltyEndTimestamp": data[2],
            }
        )
    return res


def parse_target_validators_count_changed(logs):
    res = []
    for l in logs:
        res.append(
            {
                "nodeOperatorId": eth_abi.decode_abi(["uint256"], l["topics"][1])[0],
                "targetValidatorsCount": eth_abi.decode_single("uint256", bytes.fromhex(l["data"][2:])),
            }
        )
    return res


def module_happy_path(staking_module, extra_data_service, impersonated_voting, impersonated_executor, eth_whale):
    nor_exited_count, _, _ = contracts.staking_router.getStakingModuleSummary(staking_module.module_id)

    contracts.staking_router.grantRole(
        Web3.keccak(text="STAKING_MODULE_MANAGE_ROLE"),
        impersonated_voting,
        {"from": contracts.agent.address},
    )

    contracts.acl.grantPermission(
        impersonated_voting,
        staking_module,
        Web3.keccak(text="STAKING_ROUTER_ROLE"),
        {"from": impersonated_voting},
    )

    contracts.lido.submit(ZERO_ADDRESS, {"from": eth_whale, "amount": ETH(75000)})

    base_no_id, tested_no_id_first, tested_no_id_second = staking_module.testing_node_operator_ids

    no_amount = staking_module.getNodeOperatorsCount()
    for op_index in range(no_amount):
        no = staking_module.getNodeOperator(op_index, True)
        if not no["active"]:
            continue
        staking_module.setNodeOperatorStakingLimit(op_index, no["totalDepositedValidators"], {"from": impersonated_executor})

    increase_limit(staking_module, tested_no_id_first, tested_no_id_second, base_no_id, 3, impersonated_executor)

    penalty_delay = staking_module.getStuckPenaltyDelay()

    node_operator_first = staking_module.getNodeOperatorSummary(tested_no_id_first)
    address_first = staking_module.getNodeOperator(tested_no_id_first, False)["rewardAddress"]
    node_operator_first_balance_shares_before = shares_balance(address_first)

    node_operator_second = staking_module.getNodeOperatorSummary(tested_no_id_second)
    address_second = staking_module.getNodeOperator(tested_no_id_second, False)["rewardAddress"]
    node_operator_second_balance_shares_before = shares_balance(address_second)

    node_operator_base = staking_module.getNodeOperatorSummary(base_no_id)
    address_base_no = staking_module.getNodeOperator(base_no_id, False)["rewardAddress"]
    node_operator_base_balance_shares_before = shares_balance(address_base_no)

    # First report - base empty report
    (report_tx, extra_report_tx) = oracle_report(exclude_vaults_balances=True)

    node_operator_first_balance_shares_after = shares_balance(address_first)
    node_operator_second_balance_shares_after = shares_balance(address_second)
    node_operator_base_balance_shares_after = shares_balance(address_base_no)

    # expected shares
    node_operator_first_rewards_after_first_report = calc_no_rewards(
        staking_module, no_id=tested_no_id_first, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_second_rewards_after_first_report = calc_no_rewards(
        staking_module, no_id=tested_no_id_second, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_base_rewards_after_first_report = calc_no_rewards(
        staking_module, no_id=base_no_id, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )

    # check shares by empty report
    assert almostEqWithDiff(
        node_operator_first_balance_shares_after - node_operator_first_balance_shares_before,
        node_operator_first_rewards_after_first_report,
        1,
    )
    assert almostEqWithDiff(
        node_operator_second_balance_shares_after - node_operator_second_balance_shares_before,
        node_operator_second_rewards_after_first_report,
        1,
    )
    assert almostEqWithDiff(
        node_operator_base_balance_shares_after - node_operator_base_balance_shares_before,
        node_operator_base_rewards_after_first_report,
        1,
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
        node_operator_gindex(staking_module.module_id, tested_no_id_first): 2,
        node_operator_gindex(staking_module.module_id, tested_no_id_second): 2,
    }
    vals_exited_non_zero = {
        node_operator_gindex(staking_module.module_id, tested_no_id_first): 5,
        node_operator_gindex(staking_module.module_id, tested_no_id_second): 5,
    }
    extra_data = extra_data_service.collect(vals_stuck_non_zero, vals_exited_non_zero, 10, 10)

    # shares before report
    node_operator_first_balance_shares_before = shares_balance(address_first)
    node_operator_second_balance_shares_before = shares_balance(address_second)
    node_operator_base_balance_shares_before = shares_balance(address_base_no)

    deposit_and_check_keys(staking_module, tested_no_id_first, tested_no_id_second, base_no_id, 30, impersonated_executor)

    # Second report - first NO and second NO has stuck/exited
    (report_tx, extra_report_tx) = oracle_report(
        exclude_vaults_balances=True,
        extraDataFormat=1,
        extraDataHash=extra_data.data_hash,
        extraDataItemsCount=2,
        extraDataList=extra_data.extra_data,
        numExitedValidatorsByStakingModule=[nor_exited_count + 10],
        stakingModuleIdsWithNewlyExitedValidators=[staking_module.module_id],
    )

    # shares after report
    node_operator_first = staking_module.getNodeOperatorSummary(tested_no_id_first)
    node_operator_second = staking_module.getNodeOperatorSummary(tested_no_id_second)
    node_operator_base = staking_module.getNodeOperatorSummary(base_no_id)

    # expected shares
    node_operator_first_rewards_after_second_report = calc_no_rewards(
        staking_module, no_id=tested_no_id_first, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_second_rewards_after_second_report = calc_no_rewards(
        staking_module, no_id=tested_no_id_second, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_base_rewards_after_second_report = calc_no_rewards(
        staking_module, no_id=base_no_id, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
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

    assert extra_report_tx.events["StETHBurnRequested"]["amountOfShares"] >= penalty_shares

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

    assert staking_module.isOperatorPenalized(tested_no_id_first)
    assert staking_module.isOperatorPenalized(tested_no_id_second)
    assert not staking_module.isOperatorPenalized(base_no_id)

    # Events
    exited_signing_keys_count_events = parse_exited_signing_keys_count_changed_logs(
        filter_transfer_logs(extra_report_tx.logs, web3.keccak(text="ExitedSigningKeysCountChanged(uint256,uint256)"))
    )
    assert exited_signing_keys_count_events[0]["nodeOperatorId"] == tested_no_id_first
    assert exited_signing_keys_count_events[0]["exitedValidatorsCount"] == 5

    assert exited_signing_keys_count_events[1]["nodeOperatorId"] == tested_no_id_second
    assert exited_signing_keys_count_events[1]["exitedValidatorsCount"] == 5

    stuck_penalty_state_changed_events = parse_stuck_penalty_state_changed_logs(
        filter_transfer_logs(extra_report_tx.logs, web3.keccak(text="StuckPenaltyStateChanged(uint256,uint256,uint256,uint256)"))
    )
    assert stuck_penalty_state_changed_events[0]["nodeOperatorId"] == tested_no_id_first
    assert stuck_penalty_state_changed_events[0]["stuckValidatorsCount"] == 2

    assert stuck_penalty_state_changed_events[1]["nodeOperatorId"] == tested_no_id_second
    assert stuck_penalty_state_changed_events[1]["stuckValidatorsCount"] == 2

    # Deposit keys
    (
        deposited_keys_first_before,
        deposited_keys_second_before,
        deposited_keys_base_before,
        deposited_keys_first_after,
        deposited_keys_second_after,
        deposited_keys_base_after,
    ) = deposit_and_check_keys(staking_module, tested_no_id_first, tested_no_id_second, base_no_id, 50, impersonated_executor)

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
        node_operator_gindex(staking_module.module_id, tested_no_id_first): 0,
    }
    vals_exited_non_zero = {
        node_operator_gindex(staking_module.module_id, tested_no_id_first): 7,
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
        numExitedValidatorsByStakingModule=[nor_exited_count + 12],
        stakingModuleIdsWithNewlyExitedValidators=[staking_module.module_id],
    )

    node_operator_first = staking_module.getNodeOperatorSummary(tested_no_id_first)
    node_operator_second = staking_module.getNodeOperatorSummary(tested_no_id_second)
    node_operator_base = staking_module.getNodeOperatorSummary(base_no_id)

    # shares after report
    node_operator_first_balance_shares_after = shares_balance(address_first)
    node_operator_second_balance_shares_after = shares_balance(address_second)
    node_operator_base_balance_shares_after = shares_balance(address_base_no)

    # expected shares
    node_operator_first_rewards_after_third_report = calc_no_rewards(
        staking_module, no_id=tested_no_id_first, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_second_rewards_after__third_report = calc_no_rewards(
        staking_module, no_id=tested_no_id_second, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_base_rewards_after__third_report = calc_no_rewards(
        staking_module, no_id=base_no_id, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
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
    # TODO: Fix below check when nor contains other penalized node operators
    # assert almostEqWithDiff(extra_report_tx.events["StETHBurnRequested"]["amountOfShares"], penalty_shares, 2)
    assert extra_report_tx.events["StETHBurnRequested"]["amountOfShares"] >= penalty_shares

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

    assert staking_module.isOperatorPenalized(tested_no_id_first) == True
    assert staking_module.isOperatorPenalized(tested_no_id_second) == True
    assert staking_module.isOperatorPenalized(base_no_id) == False

    # events
    exited_signing_keys_count_events = parse_exited_signing_keys_count_changed_logs(
        filter_transfer_logs(extra_report_tx.logs, web3.keccak(text="ExitedSigningKeysCountChanged(uint256,uint256)"))
    )
    assert exited_signing_keys_count_events[0]["nodeOperatorId"] == tested_no_id_first
    assert exited_signing_keys_count_events[0]["exitedValidatorsCount"] == 7

    stuck_penalty_state_changed_events = parse_stuck_penalty_state_changed_logs(
        filter_transfer_logs(extra_report_tx.logs, web3.keccak(text="StuckPenaltyStateChanged(uint256,uint256,uint256,uint256)"))
    )
    assert stuck_penalty_state_changed_events[0]["nodeOperatorId"] == tested_no_id_first
    assert stuck_penalty_state_changed_events[0]["stuckValidatorsCount"] == 0

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
    staking_module.clearNodeOperatorPenalty(tested_no_id_first, {"from": impersonated_voting})

    # Prepare extra data for report by second NO
    vals_stuck_non_zero = {
        node_operator_gindex(staking_module.module_id, tested_no_id_second): 2,
    }
    vals_exited_non_zero = {
        node_operator_gindex(staking_module.module_id, tested_no_id_second): 5,
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
        numExitedValidatorsByStakingModule=[nor_exited_count + 12],
        stakingModuleIdsWithNewlyExitedValidators=[staking_module.module_id],
    )

    node_operator_first = staking_module.getNodeOperatorSummary(tested_no_id_first)
    node_operator_second = staking_module.getNodeOperatorSummary(tested_no_id_second)
    node_operator_base = staking_module.getNodeOperatorSummary(base_no_id)

    # shares after report
    node_operator_first_balance_shares_after = shares_balance(address_first)
    node_operator_second_balance_shares_after = shares_balance(address_second)
    node_operator_base_balance_shares_after = shares_balance(address_base_no)

    # expected shares
    node_operator_first_rewards_after_fourth_report = calc_no_rewards(
        staking_module, no_id=tested_no_id_first, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_second_rewards_after__fourth_report = calc_no_rewards(
        staking_module, no_id=tested_no_id_second, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_base_rewards_after__fourth_report = calc_no_rewards(
        staking_module, no_id=base_no_id, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
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
    # TODO: Fix below check when nor contains other penalized node operators
    # assert almostEqWithDiff(extra_report_tx.events["StETHBurnRequested"]["amountOfShares"], amount_penalty_second_no, 1)
    assert extra_report_tx.events["StETHBurnRequested"]["amountOfShares"] >= amount_penalty_second_no

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

    assert not staking_module.isOperatorPenalized(tested_no_id_first)
    assert staking_module.isOperatorPenalized(tested_no_id_second)
    assert not staking_module.isOperatorPenalized(base_no_id)

    # Deposit
    (
        deposited_keys_first_before,
        deposited_keys_second_before,
        deposited_keys_base_before,
        deposited_keys_first_after,
        deposited_keys_second_after,
        deposited_keys_base_after,
    ) = deposit_and_check_keys(staking_module, tested_no_id_first, tested_no_id_second, base_no_id, 50, impersonated_voting)

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
    contracts.staking_router.updateRefundedValidatorsCount(staking_module.module_id, tested_no_id_second, 2, {"from": impersonated_voting})

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

    node_operator_first = staking_module.getNodeOperatorSummary(tested_no_id_first)
    node_operator_second = staking_module.getNodeOperatorSummary(tested_no_id_second)
    node_operator_base = staking_module.getNodeOperatorSummary(base_no_id)

    # expected shares
    node_operator_first_rewards_after_fifth_report = calc_no_rewards(
        staking_module, no_id=tested_no_id_first, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_second_rewards_after_fifth_report = calc_no_rewards(
        staking_module, no_id=tested_no_id_second, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_base_rewards_after_fifth_report = calc_no_rewards(
        staking_module, no_id=base_no_id, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
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
    # TODO: Fix below check when nor contains other penalized node operators
    # assert almostEqWithDiff(extra_report_tx.events["StETHBurnRequested"]["amountOfShares"], amount_penalty_second_no, 1)
    assert extra_report_tx.events["StETHBurnRequested"]["amountOfShares"] >= amount_penalty_second_no

    assert node_operator_base["stuckPenaltyEndTimestamp"] == 0

    assert node_operator_first["stuckValidatorsCount"] == 0
    assert node_operator_first["totalExitedValidators"] == 7
    assert node_operator_first["refundedValidatorsCount"] == 0
    assert node_operator_first["stuckPenaltyEndTimestamp"] < chain.time()

    assert node_operator_second["stuckValidatorsCount"] == 2
    assert node_operator_second["totalExitedValidators"] == 5
    assert node_operator_second["refundedValidatorsCount"] == 2
    assert node_operator_second["stuckPenaltyEndTimestamp"] > chain.time()

    assert staking_module.isOperatorPenaltyCleared(tested_no_id_first) == True
    assert staking_module.isOperatorPenaltyCleared(tested_no_id_second) == False

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
    staking_module.clearNodeOperatorPenalty(tested_no_id_second, {"from": impersonated_voting})

    # shares before report
    node_operator_first_balance_shares_before = shares_balance(address_first)
    node_operator_second_balance_shares_before = shares_balance(address_second)
    node_operator_base_balance_shares_before = shares_balance(address_base_no)

    # Seventh report
    (report_tx, extra_report_tx) = oracle_report()

    assert not staking_module.isOperatorPenalized(tested_no_id_first)
    assert not staking_module.isOperatorPenalized(tested_no_id_second)
    assert not staking_module.isOperatorPenalized(base_no_id)

    # shares after report
    node_operator_first_balance_shares_after = shares_balance(address_first)
    node_operator_second_balance_shares_after = shares_balance(address_second)
    node_operator_base_balance_shares_after = shares_balance(address_base_no)

    assert staking_module.isOperatorPenaltyCleared(tested_no_id_first)
    assert staking_module.isOperatorPenaltyCleared(tested_no_id_second)

    node_operator_first = staking_module.getNodeOperatorSummary(tested_no_id_first)
    node_operator_second = staking_module.getNodeOperatorSummary(tested_no_id_second)

    # expected shares
    node_operator_first_rewards_after_seventh_report = calc_no_rewards(
        staking_module, no_id=tested_no_id_first, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_second_rewards_after_seventh_report = calc_no_rewards(
        staking_module, no_id=tested_no_id_second, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    node_operator_base_rewards_after_seventh_report = calc_no_rewards(
        staking_module, no_id=base_no_id, shares_minted_as_fees=report_tx.events["TokenRebased"]["sharesMintedAsFees"]
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
    ) = deposit_and_check_keys(staking_module, tested_no_id_first, tested_no_id_second, base_no_id, 50, impersonated_voting)

    # check deposit is applied for all NOs
    assert deposited_keys_first_before != deposited_keys_first_after
    assert deposited_keys_second_before != deposited_keys_second_after
    assert deposited_keys_base_before != deposited_keys_base_after

    for op_index in (tested_no_id_first, tested_no_id_second, base_no_id):
        no = staking_module.getNodeOperator(op_index, True)
        staking_module.setNodeOperatorStakingLimit(op_index, no["totalDepositedValidators"] + 10, {"from": impersonated_voting})

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
    first_no_summary_before = staking_module.getNodeOperatorSummary(tested_no_id_first)

    assert first_no_summary_before["depositableValidatorsCount"] > 0

    target_limit_tx = staking_module.updateTargetValidatorsLimits(tested_no_id_first, True, 0, {"from": STAKING_ROUTER})

    target_validators_count_changed_events = parse_target_validators_count_changed(
        filter_transfer_logs(target_limit_tx.logs, web3.keccak(text="TargetValidatorsCountChanged(uint256,uint256)"))
    )
    assert target_validators_count_changed_events[0]["nodeOperatorId"] == tested_no_id_first
    assert target_validators_count_changed_events[0]["targetValidatorsCount"] == 0

    first_no_summary_after = staking_module.getNodeOperatorSummary(tested_no_id_first)

    assert first_no_summary_after["depositableValidatorsCount"] == 0
    assert first_no_summary_after["isTargetLimitActive"]

    # Deposit
    (
        deposited_keys_first_before,
        deposited_keys_second_before,
        deposited_keys_base_before,
        deposited_keys_first_after,
        deposited_keys_second_after,
        deposited_keys_base_after,
    ) = deposit_and_check_keys(staking_module, tested_no_id_first, tested_no_id_second, base_no_id, 50, impersonated_voting)

    # check deposit is not applied for first NO
    assert deposited_keys_first_before == deposited_keys_first_after
    assert deposited_keys_second_before != deposited_keys_second_after
    assert deposited_keys_base_before != deposited_keys_base_after

    # Disable target limit
    target_limit_tx = staking_module.updateTargetValidatorsLimits(tested_no_id_first, False, 0, {"from": STAKING_ROUTER})
    target_validators_count_changed_events = parse_target_validators_count_changed(
        filter_transfer_logs(target_limit_tx.logs, web3.keccak(text="TargetValidatorsCountChanged(uint256,uint256)"))
    )
    assert target_validators_count_changed_events[0]["nodeOperatorId"] == tested_no_id_first

    first_no_summary_after = staking_module.getNodeOperatorSummary(tested_no_id_first)

    assert first_no_summary_after["depositableValidatorsCount"] > 0
    assert not first_no_summary_after["isTargetLimitActive"]

    # Deposit
    (
        deposited_keys_first_before,
        deposited_keys_second_before,
        deposited_keys_base_before,
        deposited_keys_first_after,
        deposited_keys_second_after,
        deposited_keys_base_after,
    ) = deposit_and_check_keys(staking_module, tested_no_id_first, tested_no_id_second, base_no_id, 50, impersonated_voting)

    # check - deposit not applied to NOs.
    assert deposited_keys_first_before != deposited_keys_first_after
    assert deposited_keys_second_before != deposited_keys_second_after
    assert deposited_keys_base_before != deposited_keys_base_after


def test_node_operator_registry(impersonated_voting, eth_whale):
    nor = contracts.node_operators_registry
    nor.module_id = 1
    nor.testing_node_operator_ids = [23, 20, 28]
    module_happy_path(nor, ExtraDataService(), impersonated_voting, impersonated_voting, eth_whale)


def test_sdvt(impersonated_voting, impersonate_es_executor, stranger, eth_whale):
    sdvt = contracts.simple_dvt
    sdvt.module_id = 2
    sdvt.testing_node_operator_ids = [0, 1, 2]
    fill_simple_dvt_ops_vetted_keys(stranger, 3, 100)
    fill_simple_dvt_ops_vetted_keys(stranger, 3, 200)
    fill_simple_dvt_ops_vetted_keys(stranger, 3, 300)
    module_happy_path(sdvt, ExtraDataService(), impersonated_voting, impersonate_es_executor, eth_whale)
