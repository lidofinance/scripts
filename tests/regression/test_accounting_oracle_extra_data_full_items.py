from math import ceil

import pytest
from brownie import convert, web3
from brownie.network.account import Account
from brownie.network.web3 import Web3

from utils.test.csm_helpers import csm_add_node_operator, csm_upload_keys, fill_csm_operators_with_keys
from utils.test.deposits_helpers import fill_deposit_buffer
from utils.test.helpers import shares_balance, almostEqWithDiff
from utils.test.keys_helpers import random_pubkeys_batch, random_signatures_batch
from utils.test.oracle_report_helpers import oracle_report
from utils.test.node_operators_helpers import distribute_reward

from utils.config import MAX_ITEMS_PER_EXTRA_DATA_TRANSACTION, MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM
from utils.config import contracts
from utils.test.staking_router_helpers import increase_staking_module_share

NEW_KEYS_PER_OPERATOR = 2

@pytest.fixture(scope="module")
def agent_eoa(accounts):
    return accounts.at(contracts.agent.address, force=True)


@pytest.fixture(scope="module")
def evm_script_executor_eoa(accounts):
    return accounts.at(contracts.easy_track.evmScriptExecutor(), force=True)


@pytest.fixture(scope="module")
def nor(interface):
    return interface.NodeOperatorsRegistry(contracts.node_operators_registry.address)


@pytest.fixture(scope="module")
def sdvt(interface):
    return interface.SimpleDVT(contracts.simple_dvt.address)


@pytest.fixture(scope="module")
def prepare_modules(nor, sdvt, agent_eoa, evm_script_executor_eoa):
    # Fill NOR with new operators and keys
    (nor_count_before, added_nor_operators_count) = fill_nor_with_old_and_new_operators(
        nor,
        agent_eoa,
        evm_script_executor_eoa,
        NEW_KEYS_PER_OPERATOR,
        MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM,
    )

    (sdvt_count_before, added_sdvt_operators_count) = fill_nor_with_old_and_new_operators(
        sdvt,
        agent_eoa,
        evm_script_executor_eoa,
        NEW_KEYS_PER_OPERATOR,
        MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM,
    )

    # Fill CSM with new operators and keys
    csm_operators_count = MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM
    csm_count_before, added_csm_operators_count = fill_csm_operators_with_keys(csm_operators_count,
                                                                               NEW_KEYS_PER_OPERATOR)

    # Deposit for new added keys from buffer
    keys_for_sdvt = (added_sdvt_operators_count * NEW_KEYS_PER_OPERATOR) + (sdvt_count_before * NEW_KEYS_PER_OPERATOR)
    keys_for_nor = (added_nor_operators_count * NEW_KEYS_PER_OPERATOR) + (nor_count_before * NEW_KEYS_PER_OPERATOR)
    keys_for_csm = (added_csm_operators_count * NEW_KEYS_PER_OPERATOR) + (csm_count_before * NEW_KEYS_PER_OPERATOR)
    deposit_buffer_for_keys(
        contracts.staking_router,
        keys_for_nor,
        keys_for_sdvt,
        keys_for_csm,
    )


