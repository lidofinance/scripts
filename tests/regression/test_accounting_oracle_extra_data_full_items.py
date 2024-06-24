import pytest
from brownie import convert
from brownie.network.account import Account
from brownie.network.web3 import Web3

from utils.test.deposits_helpers import fill_deposit_buffer
from utils.test.extra_data import ExtraDataService
from utils.test.helpers import shares_balance, almostEqWithDiff
from utils.test.keys_helpers import random_pubkeys_batch, random_signatures_batch
from utils.test.oracle_report_helpers import oracle_report
from utils.test.node_operators_helpers import distribute_reward

from utils.config import MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT, MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT
from utils.config import contracts
from utils.test.simple_dvt_helpers import simple_dvt_add_node_operators, simple_dvt_add_keys, simple_dvt_vet_keys

@pytest.fixture()
def extra_data_service():
    return ExtraDataService()


@pytest.fixture
def voting_eoa(accounts):
    return accounts.at(contracts.voting.address, force=True)


@pytest.fixture
def agent_eoa(accounts):
    return accounts.at(contracts.agent.address, force=True)


@pytest.fixture
def evm_script_executor_eoa(accounts):
    return accounts.at(contracts.easy_track.evmScriptExecutor(), force=True)


@pytest.fixture
def nor(interface):
    return interface.NodeOperatorsRegistry(contracts.node_operators_registry.address)


@pytest.fixture
def sdvt(interface):
    return interface.SimpleDVT(contracts.simple_dvt.address)


