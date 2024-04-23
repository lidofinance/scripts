import pytest
from web3 import Web3
import eth_abi
from brownie import chain, ZERO_ADDRESS, web3

from utils.test.extra_data import (
    ExtraDataService,
)
from utils.test.helpers import shares_balance, ETH, almostEqWithDiff
from utils.test.oracle_report_helpers import (
    oracle_report,
)
from utils.config import contracts, STAKING_ROUTER, EASYTRACK_EVMSCRIPT_EXECUTOR
from utils.test.node_operators_helpers import node_operator_gindex
from utils.test.simple_dvt_helpers import fill_simple_dvt_ops_keys


STAKING_ROUTER_ROLE = Web3.keccak(text="STAKING_ROUTER_ROLE")
STAKING_MODULE_MANAGE_ROLE = Web3.keccak(text="STAKING_MODULE_MANAGE_ROLE")
SET_NODE_OPERATOR_LIMIT_ROLE = Web3.keccak(text="SET_NODE_OPERATOR_LIMIT_ROLE")


@pytest.fixture(scope="function")
def impersonated_voting(accounts):
    return accounts.at(contracts.voting.address, force=True)


def calc_module_reward_shares(module_id, shares_minted_as_fees):
    distribution = contracts.staking_router.getStakingRewardsDistribution()
    module_idx = distribution[1].index(module_id)
    return distribution[2][module_idx] * shares_minted_as_fees // distribution[3]


def calc_no_rewards(nor, no_id, minted_shares):
    operator_summary = nor.getNodeOperatorSummary(no_id)
    module_summary = nor.getStakingModuleSummary()

    operator_total_active_keys = (
        operator_summary["totalDepositedValidators"] - operator_summary["totalExitedValidators"]
    )
    module_total_active_keys = module_summary["totalDepositedValidators"] - module_summary["totalExitedValidators"]

    return minted_shares * operator_total_active_keys // module_total_active_keys


def set_staking_limit(nor, ops_ids, keys_count, impersonated_voting):
    for op_index in ops_ids:
        no = nor.getNodeOperator(op_index, False)
        if not no["active"]:
            continue
        cur_deposited_keys = no["totalDepositedValidators"]
        cur_vetted_keys = no["totalVettedValidators"]
        new_vetted_keys = cur_deposited_keys + keys_count
        print(
            f"Set staking limit for OP: {op_index} (total deposited: {cur_deposited_keys}) from: {cur_vetted_keys} to: {new_vetted_keys}"
        )
        nor.setNodeOperatorStakingLimit(op_index, new_vetted_keys, {"from": impersonated_voting})


def deposit_and_check_keys(nor, first_id, second_id, third_id, keys_count, impersonated_voting):
    # increase limit by 10 keys
    set_staking_limit(nor, (first_id, second_id, third_id), 10, impersonated_voting)

    deposited_keys_first_before = nor.getNodeOperatorSummary(first_id)["totalDepositedValidators"]
    deposited_keys_second_before = nor.getNodeOperatorSummary(second_id)["totalDepositedValidators"]
    deposited_keys_base_before = nor.getNodeOperatorSummary(third_id)["totalDepositedValidators"]
    validators_before = contracts.lido.getBeaconStat().dict()["depositedValidators"]

    module_total_deposited_keys_before = nor.getStakingModuleSummary()["totalDepositedValidators"]

    print(f"Deposit {keys_count} keys for module {nor.module_id}")
    tx = contracts.lido.deposit(keys_count, nor.module_id, "0x", {"from": contracts.deposit_security_module.address})

    validators_after = contracts.lido.getBeaconStat().dict()["depositedValidators"]
    module_total_deposited_keys_after = nor.getStakingModuleSummary()["totalDepositedValidators"]

    just_deposited = validators_after - validators_before
    print("Deposited:", just_deposited)
    if just_deposited:
        assert tx.events["DepositedValidatorsChanged"]["depositedValidators"] == validators_after
        assert tx.events["Unbuffered"]["amount"] == just_deposited * ETH(32)
        assert module_total_deposited_keys_before + just_deposited == module_total_deposited_keys_after

    deposited_keys_first_after = nor.getNodeOperatorSummary(first_id)["totalDepositedValidators"]
    deposited_keys_second_after = nor.getNodeOperatorSummary(second_id)["totalDepositedValidators"]
    deposited_keys_base_after = nor.getNodeOperatorSummary(third_id)["totalDepositedValidators"]

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
                "nodeOperatorId": eth_abi.decode(["uint256"], l["topics"][1])[0],
                "exitedValidatorsCount": eth_abi.decode(["uint256"], l["data"]),
            }
        )
    return res