@pytest.mark.parametrize("nor_stuck_items", [1, 0])
@pytest.mark.parametrize("nor_exited_items", [1, 0])
@pytest.mark.parametrize("sdvt_stuck_items", [1, 0])
@pytest.mark.parametrize("sdvt_exited_items", [1, 0])
@pytest.mark.parametrize("csm_stuck_items", [1, 0])
@pytest.mark.parametrize("csm_exited_items", [1, 0])
@pytest.mark.usefixtures("prepare_modules")
def test_extra_data_full_items(
    stranger, nor, sdvt, extra_data_service,
    nor_stuck_items, nor_exited_items, sdvt_stuck_items, sdvt_exited_items, csm_stuck_items, csm_exited_items
):
    if (nor_stuck_items + nor_exited_items + sdvt_stuck_items + sdvt_exited_items + csm_exited_items + csm_stuck_items) == 0:
        pytest.skip("No items to report in this test case")

    nor_ids = []
    for i in range(0, nor.getNodeOperatorsCount()):
        if nor.getNodeOperatorIsActive(i):
            nor_ids.append(i)
    sdvt_ids = []
    for i in range(0, sdvt.getNodeOperatorsCount()):
        if sdvt.getNodeOperatorIsActive(i):
            sdvt_ids.append(i)
    csm_ids = range(0, MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM)
    nor_ids_exited = nor_ids[:nor_exited_items * MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM]
    nor_ids_stuck = nor_ids[:nor_stuck_items * MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM]
    sdvt_ids_exited = sdvt_ids[:sdvt_exited_items * MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM]
    sdvt_ids_stuck = sdvt_ids[:sdvt_stuck_items * MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM]
    csm_ids_exited = csm_ids[:csm_exited_items * MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM]
    csm_ids_stuck = csm_ids[:csm_stuck_items * MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM]

    # Prepare report extra data
    nor_stuck = {(1, i): nor.getNodeOperatorSummary(i)['stuckValidatorsCount'] + 1 for i in nor_ids_stuck}
    nor_exited = {(1, i): nor.getNodeOperatorSummary(i)['totalExitedValidators'] + 1 for i in nor_ids_exited}
    sdvt_stuck = {(2, i): sdvt.getNodeOperatorSummary(i)['stuckValidatorsCount'] +1 for i in sdvt_ids_stuck}
    sdvt_exited = {(2, i): sdvt.getNodeOperatorSummary(i)['totalExitedValidators'] + 1 for i in sdvt_ids_exited}
    csm_stuck = {(3, i): contracts.csm.getNodeOperatorSummary(i)['stuckValidatorsCount'] + 1 for i in csm_ids_stuck}
    csm_exited = {(3, i): contracts.csm.getNodeOperatorSummary(i)['totalExitedValidators'] + 1 for i in csm_ids_exited}
    extra_data = extra_data_service.collect(
        {**nor_stuck, **sdvt_stuck, **csm_stuck},
        {**nor_exited, **sdvt_exited, **csm_exited},
        MAX_ITEMS_PER_EXTRA_DATA_TRANSACTION,
        MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM,
    )
    modules_with_exited = []
    num_exited_validators_by_staking_module = []
    if nor_exited_items > 0:
        modules_with_exited.append(1)
        nor_exited_before = nor.getStakingModuleSummary()["totalExitedValidators"]
        num_exited_validators_by_staking_module.append(nor_exited_before + (nor_exited_items * MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM))
    if sdvt_exited_items > 0:
        modules_with_exited.append(2)
        sdvt_exited_before = sdvt.getStakingModuleSummary()["totalExitedValidators"]
        num_exited_validators_by_staking_module.append(sdvt_exited_before + (sdvt_exited_items * MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM))
    if csm_exited_items > 0:
        modules_with_exited.append(3)
        csm_exited_before = contracts.csm.getStakingModuleSummary()["totalExitedValidators"]
        num_exited_validators_by_staking_module.append(csm_exited_before + (csm_exited_items * MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM))

    nor_balance_shares_before = {}
    for i in nor_ids_stuck:
        nor_balance_shares_before[i] = shares_balance(nor.getNodeOperator(i, False)["rewardAddress"])
    sdvt_balance_shares_before = {}
    for i in sdvt_ids_stuck:
        sdvt_balance_shares_before[i] = shares_balance(sdvt.getNodeOperator(i, False)["rewardAddress"])
    csm_balance_shares_before = {}
    for i in csm_ids_stuck:
        csm_balance_shares_before[i] = shares_balance(contracts.csm.getNodeOperator(i)["rewardAddress"])

    # Perform report
    (report_tx, extra_report_tx_list) = oracle_report(
        extraDataFormat=1,
        extraDataHashList=extra_data.extra_data_hash_list,
        extraDataItemsCount=(nor_exited_items + nor_stuck_items + sdvt_exited_items + sdvt_stuck_items + csm_exited_items + csm_stuck_items),
        extraDataList=extra_data.extra_data_list,
        stakingModuleIdsWithNewlyExitedValidators=modules_with_exited,
        numExitedValidatorsByStakingModule=num_exited_validators_by_staking_module,
        skip_withdrawals=True,
    )

    nor_distribute_reward_tx = distribute_reward(nor, stranger)
    sdvt_distribute_reward_tx = distribute_reward(sdvt, stranger)

    # Check NOR exited
    nor_penalty_shares = 0
    for i in nor_ids_exited:
        assert nor.getNodeOperatorSummary(i)["totalExitedValidators"] == nor_exited[(1, i)]
    # Check NOR stuck. Check penalties and rewards
    if len(nor_stuck) > 0:
        nor_rewards = [e for e in report_tx.events["TransferShares"] if e['to'] == nor.address][0]['sharesValue']
        for i in nor_ids_stuck:
            assert nor.getNodeOperatorSummary(i)["stuckValidatorsCount"] == nor_stuck[(1, i)]
            assert nor.isOperatorPenalized(i) == True
            shares_after = shares_balance(nor.getNodeOperator(i, False)["rewardAddress"])
            rewards_after = calc_no_rewards(
                nor, no_id=i, shares_minted_as_fees=nor_rewards
            )
            assert almostEqWithDiff(
                shares_after - nor_balance_shares_before[i],
                rewards_after // 2,
                2,
            )
            nor_penalty_shares += rewards_after // 2

    if nor_penalty_shares > 0:
        assert almostEqWithDiff(sum(e['amountOfShares'] for e in nor_distribute_reward_tx.events["StETHBurnRequested"]), nor_penalty_shares, 100)

    # Check SDVT exited
    sdvt_penalty_shares = 0
    for i in sdvt_ids_exited:
        assert sdvt.getNodeOperatorSummary(i)["totalExitedValidators"] == sdvt_exited[(2, i)]
    # Check SDVT stuck. Check penalties and rewards
    if len(sdvt_stuck) > 0:
        sdvt_rewards = [e for e in report_tx.events["TransferShares"] if e['to'] == sdvt.address][0]['sharesValue']
        for i in sdvt_ids_stuck:
            assert sdvt.getNodeOperatorSummary(i)["stuckValidatorsCount"] == sdvt_stuck[(2, i)]
            assert sdvt.isOperatorPenalized(i) == True
            shares_after = shares_balance(sdvt.getNodeOperator(i, False)["rewardAddress"])
            rewards_after = calc_no_rewards(
                sdvt, no_id=i, shares_minted_as_fees=sdvt_rewards
            )
            assert almostEqWithDiff(
                shares_after - sdvt_balance_shares_before[i],
                rewards_after // 2,
                2,
            )
            sdvt_penalty_shares += rewards_after // 2

    if sdvt_penalty_shares > 0:
        # TODO: Fix below check when contains other penalized node operators
        assert almostEqWithDiff(sum(e['amountOfShares'] for e in sdvt_distribute_reward_tx.events["StETHBurnRequested"]), sdvt_penalty_shares, 100)

    # Check CSM exited
    for i in csm_ids_exited:
        assert contracts.csm.getNodeOperatorSummary(i)["totalExitedValidators"] == csm_exited[(3, i)]
    # Check CSM stuck
    for i in csm_ids_stuck:
        assert contracts.csm.getNodeOperatorSummary(i)["stuckValidatorsCount"] == csm_stuck[(3, i)]