@pytest.mark.parametrize(
    ("nor_stuck_items", "nor_exited_items", "sdvt_stuck_items", "sdvt_exited_items"),
    [
        (1, 1, 1, 1),
        (1, 1, 1, 0),
        (1, 1, 0, 1),
        (1, 1, 0, 0),
        (1, 0, 1, 1),
        (1, 0, 1, 0),
        (1, 0, 0, 1),
        (1, 0, 0, 0),
        (0, 1, 1, 1),
        (0, 1, 1, 0),
        (0, 1, 0, 1),
        (0, 1, 0, 0),
        (0, 0, 1, 1),
        (0, 0, 1, 0),
        (0, 0, 0, 1),
    ]
)
def test_extra_data_full_items(
    stranger, voting_eoa, agent_eoa, evm_script_executor_eoa, nor, sdvt, extra_data_service,
    nor_stuck_items, nor_exited_items, sdvt_stuck_items, sdvt_exited_items
):
    max_node_operators_per_item = MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT
    new_keys_per_operator = 2

    # Fill NOR with new operators and keys
    (nor_count_before, added_nor_operators_count) = fill_nor_with_old_and_new_operators(
        nor,
        voting_eoa,
        agent_eoa,
        evm_script_executor_eoa,
        new_keys_per_operator,
        nor_stuck_items,
        nor_exited_items,
        max_node_operators_per_item,
    )

    # Fill SimpleDVT with new operators and keys
    sdvt_operators_count = max(sdvt_stuck_items, sdvt_exited_items) * max_node_operators_per_item
    add_sdvt_operators_with_keys(stranger, sdvt_operators_count, new_keys_per_operator)

    # Deposit for new added keys from buffer
    keys_for_sdvt = sdvt_operators_count * new_keys_per_operator
    keys_for_nor = 0
    if added_nor_operators_count > 0:
        keys_for_nor = (added_nor_operators_count * new_keys_per_operator) + (nor_count_before * new_keys_per_operator)
    deposit_buffer_for_keys(
        contracts.staking_router,
        keys_for_sdvt,
        keys_for_nor
    )

    # Prepare report extra data
    nor_stuck = {(1, i): 1 for i in range(0, nor_stuck_items * max_node_operators_per_item)}
    nor_exited = {(1, i): nor.getNodeOperatorSummary(i)['totalExitedValidators'] + 1 for i in range(0, nor_exited_items * max_node_operators_per_item)}
    sdvt_stuck = {(2, i): 1 for i in range(0, sdvt_stuck_items * max_node_operators_per_item)}
    sdvt_exited = {(2, i): 1 for i in range(0, sdvt_exited_items * max_node_operators_per_item)}
    extra_data = extra_data_service.collect(
        {**nor_stuck, **sdvt_stuck},
        {**nor_exited, **sdvt_exited},
        MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT,
        MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT,
    )
    modules_with_exited = []
    num_exited_validators_by_staking_module = []
    if nor_exited_items > 0:
        modules_with_exited.append(1)
        nor_exited_before = nor.getStakingModuleSummary()["totalExitedValidators"]
        num_exited_validators_by_staking_module.append(nor_exited_before + (nor_exited_items * max_node_operators_per_item))
    if sdvt_exited_items > 0:
        modules_with_exited.append(2)
        num_exited_validators_by_staking_module.append(sdvt_exited_items * max_node_operators_per_item)

    nor_balance_shares_before = []
    for i in range(0, len(nor_stuck)):
        nor_balance_shares_before.append(shares_balance(nor.getNodeOperator(i, False)["rewardAddress"]))
    sdvt_balance_shares_before = []
    for i in range(0, len(sdvt_stuck)):
        sdvt_balance_shares_before.append(shares_balance(sdvt.getNodeOperator(i, False)["rewardAddress"]))

    # Perform report
    (report_tx, _) = oracle_report(
        extraDataFormat=1,
        extraDataHash=extra_data.data_hash,
        extraDataItemsCount=(nor_exited_items + nor_stuck_items + sdvt_exited_items + sdvt_stuck_items),
        extraDataList=extra_data.extra_data_list,
        stakingModuleIdsWithNewlyExitedValidators=modules_with_exited,
        numExitedValidatorsByStakingModule=num_exited_validators_by_staking_module,
    )

    nor_distribute_reward_tx = distribute_reward(nor, stranger)
    sdvt_distribute_reward_tx = distribute_reward(sdvt, stranger)

    # Check NOR exited
    nor_penalty_shares = 0
    for i in range(0, len(nor_exited)):
        assert nor.getNodeOperatorSummary(i)["totalExitedValidators"] == nor_exited[(1, i)]
    # Check NOR stuck. Check penalties and rewards
    if len(nor_stuck) > 0:
        nor_rewards = [e for e in report_tx.events["TransferShares"] if e['to'] == nor.address][0]['sharesValue']
        for i in range(0, len(nor_stuck)):
            assert nor.getNodeOperatorSummary(i)["stuckValidatorsCount"] == nor_stuck[(1, i)]
            assert nor.isOperatorPenalized(i) == True
            shares_after = shares_balance(nor.getNodeOperator(i, False)["rewardAddress"])
            rewards_after = calc_no_rewards(
                nor, no_id=i, shares_minted_as_fees=nor_rewards
            )
            assert almostEqWithDiff(
                shares_after - nor_balance_shares_before[i],
                rewards_after // 2,
                1,
            )
            nor_penalty_shares += rewards_after // 2

    if nor_penalty_shares > 0:
        assert almostEqWithDiff(sum(e['amountOfShares'] for e in nor_distribute_reward_tx.events["StETHBurnRequested"]), nor_penalty_shares, 50)

    # Check SDVT exited
    sdvt_penalty_shares = 0
    for i in range(0, len(sdvt_exited)):
        assert sdvt.getNodeOperatorSummary(i)["totalExitedValidators"] == sdvt_exited[(2, i)]
    # Check SDVT stuck. Check penalties and rewards
    if len(sdvt_stuck) > 0:
        sdvt_rewards = [e for e in report_tx.events["TransferShares"] if e['to'] == sdvt.address][0]['sharesValue']
        for i in range(0, len(sdvt_stuck)):
            assert sdvt.getNodeOperatorSummary(i)["stuckValidatorsCount"] == sdvt_stuck[(2, i)]
            assert sdvt.isOperatorPenalized(i) == True
            shares_after = shares_balance(sdvt.getNodeOperator(i, False)["rewardAddress"])
            rewards_after = calc_no_rewards(
                sdvt, no_id=i, shares_minted_as_fees=sdvt_rewards
            )
            assert almostEqWithDiff(
                shares_after - sdvt_balance_shares_before[i],
                rewards_after // 2,
                1,
            )
            sdvt_penalty_shares += rewards_after // 2


    if sdvt_penalty_shares > 0:
        # TODO: Fix below check when contains other penalized node operators
        assert almostEqWithDiff(sum(e['amountOfShares'] for e in sdvt_distribute_reward_tx.events["StETHBurnRequested"]), sdvt_penalty_shares, 50)

############################################
# HELPER FUNCTIONS
############################################


def add_sdvt_operators_with_keys(enactor: Account, count: int, keys_per_operator: int):
    names = [f"Name {i}" for i in range(0, count)]
    reward_addresses = [f"0xab{str(i).zfill(38)}" for i in range(0, count)]
    managers = [f"0xcd{str(i).zfill(38)}" for i in range(0, count)]

    node_operators_per_tx = 20
    for i in range(0, count, node_operators_per_tx):
        simple_dvt_add_node_operators(
            contracts.simple_dvt,
            enactor,
            [
                (names[j], reward_addresses[j], managers[j])
                for j in range(i, i + node_operators_per_tx) if j < count
            ]
        )
    for i in range(0, count):
        simple_dvt_add_keys(contracts.simple_dvt, i, keys_per_operator)
        simple_dvt_vet_keys(i, enactor)