def parse_stuck_penalty_state_changed_logs(logs):
    res = []
    for l in logs:
        data = eth_abi.decode(["uint256", "uint256", "uint256"], l["data"])
        res.append(
            {
                "nodeOperatorId": eth_abi.decode(["uint256"], l["topics"][1])[0],
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
                "nodeOperatorId": eth_abi.decode(["uint256"], l["topics"][1])[0],
                "targetValidatorsCount": eth_abi.decode(["uint256"], l["data"]),
            }
        )
    return res


def module_happy_path(staking_module, extra_data_service, impersonated_voting, eth_whale):
    nor_exited_count, _, _ = contracts.staking_router.getStakingModuleSummary(staking_module.module_id)

    # all_modules = contracts.staking_router.getStakingModules()

    contracts.staking_router.grantRole(
        STAKING_MODULE_MANAGE_ROLE,
        impersonated_voting,
        {"from": contracts.agent.address},
    )

    contracts.acl.grantPermission(
        impersonated_voting,
        staking_module,
        STAKING_ROUTER_ROLE,
        {"from": impersonated_voting},
    )

    contracts.acl.grantPermission(
        impersonated_voting,
        staking_module,
        SET_NODE_OPERATOR_LIMIT_ROLE,
        {"from": impersonated_voting},
    )

    contracts.lido.submit(ZERO_ADDRESS, {"from": eth_whale, "amount": ETH(150_000)})

    print("Reset staking limit for all OPs...")
    no_amount = staking_module.getNodeOperatorsCount()
    set_staking_limit(staking_module, range(no_amount), 0, impersonated_voting)

    no3_id, no1_id, no2_id = staking_module.testing_node_operator_ids

    deposit_and_check_keys(staking_module, no1_id, no2_id, no3_id, 30, impersonated_voting)

    penalty_delay = staking_module.getStuckPenaltyDelay()

    no1_summary = staking_module.getNodeOperatorSummary(no1_id)
    no1_reward_address = staking_module.getNodeOperator(no1_id, False)["rewardAddress"]
    no1_balance_shares_before = shares_balance(no1_reward_address)

    no2_summary = staking_module.getNodeOperatorSummary(no2_id)
    no2_reward_address = staking_module.getNodeOperator(no2_id, False)["rewardAddress"]
    no2_balance_shares_before = shares_balance(no2_reward_address)

    no3_summary = staking_module.getNodeOperatorSummary(no3_id)
    no3_reward_address = staking_module.getNodeOperator(no3_id, False)["rewardAddress"]
    no3_balance_shares_before = shares_balance(no3_reward_address)

    # First report - base empty report
    (report_tx, extra_report_tx) = oracle_report(exclude_vaults_balances=True)

    no1_balance_shares_after = shares_balance(no1_reward_address)
    no2_balance_shares_after = shares_balance(no2_reward_address)
    no3_balance_shares_after = shares_balance(no3_reward_address)

    minted_share = calc_module_reward_shares(
        staking_module.module_id, report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    no1_rewards_after_first_report = calc_no_rewards(staking_module, no_id=no1_id, minted_shares=minted_share)
    no2_rewards_after_first_report = calc_no_rewards(staking_module, no_id=no2_id, minted_shares=minted_share)
    no3_rewards_after_first_report = calc_no_rewards(staking_module, no_id=no3_id, minted_shares=minted_share)

    # check shares by empty report
    assert almostEqWithDiff(
        no1_balance_shares_after - no1_balance_shares_before,
        no1_rewards_after_first_report,
        1,
    )
    assert almostEqWithDiff(
        no2_balance_shares_after - no2_balance_shares_before,
        no2_rewards_after_first_report,
        1,
    )
    assert almostEqWithDiff(
        no3_balance_shares_after - no3_balance_shares_before,
        no3_rewards_after_first_report,
        1,
    )

    # Case 1
    # --- operator "1st" had 5 keys (exited), and 2 keys got stuck (stuck)
    # --- operator "2nd" had 5 keys (exited), and 2 keys got stuck (stuck)
    # - Send report
    # - Check rewards shares for "3d" NO and tested NO (should be half of expected)
    # - Check deposits (should be 0 for penalized NOs)
    # - Check burned shares
    # - Check NOs stats
    # - Check Report events

    # Prepare extra data
    vals_stuck_non_zero = {
        node_operator_gindex(staking_module.module_id, no1_id): 2,
        node_operator_gindex(staking_module.module_id, no2_id): 2,
    }
    vals_exited_non_zero = {
        node_operator_gindex(staking_module.module_id, no1_id): 5,
        node_operator_gindex(staking_module.module_id, no2_id): 5,
    }
    extra_data = extra_data_service.collect(vals_stuck_non_zero, vals_exited_non_zero, 10, 10)

    # shares before report
    no1_balance_shares_before = shares_balance(no1_reward_address)
    no2_balance_shares_before = shares_balance(no2_reward_address)
    no3_balance_shares_before = shares_balance(no3_reward_address)

    deposit_and_check_keys(staking_module, no1_id, no2_id, no3_id, 30, impersonated_voting)

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
    no1_summary = staking_module.getNodeOperatorSummary(no1_id)
    no2_summary = staking_module.getNodeOperatorSummary(no2_id)
    no3_summary = staking_module.getNodeOperatorSummary(no3_id)

    # expected shares
    minted_share = calc_module_reward_shares(
        staking_module.module_id, report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    no1_rewards_after_second_report = calc_no_rewards(staking_module, no_id=no1_id, minted_shares=minted_share)
    no2_rewards_after_second_report = calc_no_rewards(staking_module, no_id=no2_id, minted_shares=minted_share)
    no3_rewards_after_second_report = calc_no_rewards(staking_module, no_id=no3_id, minted_shares=minted_share)

    no1_balance_shares_after = shares_balance(no1_reward_address)
    no2_balance_shares_after = shares_balance(no2_reward_address)
    no3_balance_shares_after = shares_balance(no3_reward_address)

    # check shares by report with penalty
    assert almostEqWithDiff(
        no1_balance_shares_after - no1_balance_shares_before,
        no1_rewards_after_second_report // 2,
        1,
    )
    assert almostEqWithDiff(
        no2_balance_shares_after - no2_balance_shares_before,
        no2_rewards_after_second_report // 2,
        1,
    )
    assert almostEqWithDiff(
        no3_balance_shares_after - no3_balance_shares_before,
        no3_rewards_after_second_report,
        1,
    )

    # Check burn shares
    no1_amount_penalty = no1_rewards_after_second_report // 2
    no2_amount_penalty = no2_rewards_after_second_report // 2
    penalty_shares = no1_amount_penalty + no2_amount_penalty

    assert extra_report_tx.events["StETHBurnRequested"]["amountOfShares"] >= penalty_shares

    # NO stats
    assert no1_summary["stuckValidatorsCount"] == 2
    assert no1_summary["totalExitedValidators"] == 5
    assert no1_summary["refundedValidatorsCount"] == 0
    assert no1_summary["stuckPenaltyEndTimestamp"] == 0

    assert no2_summary["stuckValidatorsCount"] == 2
    assert no2_summary["totalExitedValidators"] == 5
    assert no2_summary["refundedValidatorsCount"] == 0
    assert no2_summary["stuckPenaltyEndTimestamp"] == 0

    assert no3_summary["stuckValidatorsCount"] == 0
    assert no3_summary["totalExitedValidators"] == 0
    assert no3_summary["refundedValidatorsCount"] == 0
    assert no3_summary["stuckPenaltyEndTimestamp"] == 0

    assert staking_module.isOperatorPenalized(no1_id)
    assert staking_module.isOperatorPenalized(no2_id)
    assert not staking_module.isOperatorPenalized(no3_id)

    # Events
    exited_signing_keys_count_events = parse_exited_signing_keys_count_changed_logs(
        filter_transfer_logs(extra_report_tx.logs, web3.keccak(text="ExitedSigningKeysCountChanged(uint256,uint256)"))
    )
    assert exited_signing_keys_count_events[0]["nodeOperatorId"] == no1_id
    assert exited_signing_keys_count_events[0]["exitedValidatorsCount"][0] == 5

    assert exited_signing_keys_count_events[1]["nodeOperatorId"] == no2_id
    assert exited_signing_keys_count_events[1]["exitedValidatorsCount"][0] == 5

    stuck_penalty_state_changed_events = parse_stuck_penalty_state_changed_logs(
        filter_transfer_logs(
            extra_report_tx.logs, web3.keccak(text="StuckPenaltyStateChanged(uint256,uint256,uint256,uint256)")
        )
    )
    assert stuck_penalty_state_changed_events[0]["nodeOperatorId"] == no1_id
    assert stuck_penalty_state_changed_events[0]["stuckValidatorsCount"] == 2

    assert stuck_penalty_state_changed_events[1]["nodeOperatorId"] == no2_id
    assert stuck_penalty_state_changed_events[1]["stuckValidatorsCount"] == 2

    # Deposit keys
    (
        no1_deposited_keys_before,
        no2_deposited_keys_before,
        no3_deposited_keys_before,
        no1_deposited_keys_after,
        no2_deposited_keys_after,
        no3_deposited_keys_after,
    ) = deposit_and_check_keys(staking_module, no1_id, no2_id, no3_id, 50, impersonated_voting)

    # check don't change deposited keys for penalized NO
    assert no1_deposited_keys_before == no1_deposited_keys_after
    assert no2_deposited_keys_before == no2_deposited_keys_after
    assert no3_deposited_keys_before != no3_deposited_keys_after

    # Case 2
    # --- "1st" NO exited the keys (stuck == 0, exited increased by the number of stacks)
    # --- BUT the penalty still affects both
    # - Send report
    # - Check rewards shares for NO3 and tested NO (should be half of expected)
    # - Check burned shares
    # - Check NOs stats
    # - Check Report events

    # Prepare extra data - first node operator has exited 2 + 5 keys an stuck 0
    vals_stuck_non_zero = {
        node_operator_gindex(staking_module.module_id, no1_id): 0,
    }
    vals_exited_non_zero = {
        node_operator_gindex(staking_module.module_id, no1_id): 7,
    }
    extra_data = extra_data_service.collect(vals_stuck_non_zero, vals_exited_non_zero, 10, 10)

    # shares before report
    no1_balance_shares_before = shares_balance(no1_reward_address)
    no2_balance_shares_before = shares_balance(no2_reward_address)
    no3_balance_shares_before = shares_balance(no3_reward_address)

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

    no1_summary = staking_module.getNodeOperatorSummary(no1_id)
    no2_summary = staking_module.getNodeOperatorSummary(no2_id)
    no3_summary = staking_module.getNodeOperatorSummary(no3_id)

    # shares after report
    no1_balance_shares_after = shares_balance(no1_reward_address)
    no2_balance_shares_after = shares_balance(no2_reward_address)
    no3_balance_shares_after = shares_balance(no3_reward_address)

    # expected shares
    minted_share = calc_module_reward_shares(
        staking_module.module_id, report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    no1_rewards_after_third_report = calc_no_rewards(staking_module, no_id=no1_id, minted_shares=minted_share)
    no2_rewards_after_third_report = calc_no_rewards(staking_module, no_id=no2_id, minted_shares=minted_share)
    no3_rewards_after_third_report = calc_no_rewards(staking_module, no_id=no3_id, minted_shares=minted_share)

    # first NO has penalty has a penalty until stuckPenaltyEndTimestamp
    # check shares by report with penalty
    # diff by 1 share because of rounding
    assert almostEqWithDiff(
        no1_balance_shares_after - no1_balance_shares_before,
        no1_rewards_after_third_report // 2,
        2,
    )
    assert almostEqWithDiff(
        no2_balance_shares_after - no2_balance_shares_before,
        no2_rewards_after_third_report // 2,
        2,
    )
    assert almostEqWithDiff(
        no3_balance_shares_after - no3_balance_shares_before,
        no3_rewards_after_third_report,
        4,
    )

    # Check burn shares
    no1_amount_penalty = no1_rewards_after_third_report // 2
    no2_amount_penalty = no2_rewards_after_third_report // 2
    penalty_shares = no1_amount_penalty + no2_amount_penalty
    # diff by 2 share because of rounding
    # TODO: Fix below check when nor contains other penalized node operators
    # assert almostEqWithDiff(extra_report_tx.events["StETHBurnRequested"]["amountOfShares"], penalty_shares, 2)
    assert extra_report_tx.events["StETHBurnRequested"]["amountOfShares"] >= penalty_shares

    # NO stats
    assert no3_summary["stuckPenaltyEndTimestamp"] == 0

    assert no1_summary["stuckValidatorsCount"] == 0
    assert no1_summary["totalExitedValidators"] == 7
    assert no1_summary["refundedValidatorsCount"] == 0
    # first NO has penalty has a penalty until stuckPenaltyEndTimestamp
    assert no1_summary["stuckPenaltyEndTimestamp"] > chain.time()

    assert no2_summary["stuckValidatorsCount"] == 2
    assert no2_summary["totalExitedValidators"] == 5
    assert no2_summary["refundedValidatorsCount"] == 0
    assert no2_summary["stuckPenaltyEndTimestamp"] == 0

    assert staking_module.isOperatorPenalized(no1_id) == True
    assert staking_module.isOperatorPenalized(no2_id) == True
    assert staking_module.isOperatorPenalized(no3_id) == False

    # events
    exited_signing_keys_count_events = parse_exited_signing_keys_count_changed_logs(
        filter_transfer_logs(extra_report_tx.logs, web3.keccak(text="ExitedSigningKeysCountChanged(uint256,uint256)"))
    )
    assert exited_signing_keys_count_events[0]["nodeOperatorId"] == no1_id
    assert exited_signing_keys_count_events[0]["exitedValidatorsCount"][0] == 7

    stuck_penalty_state_changed_events = parse_stuck_penalty_state_changed_logs(
        filter_transfer_logs(
            extra_report_tx.logs, web3.keccak(text="StuckPenaltyStateChanged(uint256,uint256,uint256,uint256)")
        )
    )
    assert stuck_penalty_state_changed_events[0]["nodeOperatorId"] == no1_id
    assert stuck_penalty_state_changed_events[0]["stuckValidatorsCount"] == 0

    # Case 3
    # -- PENALTY_DELAY time passes
    # -- A new report comes in and says "2nd" NO still has a stuck of keys
    # -- "1st" NO is fine
    # - Wait PENALTY_DELAY time
    # - Send report
    # - Check rewards shares for "3d" NO and tested NO (should be half for "2nd" NO)
    # - Check deposits (should be 0 for "2nd" NO)
    # - Check burned shares
    # - Check NOs stats

    # sleep PENALTY_DELAY time
    chain.sleep(penalty_delay + 1)
    chain.mine()

    # Clear penalty for first NO after penalty delay
    staking_module.clearNodeOperatorPenalty(no1_id, {"from": impersonated_voting})

    # Prepare extra data for report by second NO
    vals_stuck_non_zero = {
        node_operator_gindex(staking_module.module_id, no2_id): 2,
    }
    vals_exited_non_zero = {
        node_operator_gindex(staking_module.module_id, no2_id): 5,
    }
    extra_data = extra_data_service.collect(vals_stuck_non_zero, vals_exited_non_zero, 10, 10)

    # shares before report
    no1_balance_shares_before = shares_balance(no1_reward_address)
    no2_balance_shares_before = shares_balance(no2_reward_address)
    no3_balance_shares_before = shares_balance(no3_reward_address)

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

    no1_summary = staking_module.getNodeOperatorSummary(no1_id)
    no2_summary = staking_module.getNodeOperatorSummary(no2_id)
    no3_summary = staking_module.getNodeOperatorSummary(no3_id)

    # shares after report
    no1_balance_shares_after = shares_balance(no1_reward_address)
    no2_balance_shares_after = shares_balance(no2_reward_address)
    no3_balance_shares_after = shares_balance(no3_reward_address)

    # expected shares
    minted_share = calc_module_reward_shares(
        staking_module.module_id, report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    no1_rewards_after_fourth_report = calc_no_rewards(staking_module, no_id=no1_id, minted_shares=minted_share)
    no2_rewards_after_fourth_report = calc_no_rewards(staking_module, no_id=no2_id, minted_shares=minted_share)
    no3_rewards_after_fourth_report = calc_no_rewards(staking_module, no_id=no3_id, minted_shares=minted_share)

    # Penalty ended for first operator
    # check shares by report with penalty for second NO
    # diff by 1 share because of rounding
    assert almostEqWithDiff(
        no1_balance_shares_after - no1_balance_shares_before,
        no1_rewards_after_fourth_report,
        2,
    )
    assert almostEqWithDiff(
        no2_balance_shares_after - no2_balance_shares_before,
        no2_rewards_after_fourth_report // 2,
        2,
    )
    assert almostEqWithDiff(
        no3_balance_shares_after - no3_balance_shares_before,
        no3_rewards_after_fourth_report,
        4,
    )

    # Check burn shares
    no2_amount_penalty = no2_rewards_after_fourth_report // 2
    # diff by 2 share because of rounding
    # TODO: Fix below check when nor contains other penalized node operators
    # assert almostEqWithDiff(extra_report_tx.events["StETHBurnRequested"]["amountOfShares"], amount_penalty_second_no, 1)
    assert extra_report_tx.events["StETHBurnRequested"]["amountOfShares"] >= no2_amount_penalty

    assert no3_summary["stuckPenaltyEndTimestamp"] == 0

    assert no1_summary["stuckValidatorsCount"] == 0
    assert no1_summary["totalExitedValidators"] == 7
    assert no1_summary["refundedValidatorsCount"] == 0
    # Penalty ended for first operator
    assert no1_summary["stuckPenaltyEndTimestamp"] < chain.time()

    assert no2_summary["stuckValidatorsCount"] == 2
    assert no2_summary["totalExitedValidators"] == 5
    assert no2_summary["refundedValidatorsCount"] == 0
    assert no2_summary["stuckPenaltyEndTimestamp"] == 0

    assert not staking_module.isOperatorPenalized(no1_id)
    assert staking_module.isOperatorPenalized(no2_id)
    assert not staking_module.isOperatorPenalized(no3_id)

    # Deposit
    (
        no1_deposited_keys_before,
        no2_deposited_keys_before,
        no3_deposited_keys_before,
        no1_deposited_keys_after,
        no2_deposited_keys_after,
        no3_deposited_keys_after,
    ) = deposit_and_check_keys(staking_module, no1_id, no2_id, no3_id, 50, impersonated_voting)

    # check don't change deposited keys for penalized NO (only second NO)
    assert no1_deposited_keys_before != no1_deposited_keys_after
    assert no2_deposited_keys_before == no2_deposited_keys_after
    assert no3_deposited_keys_before != no3_deposited_keys_after

    # Case 4
    # -- Do key refend (redunded == stuck) for X2
    # -- A new report arrives and says that everything remains the same
    # _ Refund 2 keys Second NO
    # - Send report
    # - Check rewards shares for "3d" NO and tested NO (should be half for "2nd" NO)
    # - Check burned shares
    # - Check NOs stats

    # # Refund 2 keys Second NO
    contracts.staking_router.updateRefundedValidatorsCount(
        staking_module.module_id, no2_id, 2, {"from": impersonated_voting}
    )

    # shares before report
    no1_balance_shares_before = shares_balance(no1_reward_address)
    no2_balance_shares_before = shares_balance(no2_reward_address)
    no3_balance_shares_before = shares_balance(no3_reward_address)

    # Fifth report
    (report_tx, extra_report_tx) = oracle_report(exclude_vaults_balances=True)

    # shares after report
    no1_balance_shares_after = shares_balance(no1_reward_address)
    no2_balance_shares_after = shares_balance(no2_reward_address)
    no3_balance_shares_after = shares_balance(no3_reward_address)

    no1_summary = staking_module.getNodeOperatorSummary(no1_id)
    no2_summary = staking_module.getNodeOperatorSummary(no2_id)
    no3_summary = staking_module.getNodeOperatorSummary(no3_id)

    # expected shares
    minted_share = calc_module_reward_shares(
        staking_module.module_id, report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    no1_rewards_after_fifth_report = calc_no_rewards(staking_module, no_id=no1_id, minted_shares=minted_share)
    no2_rewards_after_fifth_report = calc_no_rewards(staking_module, no_id=no2_id, minted_shares=minted_share)
    no3_rewards_after_fifth_report = calc_no_rewards(staking_module, no_id=no3_id, minted_shares=minted_share)

    # Penalty only for second operator
    # diff by 1 share because of rounding
    assert almostEqWithDiff(
        no1_balance_shares_after - no1_balance_shares_before,
        no1_rewards_after_fifth_report,
        2,
    )
    assert almostEqWithDiff(
        no2_balance_shares_after - no2_balance_shares_before,
        no2_rewards_after_fifth_report // 2,
        2,
    )
    assert almostEqWithDiff(
        no3_balance_shares_after - no3_balance_shares_before,
        no3_rewards_after_fifth_report,
        4,
    )

    # Check burn shares
    no2_amount_penalty = no2_rewards_after_fifth_report // 2
    # diff by 2 share because of rounding
    # TODO: Fix below check when nor contains other penalized node operators
    # assert almostEqWithDiff(extra_report_tx.events["StETHBurnRequested"]["amountOfShares"], amount_penalty_second_no, 1)
    assert extra_report_tx.events["StETHBurnRequested"]["amountOfShares"] >= no2_amount_penalty

    assert no3_summary["stuckPenaltyEndTimestamp"] == 0

    assert no1_summary["stuckValidatorsCount"] == 0
    assert no1_summary["totalExitedValidators"] == 7
    assert no1_summary["refundedValidatorsCount"] == 0
    assert no1_summary["stuckPenaltyEndTimestamp"] < chain.time()

    assert no2_summary["stuckValidatorsCount"] == 2
    assert no2_summary["totalExitedValidators"] == 5
    assert no2_summary["refundedValidatorsCount"] == 2
    assert no2_summary["stuckPenaltyEndTimestamp"] > chain.time()

    assert staking_module.isOperatorPenaltyCleared(no1_id) == True
    assert staking_module.isOperatorPenaltyCleared(no2_id) == False

    # Case 5
    # -- PENALTY_DELAY time passes
    # -- A new report arrives
    # - Wait for penalty delay time
    # - Send report
    # - Check rewards shares for "3d" NO and tested NO (should be full for all NOs)
    # - Check deposits (should be full for all NOs)
    # - Check NOs stats

    # Wait for penalty delay time
    chain.sleep(penalty_delay + 1)
    chain.mine()

    # Clear penalty for second NO after penalty delay
    staking_module.clearNodeOperatorPenalty(no2_id, {"from": impersonated_voting})

    # shares before report
    no1_balance_shares_before = shares_balance(no1_reward_address)
    no2_balance_shares_before = shares_balance(no2_reward_address)
    no3_balance_shares_before = shares_balance(no3_reward_address)

    # Seventh report
    (report_tx, extra_report_tx) = oracle_report()

    assert not staking_module.isOperatorPenalized(no1_id)
    assert not staking_module.isOperatorPenalized(no2_id)
    assert not staking_module.isOperatorPenalized(no3_id)

    # shares after report
    no1_balance_shares_after = shares_balance(no1_reward_address)
    no2_balance_shares_after = shares_balance(no2_reward_address)
    no3_balance_shares_after = shares_balance(no3_reward_address)

    assert staking_module.isOperatorPenaltyCleared(no1_id)
    assert staking_module.isOperatorPenaltyCleared(no2_id)

    no1_summary = staking_module.getNodeOperatorSummary(no1_id)
    no2_summary = staking_module.getNodeOperatorSummary(no2_id)

    # expected shares
    minted_share = calc_module_reward_shares(
        staking_module.module_id, report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    )
    no1_rewards_after_sixth_report = calc_no_rewards(staking_module, no_id=no1_id, minted_shares=minted_share)
    no2_rewards_after_sixth_report = calc_no_rewards(staking_module, no_id=no2_id, minted_shares=minted_share)
    no3_rewards_after_sixth_report = calc_no_rewards(staking_module, no_id=no3_id, minted_shares=minted_share)

    # No penalty
    # diff by 1 share because of rounding
    assert almostEqWithDiff(
        no1_balance_shares_after - no1_balance_shares_before,
        no1_rewards_after_sixth_report,
        2,
    )
    assert almostEqWithDiff(
        no2_balance_shares_after - no2_balance_shares_before,
        no2_rewards_after_sixth_report,
        2,
    )
    assert almostEqWithDiff(
        no3_balance_shares_after - no3_balance_shares_before,
        no3_rewards_after_sixth_report,
        4,
    )

    assert no1_summary["stuckValidatorsCount"] == 0
    assert no1_summary["totalExitedValidators"] == 7
    assert no1_summary["refundedValidatorsCount"] == 0
    assert no1_summary["stuckPenaltyEndTimestamp"] < chain.time()

    assert no2_summary["stuckValidatorsCount"] == 2
    assert no2_summary["totalExitedValidators"] == 5
    assert no2_summary["refundedValidatorsCount"] == 2
    assert no2_summary["stuckPenaltyEndTimestamp"] < chain.time()

    # Deposit
    (
        no1_deposited_keys_before,
        no2_deposited_keys_before,
        no3_deposited_keys_before,
        no1_deposited_keys_after,
        no2_deposited_keys_after,
        no3_deposited_keys_after,
    ) = deposit_and_check_keys(staking_module, no1_id, no2_id, no3_id, 50, impersonated_voting)

    # check deposit is applied for all NOs
    assert no1_deposited_keys_before != no1_deposited_keys_after
    assert no2_deposited_keys_before != no2_deposited_keys_after
    assert no3_deposited_keys_before != no3_deposited_keys_after

    for op_index in (no1_id, no2_id, no3_id):
        no = staking_module.getNodeOperator(op_index, False)
        staking_module.setNodeOperatorStakingLimit(
            op_index, no["totalDepositedValidators"] + 10, {"from": impersonated_voting}
        )

    # Case 6
    # -- SActivate target limit for "1st" NO
    # -- Check deposits
    # -- Disable target limit for "1st" NO
    # - Set target limit for "1st" NO with 0 validators
    # - Check events
    # - Check NO stats
    # - Check deposits (should be 0 for "1st" NO)
    # - Disable target limit for "1st" NO
    # - Check events
    # - Check NO stats
    # - Check deposits (should be not 0 for "1st" NO)

    # Activate target limit
    first_no_summary_before = staking_module.getNodeOperatorSummary(no1_id)

    assert first_no_summary_before["depositableValidatorsCount"] > 0

    target_limit_tx = staking_module.updateTargetValidatorsLimits(no1_id, True, 0, {"from": STAKING_ROUTER})

    target_validators_count_changed_events = parse_target_validators_count_changed(
        filter_transfer_logs(target_limit_tx.logs, web3.keccak(text="TargetValidatorsCountChanged(uint256,uint256)"))
    )
    assert target_validators_count_changed_events[0]["nodeOperatorId"] == no1_id
    assert target_validators_count_changed_events[0]["targetValidatorsCount"][0] == 0

    first_no_summary_after = staking_module.getNodeOperatorSummary(no1_id)

    assert first_no_summary_after["depositableValidatorsCount"] == 0
    assert first_no_summary_after["isTargetLimitActive"]

    # Deposit
    (
        no1_deposited_keys_before,
        no2_deposited_keys_before,
        no3_deposited_keys_before,
        no1_deposited_keys_after,
        no2_deposited_keys_after,
        no3_deposited_keys_after,
    ) = deposit_and_check_keys(staking_module, no1_id, no2_id, no3_id, 50, impersonated_voting)

    # check deposit is not applied for first NO
    assert no1_deposited_keys_before == no1_deposited_keys_after
    assert no2_deposited_keys_before != no2_deposited_keys_after
    assert no3_deposited_keys_before != no3_deposited_keys_after

    # Disable target limit
    target_limit_tx = staking_module.updateTargetValidatorsLimits(no1_id, False, 0, {"from": STAKING_ROUTER})
    target_validators_count_changed_events = parse_target_validators_count_changed(
        filter_transfer_logs(target_limit_tx.logs, web3.keccak(text="TargetValidatorsCountChanged(uint256,uint256)"))
    )
    assert target_validators_count_changed_events[0]["nodeOperatorId"] == no1_id

    first_no_summary_after = staking_module.getNodeOperatorSummary(no1_id)

    assert first_no_summary_after["depositableValidatorsCount"] > 0
    assert not first_no_summary_after["isTargetLimitActive"]

    # Deposit
    (
        no1_deposited_keys_before,
        no2_deposited_keys_before,
        no3_deposited_keys_before,
        no1_deposited_keys_after,
        no2_deposited_keys_after,
        no3_deposited_keys_after,
    ) = deposit_and_check_keys(staking_module, no1_id, no2_id, no3_id, 50, impersonated_voting)

    # check - deposit not applied to NOs.
    assert no1_deposited_keys_before != no1_deposited_keys_after
    assert no2_deposited_keys_before != no2_deposited_keys_after
    assert no3_deposited_keys_before != no3_deposited_keys_after


@pytest.mark.skip(
    "TODO: fix the test assumptions about the state of the chain (no exited validators, depositable ETH amount)"
)
def test_node_operator_registry(impersonated_voting, eth_whale):
    nor = contracts.node_operators_registry
    nor.module_id = 1
    nor.testing_node_operator_ids = [35, 36, 37]
    module_happy_path(nor, ExtraDataService(), impersonated_voting, eth_whale)


def test_sdvt(impersonated_voting, stranger, eth_whale):
    sdvt = contracts.simple_dvt
    sdvt.module_id = 2
    sdvt.testing_node_operator_ids = [0, 1, 2]
    fill_simple_dvt_ops_keys(stranger, 3, 100)

    module_happy_path(sdvt, ExtraDataService(), impersonated_voting, eth_whale)