# @pytest.mark.skip("This is a heavy test. Make sure to run it only if there are changes in the Staking Router or CSM contracts")
def test_extra_data_most_expensive_report(extra_data_service):
    """
    Make sure the worst report fits into the block gas limit.
    It needs to prepare a lot of node operators in a very special state, so it takes a lot of time to run.

    N = oracle limit
    - Create N NOs
    - Deposit all keys
    - Upload +1 key for each NO
    - Create New NO with 1 key
    - Stuck N NOs
    - Deposit 1 key from NO N+1 (to exclude batches from the queue)
    - Unstuck N NOs

    An estimate for 8 * 24 items:
    Gas used: 11850807 (39.50%)
    """
    increase_staking_module_share(module_id=3, share_multiplier=2)

    csm_operators_count = MAX_ITEMS_PER_EXTRA_DATA_TRANSACTION * MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM
    # create or ensure there are max node operators with 1 depositable key
    fill_csm_operators_with_keys(csm_operators_count,1)
    depositable_keys = contracts.csm.getStakingModuleSummary()["depositableValidatorsCount"]
    deposit_buffer_for_keys(contracts.staking_router, 0, 0, depositable_keys)
    assert contracts.csm.getStakingModuleSummary()["depositableValidatorsCount"] == 0

    csm_ids = range(0, csm_operators_count)
    # Upload a new key for each node operator to put them into the queue
    for i in csm_ids:
        csm_upload_keys(contracts.csm, contracts.cs_accounting, i, 1)
        assert contracts.csm.getNodeOperator(i)["depositableValidatorsCount"] == 1
    # Add a new node operator with 1 depositable key to the end of the queue
    last_no_id = csm_add_node_operator(contracts.csm, contracts.cs_accounting, f"0xbb{str(csm_operators_count).zfill(38)}", [], keys_count=1)
    # report stuck keys for all node operators
    extra_data = extra_data_service.collect(
        {(3, i): 1 for i in range(csm_operators_count)},
        {},
        MAX_ITEMS_PER_EXTRA_DATA_TRANSACTION,
        MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM,
    )

    oracle_report(
        extraDataFormat=1,
        extraDataHashList=extra_data.extra_data_hash_list,
        extraDataItemsCount=MAX_ITEMS_PER_EXTRA_DATA_TRANSACTION,
        extraDataList=extra_data.extra_data_list,
    )

    # Check CSM stuck
    for i in csm_ids:
        assert contracts.csm.getNodeOperatorSummary(i)["stuckValidatorsCount"] == 1
    # deposit last node operator's key
    deposit_buffer_for_keys(contracts.staking_router, 0, 0, 1)
    assert contracts.csm.getNodeOperator(last_no_id)["totalDepositedKeys"] == 1

    # report unstuck keys for all node operators

    extra_data = extra_data_service.collect(
        {(3, i): 0 for i in range(csm_operators_count)},
        {},
        MAX_ITEMS_PER_EXTRA_DATA_TRANSACTION,
        MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM,
    )

    oracle_report(
        extraDataFormat=1,
        extraDataHashList=extra_data.extra_data_hash_list,
        extraDataItemsCount=MAX_ITEMS_PER_EXTRA_DATA_TRANSACTION,
        extraDataList=extra_data.extra_data_list,
    )

    # Check CSM unstuck
    for i in csm_ids:
        assert contracts.csm.getNodeOperatorSummary(i)["stuckValidatorsCount"] == 0


