import pytest
from web3 import Web3
import eth_abi
from brownie import web3

from utils.staking_module import calc_module_reward_shares
from utils.test.extra_data import (
    ExtraDataService,
)
from utils.test.helpers import shares_balance, ETH
from utils.test.oracle_report_helpers import (
    oracle_report,
)
from utils.config import contracts, STAKING_ROUTER
from utils.test.node_operators_helpers import distribute_reward, node_operator_gindex
from utils.test.simple_dvt_helpers import fill_simple_dvt_ops_keys
from utils.test.staking_router_helpers import set_staking_module_status, StakingModuleStatus
from utils.test.deposits_helpers import fill_deposit_buffer

STAKING_ROUTER_ROLE = Web3.keccak(text="STAKING_ROUTER_ROLE")
STAKING_MODULE_MANAGE_ROLE = Web3.keccak(text="STAKING_MODULE_MANAGE_ROLE")
SET_NODE_OPERATOR_LIMIT_ROLE = Web3.keccak(text="SET_NODE_OPERATOR_LIMIT_ROLE")
STAKING_CONTROL_ROLE = Web3.keccak(text="STAKING_CONTROL_ROLE")

@pytest.fixture(scope="function")
def impersonated_agent(accounts):
    return accounts.at(contracts.agent.address, force=True)


def calc_no_rewards(nor, no_id, minted_shares):
    operator_summary = nor.getNodeOperatorSummary(no_id)
    module_summary = nor.getStakingModuleSummary()

    operator_total_active_keys = (
        operator_summary["totalDepositedValidators"] - operator_summary["totalExitedValidators"]
    )
    module_total_active_keys = module_summary["totalDepositedValidators"] - module_summary["totalExitedValidators"]

    return minted_shares * operator_total_active_keys // module_total_active_keys


def set_staking_limit(nor, ops_ids, keys_count, impersonated_agent):
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
        nor.setNodeOperatorStakingLimit(op_index, new_vetted_keys, {"from": impersonated_agent})


def deposit_and_check_keys(nor, first_id, second_id, third_id, keys_count, impersonated_agent):
    # increase limit by 10 keys
    set_staking_limit(nor, (first_id, second_id, third_id), 10, impersonated_agent)

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