def add_nor_operators_with_keys(nor, voting_eoa: Account, evm_script_executor_eoa: Account, count: int, keys_per_operator: int):
    names = [f"Name {i}" for i in range(0, count)]
    reward_addresses = [f"0xbb{str(i).zfill(38)}" for i in range(0, count)]

    for i in range(0, count):
        nor.addNodeOperator(
            names[i],
            reward_addresses[i],
            {"from": voting_eoa}
        )
        no_id = nor.getNodeOperatorsCount() - 1
        pubkeys_batch = random_pubkeys_batch(keys_per_operator)
        signatures_batch = random_signatures_batch(keys_per_operator)
        nor.addSigningKeysOperatorBH(
            no_id,
            keys_per_operator,
            pubkeys_batch,
            signatures_batch,
            {"from": reward_addresses[i]},
        )
        nor.setNodeOperatorStakingLimit(no_id, keys_per_operator, {"from": evm_script_executor_eoa})


def fill_nor_with_old_and_new_operators(
    nor, voting_eoa, agent_eoa, evm_script_executor_eoa, new_keys_per_operator, nor_stuck_items, nor_exited_items, max_node_operators_per_item,
) -> tuple[int, int]:
    # Curated: Add new operators and keys
    contracts.staking_router.grantRole(
        contracts.staking_router.MANAGE_WITHDRAWAL_CREDENTIALS_ROLE(), voting_eoa, {"from": agent_eoa}
    )
    contracts.acl.grantPermission(
        contracts.voting,
        contracts.node_operators_registry,
        convert.to_uint(Web3.keccak(text="MANAGE_NODE_OPERATOR_ROLE")),
        {"from": contracts.voting},
    )
    nor_count_before = nor.getNodeOperatorsCount()
    added_nor_operators_count = (max(nor_stuck_items, nor_exited_items) * max_node_operators_per_item) - nor_count_before
    if added_nor_operators_count <= 0:
        return nor_count_before, added_nor_operators_count
    # Add new node operators and keys
    add_nor_operators_with_keys(nor, voting_eoa, evm_script_executor_eoa, added_nor_operators_count, new_keys_per_operator)
    # Activate old deactivated node operators
    nor.activateNodeOperator(1, {"from": voting_eoa})
    nor.activateNodeOperator(12, {"from": voting_eoa})
    # Add keys to old node operators
    for i in range(0, nor_count_before):
        pubkeys_batch = random_pubkeys_batch(new_keys_per_operator)
        signatures_batch = random_signatures_batch(new_keys_per_operator)
        operator = nor.getNodeOperator(i, False)
        new_deposit_limit = operator["totalDepositedValidators"] + new_keys_per_operator
        nor.addSigningKeysOperatorBH(
            i,
            new_keys_per_operator,
            pubkeys_batch,
            signatures_batch,
            {"from": operator["rewardAddress"]},
        )
        # Change staking limits for old node operators (change to new total added keys count)
        nor.setNodeOperatorStakingLimit(i, new_deposit_limit, {"from": evm_script_executor_eoa})
        nor.updateTargetValidatorsLimits(i, True, new_deposit_limit, {"from": contracts.staking_router})
    return nor_count_before, added_nor_operators_count


def deposit_buffer_for_keys(staking_router, sdvt_keys_to_deposit, nor_keys_to_deposit):
    total_depositable_keys = 0
    module_digests = staking_router.getAllStakingModuleDigests()
    for digest in module_digests:
        (_, _, _, summary) = digest
        (exited_keys, deposited_keys, depositable_keys) = summary
        total_depositable_keys += depositable_keys

    contracts.lido.removeStakingLimit({"from": contracts.voting})
    fill_deposit_buffer(total_depositable_keys)
    keys_per_deposit = 50
    # Deposits for SDVT
    times = sdvt_keys_to_deposit // keys_per_deposit
    for _ in range(0, times):
        contracts.lido.deposit(keys_per_deposit, 2, "0x", {"from": contracts.deposit_security_module})

    # Deposits for NOR
    times = nor_keys_to_deposit // keys_per_deposit;
    for _ in range(0, times):
        contracts.lido.deposit(keys_per_deposit, 1, "0x", {"from": contracts.deposit_security_module})


def calc_no_rewards(module, no_id, shares_minted_as_fees):
    operator_summary = module.getNodeOperatorSummary(no_id)
    module_summary = module.getStakingModuleSummary()

    operator_total_active_keys = (
        operator_summary["totalDepositedValidators"] - operator_summary["totalExitedValidators"]
    )
    module_total_active_keys = module_summary["totalDepositedValidators"] - module_summary["totalExitedValidators"]

    return shares_minted_as_fees * operator_total_active_keys // module_total_active_keys