############################################
# HELPER FUNCTIONS
############################################


def add_nor_operators_with_keys(nor, agent_eoa: Account, evm_script_executor_eoa: Account, count: int, keys_per_operator: int):
    names = [f"Name {i}" for i in range(0, count)]
    base_address = int(nor.address, base=16) + 10_000
    reward_addresses = [hex(i + base_address) for i in range(0, count)]

    for i in range(0, count):
        nor.addNodeOperator(
            names[i],
            reward_addresses[i],
            {"from": agent_eoa}
        )
        no_id = nor.getNodeOperatorsCount() - 1
        pubkeys_batch = random_pubkeys_batch(keys_per_operator)
        signatures_batch = random_signatures_batch(keys_per_operator)
        nor.addSigningKeys(
            no_id,
            keys_per_operator,
            pubkeys_batch,
            signatures_batch,
            {"from": reward_addresses[i]},
        )
        nor.setNodeOperatorStakingLimit(no_id, keys_per_operator, {"from": evm_script_executor_eoa})


def fill_nor_with_old_and_new_operators(
    nor, agent_eoa, evm_script_executor_eoa, new_keys_per_operator, max_node_operators_per_item
) -> tuple[int, int]:
    contracts.acl.grantPermission(
        contracts.agent,
        nor.address,
        convert.to_uint(Web3.keccak(text="MANAGE_NODE_OPERATOR_ROLE")),
        {"from": contracts.agent}
    )

    # Calculate new operators count
    operators_count_before = nor.getNodeOperatorsCount()
    operators_count_after = max(max_node_operators_per_item, operators_count_before)
    operators_count_added = max(operators_count_after - operators_count_before, 0)

    # Add new node operators and keys
    if operators_count_added > 0:
        add_nor_operators_with_keys(
            nor,
            agent_eoa,
            evm_script_executor_eoa,
            operators_count_added,
            new_keys_per_operator
        )

    # Activate old deactivated node operators
    for i in range(0, operators_count_after):
        if not nor.getNodeOperatorIsActive(i):
            nor.activateNodeOperator(i, {"from": agent_eoa})

    # Add keys to old node operators
    for i in range(0, operators_count_before):
        pubkeys_batch = random_pubkeys_batch(new_keys_per_operator)
        signatures_batch = random_signatures_batch(new_keys_per_operator)
        operator = nor.getNodeOperator(i, False)
        operator_summary = nor.getNodeOperatorSummary(i)
        new_deposit_limit = operator["totalDepositedValidators"] + new_keys_per_operator
        nor.addSigningKeys(
            i,
            new_keys_per_operator,
            pubkeys_batch,
            signatures_batch,
            {"from": operator["rewardAddress"]},
        )

        # Change staking limits for old node operators (change to new total added keys count)
        nor.setNodeOperatorStakingLimit(i, new_deposit_limit, {"from": evm_script_executor_eoa})

        # Remove target validators limits if active
        if operator_summary["targetLimitMode"] > 0:
            nor.updateTargetValidatorsLimits['uint256,uint256,uint256'](i, 0, 0, {"from": contracts.staking_router})

    return operators_count_before, operators_count_added