def module_happy_path(staking_module, extra_data_service, impersonated_agent, stranger, helpers):
    nor_exited_count, _, _ = contracts.staking_router.getStakingModuleSummary(staking_module.module_id)

    # all_modules = contracts.staking_router.getStakingModules()

    contracts.staking_router.grantRole(
        STAKING_MODULE_MANAGE_ROLE,
        impersonated_agent,
        {"from": contracts.agent.address},
    )

    contracts.acl.grantPermission(
        impersonated_agent,
        staking_module,
        STAKING_ROUTER_ROLE,
        {"from": impersonated_agent},
    )

    contracts.acl.grantPermission(
        impersonated_agent,
        staking_module,
        SET_NODE_OPERATOR_LIMIT_ROLE,
        {"from": impersonated_agent},
    )

    contracts.acl.grantPermission(
        impersonated_agent,
        contracts.lido,
        STAKING_CONTROL_ROLE,
        {"from": impersonated_agent}
    )

    # pausing csm due to very high amount of keys in the queue
    csm_module_id = 3
    set_staking_module_status(csm_module_id, StakingModuleStatus.Stopped)

    # fill buffer enough to deposit 310 keys
    fill_deposit_buffer(310)

    print("Reset staking limit for all OPs...")
    no_amount = staking_module.getNodeOperatorsCount()
    set_staking_limit(staking_module, range(no_amount), 0, impersonated_agent)

    no3_id, no1_id, no2_id = staking_module.testing_node_operator_ids

    deposit_and_check_keys(staking_module, no1_id, no2_id, no3_id, 30, impersonated_agent)

    no1_reward_address = staking_module.getNodeOperator(no1_id, False)["rewardAddress"]
    no1_balance_shares_before = shares_balance(no1_reward_address)

    no2_reward_address = staking_module.getNodeOperator(no2_id, False)["rewardAddress"]
    no2_balance_shares_before = shares_balance(no2_reward_address)

    no3_reward_address = staking_module.getNodeOperator(no3_id, False)["rewardAddress"]
    no3_balance_shares_before = shares_balance(no3_reward_address)

    # Some stETH "dust" (small units of shares) may settle on the registry contract, so it has to be considered in the calculations:
    # https://github.com/lidofinance/core/blob/297b530793de3b162beaba8c8e1812c9f2441391/contracts/0.4.24/nos/NodeOperatorsRegistry.sol#L1329
    module_shares_dust = shares_balance(staking_module)

    # First report - base empty report
    (report_tx, extra_report_tx_list) = oracle_report(exclude_vaults_balances=True)
    distribute_reward(staking_module, stranger.address)

    no1_balance_shares_after = shares_balance(no1_reward_address)
    no2_balance_shares_after = shares_balance(no2_reward_address)
    no3_balance_shares_after = shares_balance(no3_reward_address)

    minted_share = (
        calc_module_reward_shares(staking_module.module_id, report_tx.events["TokenRebased"]["sharesMintedAsFees"])
        + module_shares_dust
    )
    no1_rewards_after_first_report = calc_no_rewards(staking_module, no_id=no1_id, minted_shares=minted_share)
    no2_rewards_after_first_report = calc_no_rewards(staking_module, no_id=no2_id, minted_shares=minted_share)
    no3_rewards_after_first_report = calc_no_rewards(staking_module, no_id=no3_id, minted_shares=minted_share)

    # check shares by empty report
    assert no1_balance_shares_after - no1_balance_shares_before == no1_rewards_after_first_report
    assert no2_balance_shares_after - no2_balance_shares_before == no2_rewards_after_first_report
    assert no3_balance_shares_after - no3_balance_shares_before == no3_rewards_after_first_report

    # Test Case: Basic Exit Handling
    # --- operator "1st" had 5 keys (exited)
    # --- operator "2nd" had 5 keys (exited)
    # - Send report
    # - Check rewards shares distribution
    # - Check NOs stats
    # - Check Report events

    # Prepare extra data
    vals_exited_non_zero = {
        node_operator_gindex(staking_module.module_id, no1_id): 5,
        node_operator_gindex(staking_module.module_id, no2_id): 5,
    }
    extra_data = extra_data_service.collect(vals_exited_non_zero, 10, 10)

    # shares before report
    no1_balance_shares_before = shares_balance(no1_reward_address)
    no2_balance_shares_before = shares_balance(no2_reward_address)
    no3_balance_shares_before = shares_balance(no3_reward_address)

    deposit_and_check_keys(staking_module, no1_id, no2_id, no3_id, 30, impersonated_agent)

    module_shares_dust = shares_balance(staking_module)
    # Second report - first NO and second NO has exited
    (report_tx, extra_report_tx_list) = oracle_report(
        exclude_vaults_balances=True,
        extraDataFormat=1,
        extraDataHashList=extra_data.extra_data_hash_list,
        extraDataItemsCount=extra_data.items_count,
        extraDataList=extra_data.extra_data_list,
        numExitedValidatorsByStakingModule=[nor_exited_count + 10],
        stakingModuleIdsWithNewlyExitedValidators=[staking_module.module_id],
    )
    distribute_reward(staking_module, stranger.address)

    # shares after report
    no1_summary = staking_module.getNodeOperatorSummary(no1_id)
    no2_summary = staking_module.getNodeOperatorSummary(no2_id)
    no3_summary = staking_module.getNodeOperatorSummary(no3_id)

    # expected shares
    minted_share = (
        calc_module_reward_shares(staking_module.module_id, report_tx.events["TokenRebased"]["sharesMintedAsFees"])
        + module_shares_dust
    )
    no1_rewards_after_second_report = calc_no_rewards(staking_module, no_id=no1_id, minted_shares=minted_share)
    no2_rewards_after_second_report = calc_no_rewards(staking_module, no_id=no2_id, minted_shares=minted_share)
    no3_rewards_after_second_report = calc_no_rewards(staking_module, no_id=no3_id, minted_shares=minted_share)

    no1_balance_shares_after = shares_balance(no1_reward_address)
    no2_balance_shares_after = shares_balance(no2_reward_address)
    no3_balance_shares_after = shares_balance(no3_reward_address)

    assert no1_balance_shares_after - no1_balance_shares_before == no1_rewards_after_second_report
    assert no2_balance_shares_after - no2_balance_shares_before == no2_rewards_after_second_report
    assert no3_balance_shares_after - no3_balance_shares_before == no3_rewards_after_second_report

    # NO stats
    assert no1_summary["totalExitedValidators"] == 5
    assert no2_summary["totalExitedValidators"] == 5
    assert no3_summary["totalExitedValidators"] == 0

    # Events
    exited_signing_keys_count_events = parse_exited_signing_keys_count_changed_logs(
        filter_transfer_logs(extra_report_tx_list[0].logs, web3.keccak(text="ExitedSigningKeysCountChanged(uint256,uint256)"))
    )
    assert exited_signing_keys_count_events[0]["nodeOperatorId"] == no1_id
    assert exited_signing_keys_count_events[0]["exitedValidatorsCount"][0] == 5

    assert exited_signing_keys_count_events[1]["nodeOperatorId"] == no2_id
    assert exited_signing_keys_count_events[1]["exitedValidatorsCount"][0] == 5

    # Deposit keys
    deposit_and_check_keys(staking_module, no1_id, no2_id, no3_id, 50, impersonated_agent)

    for op_index in (no1_id, no2_id, no3_id):
        no = staking_module.getNodeOperator(op_index, False)
        staking_module.setNodeOperatorStakingLimit(
            op_index, no["totalDepositedValidators"] + 10, {"from": impersonated_agent}
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

    target_limit_tx = staking_module.updateTargetValidatorsLimits['uint256,uint256,uint256'](no1_id, 1, 0, {"from": STAKING_ROUTER})

    helpers.assert_single_event_named(
            "TargetValidatorsCountChanged",
            target_limit_tx,
            {"nodeOperatorId": no1_id, "targetValidatorsCount": 0, "targetLimitMode": 1},
        )

    first_no_summary_after = staking_module.getNodeOperatorSummary(no1_id)

    assert first_no_summary_after["depositableValidatorsCount"] == 0
    assert first_no_summary_after["targetLimitMode"] == 1

    fill_deposit_buffer(50, heuristic=100)
    # Deposit
    (
        no1_deposited_keys_before,
        no2_deposited_keys_before,
        no3_deposited_keys_before,
        no1_deposited_keys_after,
        no2_deposited_keys_after,
        no3_deposited_keys_after,
    ) = deposit_and_check_keys(staking_module, no1_id, no2_id, no3_id, 50, impersonated_agent)

    # check deposit is not applied for first NO
    assert no1_deposited_keys_before == no1_deposited_keys_after
    assert no2_deposited_keys_before != no2_deposited_keys_after
    assert no3_deposited_keys_before != no3_deposited_keys_after

    # Disable target limit
    target_limit_tx = staking_module.updateTargetValidatorsLimits['uint256,uint256,uint256'](no1_id, 0, 0, {"from": STAKING_ROUTER})

    helpers.assert_single_event_named(
        "TargetValidatorsCountChanged",
        target_limit_tx,
        {"nodeOperatorId": no1_id, "targetValidatorsCount": 0, "targetLimitMode": 0},
    )

    first_no_summary_after = staking_module.getNodeOperatorSummary(no1_id)

    assert first_no_summary_after["depositableValidatorsCount"] > 0
    assert first_no_summary_after["targetLimitMode"] == 0

    # Deposit
    (
        no1_deposited_keys_before,
        no2_deposited_keys_before,
        no3_deposited_keys_before,
        no1_deposited_keys_after,
        no2_deposited_keys_after,
        no3_deposited_keys_after,
    ) = deposit_and_check_keys(staking_module, no1_id, no2_id, no3_id, 50, impersonated_agent)

    # check - deposit not applied to NOs.
    assert no1_deposited_keys_before != no1_deposited_keys_after
    assert no2_deposited_keys_before != no2_deposited_keys_after
    assert no3_deposited_keys_before != no3_deposited_keys_after


@pytest.mark.skip(
    "TODO: fix the test assumptions about the state of the chain (no exited validators, depositable ETH amount)"
)
def test_node_operator_registry(impersonated_agent, stranger, helpers):
    nor = contracts.node_operators_registry
    nor.module_id = 1
    nor.testing_node_operator_ids = [35, 36, 37]
    module_happy_path(nor, ExtraDataService(), impersonated_agent, stranger, helpers)


def test_sdvt(impersonated_agent, stranger, helpers):
    sdvt = contracts.simple_dvt
    sdvt.module_id = 2
    sdvt.testing_node_operator_ids = [0, 1, 2]
    fill_simple_dvt_ops_keys(stranger, 3, 100)

    module_happy_path(sdvt, ExtraDataService(), impersonated_agent, stranger, helpers)