def deposit_buffer_for_keys(staking_router, nor_keys_to_deposit, sdvt_keys_to_deposit, csm_keys_to_deposit):
    total_depositable_keys = 0
    module_digests = staking_router.getAllStakingModuleDigests()
    for digest in module_digests:
        (_, _, _, summary) = digest
        (exited_keys, deposited_keys, depositable_keys) = summary
        total_depositable_keys += depositable_keys

    if not (contracts.acl.hasPermission(contracts.agent, contracts.lido, web3.keccak(text="STAKING_CONTROL_ROLE"))):
        contracts.acl.grantPermission(contracts.agent, contracts.lido, web3.keccak(text="STAKING_CONTROL_ROLE"), {"from": contracts.agent})

    contracts.lido.removeStakingLimit({"from": contracts.agent})
    fill_deposit_buffer(total_depositable_keys)
    keys_per_deposit = 50
    # Deposits for NOR
    times = ceil(nor_keys_to_deposit / keys_per_deposit)
    for _ in range(0, times):
        contracts.lido.deposit(keys_per_deposit, 1, "0x", {"from": contracts.deposit_security_module})
    # Deposits for SDVT
    times = ceil(sdvt_keys_to_deposit / keys_per_deposit)
    for _ in range(0, times):
        contracts.lido.deposit(keys_per_deposit, 2, "0x", {"from": contracts.deposit_security_module})
    # Deposits for CSM
    times = ceil(csm_keys_to_deposit / keys_per_deposit)
    for _ in range(0, times):
        contracts.lido.deposit(keys_per_deposit, 3, "0x", {"from": contracts.deposit_security_module})

def calc_no_rewards(module, no_id, shares_minted_as_fees):
    operator_summary = module.getNodeOperatorSummary(no_id)
    module_summary = module.getStakingModuleSummary()

    operator_total_active_keys = (
        operator_summary["totalDepositedValidators"] - operator_summary["totalExitedValidators"]
    )
    module_total_active_keys = module_summary["totalDepositedValidators"] - module_summary["totalExitedValidators"]

    return shares_minted_as_fees * operator_total_active_keys // module_total_active_keys
