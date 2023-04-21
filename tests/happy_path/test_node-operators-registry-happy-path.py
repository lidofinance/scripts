import pytest
from web3 import Web3
from brownie import chain, ZERO_ADDRESS
from hexbytes import HexBytes
from typing import NewType, Tuple

from utils.test.extra_data import (
    ExtraDataService,
)
from utils.test.helpers import (
    steth_balance,
    shares_balance,
    ETH,
    almostEq
)
from utils.test.oracle_report_helpers import (
    oracle_report,
)
from utils.config import (contracts, lido_dao_staking_router)

PUBKEY_LENGTH = 48
SIGNATURE_LENGTH = 96
INITIAL_TOKEN_HOLDER = "0x000000000000000000000000000000000000dead"
TOTAL_BASIS_POINTS = 10000
ZERO_HASH = bytes([0] * 32)
ZERO_BYTES32 = HexBytes(ZERO_HASH)


@pytest.fixture()
def extra_data_service():
    return ExtraDataService()


@pytest.fixture(scope="module")
def voting_eoa(accounts):
    return accounts.at(contracts.voting.address, force=True)


StakingModuleId = NewType('StakingModuleId', int)
NodeOperatorId = NewType('NodeOperatorId', int)
NodeOperatorGlobalIndex = Tuple[StakingModuleId, NodeOperatorId]


def node_operator(module_id, node_operator_id) -> NodeOperatorGlobalIndex:
    return module_id, node_operator_id


@pytest.fixture(scope="module")
def nor(accounts, interface):
    return interface.NodeOperatorsRegistry(contracts.node_operators_registry.address)


def calc_no_rewards(
    nor, no_id, report_shares
):
    total_signing_keys = nor.getNodeOperatorSummary(no_id)[
        'totalDepositedValidators'] - nor.getNodeOperatorSummary(no_id)['totalExitedValidators']
    total_deposite_keys = nor.getStakingModuleSummary()[
        'totalDepositedValidators'] - nor.getStakingModuleSummary()['totalExitedValidators']

    return report_shares // 2 * total_signing_keys // total_deposite_keys


def increase_limit(nor, first, second, base, keys_count, voting_eoa):
    current_first_keys = max(nor.getNodeOperator(first, True)['totalVettedValidators'], nor.getNodeOperator(
        first, True)['totalAddedValidators'])
    current_second_keys = max(nor.getNodeOperator(second, True)['totalVettedValidators'], nor.getNodeOperator(
        second, True)['totalAddedValidators'])
    current_base_keys = max(nor.getNodeOperator(base, True)['totalVettedValidators'], nor.getNodeOperator(
        base, True)['totalAddedValidators'])

    nor.setNodeOperatorStakingLimit(
        first, current_first_keys + keys_count, {'from': voting_eoa})
    nor.setNodeOperatorStakingLimit(
        second, current_second_keys + keys_count, {'from': voting_eoa})
    nor.setNodeOperatorStakingLimit(
        base, current_base_keys + keys_count, {'from': voting_eoa})


def deposit_and_check_keys(nor, first_no_id, second_no_id, base_no_id, keys_count):

    deposited_keys_first_before = nor.getNodeOperatorSummary(
        first_no_id)['totalDepositedValidators']
    deposited_keys_second_before = nor.getNodeOperatorSummary(
        second_no_id)['totalDepositedValidators']
    deposited_keys_base_before = nor.getNodeOperatorSummary(
        base_no_id)['totalDepositedValidators']

    module_total_deposited_keys_before = nor.getStakingModuleSummary()[
        'totalDepositedValidators']

    contracts.lido.deposit(keys_count, 1, '0x', {
        'from': contracts.deposit_security_module.address})

    module_total_deposited_keys_after = nor.getStakingModuleSummary()[
        'totalDepositedValidators']

    assert module_total_deposited_keys_before < module_total_deposited_keys_after

    deposited_keys_first_after = nor.getNodeOperatorSummary(
        first_no_id)['totalDepositedValidators']
    deposited_keys_second_after = nor.getNodeOperatorSummary(
        second_no_id)['totalDepositedValidators']
    deposited_keys_base_after = nor.getNodeOperatorSummary(
        base_no_id)['totalDepositedValidators']

    return (deposited_keys_first_before, deposited_keys_second_before, deposited_keys_base_before,
            deposited_keys_first_after, deposited_keys_second_after, deposited_keys_base_after)


def test_node_operators(
        nor, accounts, extra_data_service, voting_eoa, eth_whale
):
    contracts.staking_router.grantRole(
        Web3.keccak(text="STAKING_MODULE_MANAGE_ROLE"),
        voting_eoa,
        {"from": contracts.agent.address},
    )
    contracts.lido.submit(
        ZERO_ADDRESS, {'from': eth_whale, 'amount': ETH(1000)})

    tested_no_id_first = 21
    tested_no_id_second = 22
    base_no_id = 23

    increase_limit(nor, tested_no_id_first,
                   tested_no_id_second, base_no_id, 3, voting_eoa)

    # посмотреть что totalVettedValidators больше чем totalDepositedValidators, totalAddedValidators >= totalVettedValidators

    # nor.setNodeOperatorStakingLimit(
    #     tested_no_id_second, 7500, {'from': voting_eoa})

    # до репорта дергаю дистрибьюшен с любым числом
    # репорт что стакается
    # после репорта такой же запрос с такими же значениями и посмотреть что поменялось

    penalty_delay = nor.getStuckPenaltyDelay()

    print('-----getRewardsDistribution', nor.getRewardsDistribution(1000000))

    node_operator_first = nor.getNodeOperatorSummary(tested_no_id_first)
    address_first = nor.getNodeOperator(
        tested_no_id_first, False)['rewardAddress']
    node_operator_first_balance_shares_before = shares_balance(address_first)

    node_operator_second = nor.getNodeOperatorSummary(tested_no_id_second)
    address_second = nor.getNodeOperator(
        tested_no_id_second, False)['rewardAddress']
    node_operator_second_balance_shares_before = shares_balance(address_second)

    node_operator_base = nor.getNodeOperatorSummary(base_no_id)
    address_base_no = nor.getNodeOperator(base_no_id, False)['rewardAddress']
    node_operator_base_balance_shares_before = shares_balance(address_base_no)

# First report - base
    (report_tx, extra_report_tx) = oracle_report(
        exclude_vaults_balances=True)

    node_operator_first_balance_shares_after = shares_balance(address_first)
    node_operator_second_balance_shares_after = shares_balance(address_second)
    node_operator_base_balance_shares_after = shares_balance(address_base_no)

    # expeected shares
    node_operator_first_rewards_after_first_report = calc_no_rewards(
        nor, no_id=tested_no_id_first, report_shares=report_tx.events['TokenRebased']['sharesMintedAsFees'])
    node_operator_second_rewards_after_first_report = calc_no_rewards(
        nor, no_id=tested_no_id_second, report_shares=report_tx.events['TokenRebased']['sharesMintedAsFees'])
    node_operator_base_rewards_after_first_report = calc_no_rewards(
        nor, no_id=base_no_id, report_shares=report_tx.events['TokenRebased']['sharesMintedAsFees'])

    # check shares by empty report
    assert node_operator_first_balance_shares_after - \
        node_operator_first_balance_shares_before == node_operator_first_rewards_after_first_report
    assert node_operator_second_balance_shares_after - \
        node_operator_second_balance_shares_before == node_operator_second_rewards_after_first_report
    assert node_operator_base_balance_shares_after - \
        node_operator_base_balance_shares_before == node_operator_base_rewards_after_first_report

    # Prepare bad extra data
    vals_stuck_non_zero = {
        node_operator(1, tested_no_id_first): 2,
        node_operator(1, tested_no_id_second): 2,
    }
    vals_exited_non_zero = {
        node_operator(1, tested_no_id_first): 5,
        node_operator(1, tested_no_id_second): 5,
    }
    extra_data = extra_data_service.collect(
        vals_stuck_non_zero, vals_exited_non_zero, 10, 10)

    # shares before report
    node_operator_first_balance_shares_before = shares_balance(address_first)
    node_operator_second_balance_shares_before = shares_balance(address_second)
    node_operator_base_balance_shares_before = shares_balance(address_base_no)

# Second report - first NO and second NO has stuck/exited
    (report_tx, extra_report_tx) = oracle_report(
        exclude_vaults_balances=True,
        extraDataFormat=1, extraDataHash=extra_data.data_hash, extraDataItemsCount=2,
        extraDataList=extra_data.extra_data,
        numExitedValidatorsByStakingModule=[10],
        stakingModuleIdsWithNewlyExitedValidators=[1])

    # shares after report
    node_operator_first = nor.getNodeOperatorSummary(tested_no_id_first)
    node_operator_second = nor.getNodeOperatorSummary(tested_no_id_second)
    node_operator_base = nor.getNodeOperatorSummary(base_no_id)

    # expected shares
    node_operator_first_rewards_after_second_report = calc_no_rewards(
        nor, no_id=tested_no_id_first, report_shares=report_tx.events['TokenRebased']['sharesMintedAsFees'])
    node_operator_second_rewards_after_second_report = calc_no_rewards(
        nor, no_id=tested_no_id_second, report_shares=report_tx.events['TokenRebased']['sharesMintedAsFees'])
    node_operator_base_rewards_after_second_report = calc_no_rewards(
        nor, no_id=base_no_id, report_shares=report_tx.events['TokenRebased']['sharesMintedAsFees'])

    node_operator_first_balance_shares_after = shares_balance(address_first)
    node_operator_second_balance_shares_after = shares_balance(address_second)
    node_operator_base_balance_shares_after = shares_balance(address_base_no)

    print('2 ============', node_operator_first_balance_shares_after -
          node_operator_first_balance_shares_before, node_operator_second_balance_shares_after -
          node_operator_second_balance_shares_before)

    # check shares by bad report wit penalty
    assert node_operator_first_balance_shares_after - \
        node_operator_first_balance_shares_before == node_operator_first_rewards_after_second_report // 2
    assert node_operator_second_balance_shares_after - \
        node_operator_second_balance_shares_before == node_operator_second_rewards_after_second_report // 2
    assert node_operator_base_balance_shares_after - \
        node_operator_base_balance_shares_before == node_operator_base_rewards_after_second_report

    # NO stats
    assert node_operator_first['stuckValidatorsCount'] == 2
    assert node_operator_first['totalExitedValidators'] == 5
    assert node_operator_first['refundedValidatorsCount'] == 0
    assert node_operator_first['stuckPenaltyEndTimestamp'] == 0

    assert node_operator_second['stuckValidatorsCount'] == 2
    assert node_operator_second['totalExitedValidators'] == 5
    assert node_operator_second['refundedValidatorsCount'] == 0
    assert node_operator_second['stuckPenaltyEndTimestamp'] == 0

    assert node_operator_base['stuckValidatorsCount'] == 0
    assert node_operator_base['totalExitedValidators'] == 0
    assert node_operator_base['refundedValidatorsCount'] == 0
    assert node_operator_base['stuckPenaltyEndTimestamp'] == 0

    assert nor.isOperatorPenalized(tested_no_id_first) == True
    assert nor.isOperatorPenalized(tested_no_id_second) == True
    assert nor.isOperatorPenalized(base_no_id) == False

    # Events
    assert extra_report_tx.events['ExitedSigningKeysCountChanged'][0]['nodeOperatorId'] == tested_no_id_first
    assert extra_report_tx.events['ExitedSigningKeysCountChanged'][0]['exitedValidatorsCount'] == 5

    assert extra_report_tx.events['ExitedSigningKeysCountChanged'][1]['nodeOperatorId'] == tested_no_id_second
    assert extra_report_tx.events['ExitedSigningKeysCountChanged'][1]['exitedValidatorsCount'] == 5

    assert extra_report_tx.events['StuckPenaltyStateChanged'][0]['nodeOperatorId'] == tested_no_id_first
    assert extra_report_tx.events['StuckPenaltyStateChanged'][0]['stuckValidatorsCount'] == 2

    assert extra_report_tx.events['StuckPenaltyStateChanged'][1]['nodeOperatorId'] == tested_no_id_second
    assert extra_report_tx.events['StuckPenaltyStateChanged'][1]['stuckValidatorsCount'] == 2


# Deposite keys
    (deposited_keys_first_before, deposited_keys_second_before, deposited_keys_base_before,
     deposited_keys_first_after, deposited_keys_second_after, deposited_keys_base_after
     ) = deposit_and_check_keys(nor, tested_no_id_first, tested_no_id_second, base_no_id, 10)

    # check don't change deposited keys for penalized NO
    assert deposited_keys_first_before == deposited_keys_first_after
    assert deposited_keys_second_before == deposited_keys_second_after
    assert deposited_keys_base_before != deposited_keys_base_after

    # # Refund keys 0 NO
    # nor.updateRefundedValidatorsCount(
    #     tested_no_id_first, 2, {"from": lido_dao_staking_router})

    # Prepare extra data - first node operator has exited 2 + 5 keys an stuck 0
    vals_stuck_non_zero = {
        node_operator(1, tested_no_id_first): 0,
    }
    vals_exited_non_zero = {
        node_operator(1, tested_no_id_first): 7,
    }
    extra_data = extra_data_service.collect(
        vals_stuck_non_zero, vals_exited_non_zero, 10, 10)

    # shares before report
    node_operator_first_balance_shares_before = shares_balance(address_first)
    node_operator_second_balance_shares_before = shares_balance(address_second)
    node_operator_base_balance_shares_before = shares_balance(address_base_no)

    # TODO: добавить проверку что если разные эексид ключи то шар будет 0

# Third report - first NO: increase stuck to 0, desc exited to 7 = 5 + 2
    # Second NO: same as prev report
    (report_tx, extra_report_tx) = oracle_report(cl_diff=ETH(10), exclude_vaults_balances=True,
                                                 extraDataFormat=1, extraDataHash=extra_data.data_hash,
                                                 extraDataItemsCount=2, extraDataList=extra_data.extra_data,
                                                 numExitedValidatorsByStakingModule=[12], stakingModuleIdsWithNewlyExitedValidators=[1])

    node_operator_first = nor.getNodeOperatorSummary(tested_no_id_first)
    node_operator_second = nor.getNodeOperatorSummary(tested_no_id_second)
    node_operator_base = nor.getNodeOperatorSummary(base_no_id)

    # shares after report
    node_operator_first_balance_shares_after = shares_balance(address_first)
    node_operator_second_balance_shares_after = shares_balance(address_second)
    node_operator_base_balance_shares_after = shares_balance(address_base_no)

    # expected shares
    node_operator_first_rewards_after_third_report = calc_no_rewards(
        nor, no_id=tested_no_id_first, report_shares=report_tx.events['TokenRebased']['sharesMintedAsFees'])
    node_operator_second_rewards_after__third_report = calc_no_rewards(
        nor, no_id=tested_no_id_second, report_shares=report_tx.events['TokenRebased']['sharesMintedAsFees'])
    node_operator_base_rewards_after__third_report = calc_no_rewards(
        nor, no_id=base_no_id, report_shares=report_tx.events['TokenRebased']['sharesMintedAsFees'])

    # first NO has penalty has a penalty until stuckPenaltyEndTimestamp
    # check shares by bad report wit penalty
    # diff by 1 share because of rounding
    assert almostEq(node_operator_first_balance_shares_after -
                    node_operator_first_balance_shares_before, node_operator_first_rewards_after_third_report // 2, 1)
    assert almostEq(node_operator_second_balance_shares_after -
                    node_operator_second_balance_shares_before, node_operator_second_rewards_after__third_report // 2, 1)
    assert almostEq(node_operator_base_balance_shares_after -
                    node_operator_base_balance_shares_before, node_operator_base_rewards_after__third_report, 1)

    # TODO: расчитать сколько на самом деле получил в шарах

    # NO stats
    assert node_operator_base['stuckPenaltyEndTimestamp'] == 0

    assert node_operator_first['stuckValidatorsCount'] == 0
    assert node_operator_first['totalExitedValidators'] == 7
    assert node_operator_first['refundedValidatorsCount'] == 0
    # first NO has penalty has a penalty until stuckPenaltyEndTimestamp
    assert node_operator_first['stuckPenaltyEndTimestamp'] > chain.time()

    assert node_operator_second['stuckValidatorsCount'] == 2
    assert node_operator_second['totalExitedValidators'] == 5
    assert node_operator_second['refundedValidatorsCount'] == 0
    assert node_operator_second['stuckPenaltyEndTimestamp'] == 0

    assert nor.isOperatorPenalized(tested_no_id_first) == True
    assert nor.isOperatorPenalized(tested_no_id_second) == True
    assert nor.isOperatorPenalized(base_no_id) == False

    # events
    assert extra_report_tx.events['ExitedSigningKeysCountChanged'][0]['nodeOperatorId'] == tested_no_id_first
    assert extra_report_tx.events['ExitedSigningKeysCountChanged'][0]['exitedValidatorsCount'] == 7

    assert extra_report_tx.events['StuckPenaltyStateChanged'][0]['nodeOperatorId'] == tested_no_id_first
    assert extra_report_tx.events['StuckPenaltyStateChanged'][0]['stuckValidatorsCount'] == 0

    # stuckPenaltyEndTimestamp = extra_report_tx.events[
    #     'StuckPenaltyStateChanged'][0]['stuckPenaltyEndTimestamp']

    # Burner проверить что в след репорте шары сожгуться которые getSharesRequestedToBurn()


# sleep PENALTY_DELAY time
    chain.sleep(penalty_delay + 1)
    chain.mine()

    # Prepare extra data for bad report by second NO
    vals_stuck_non_zero = {
        node_operator(1, tested_no_id_second): 2,
    }
    vals_exited_non_zero = {
        node_operator(1, tested_no_id_second): 5,
    }
    extra_data = extra_data_service.collect(
        vals_stuck_non_zero, vals_exited_non_zero, 10, 10)

    # shares before report
    node_operator_first_balance_shares_before = shares_balance(address_first)
    node_operator_second_balance_shares_before = shares_balance(address_second)
    node_operator_base_balance_shares_before = shares_balance(address_base_no)

# Fourth report - second NO: has stuck 2 keys
    (report_tx, extra_report_tx) = oracle_report(
        exclude_vaults_balances=True,
        extraDataFormat=1, extraDataHash=extra_data.data_hash, extraDataItemsCount=2, extraDataList=extra_data.extra_data,
        numExitedValidatorsByStakingModule=[12], stakingModuleIdsWithNewlyExitedValidators=[1])

    node_operator_first = nor.getNodeOperatorSummary(tested_no_id_first)
    node_operator_second = nor.getNodeOperatorSummary(tested_no_id_second)
    node_operator_base = nor.getNodeOperatorSummary(base_no_id)

    # shares after report
    node_operator_first_balance_shares_after = shares_balance(address_first)
    node_operator_second_balance_shares_after = shares_balance(address_second)
    node_operator_base_balance_shares_after = shares_balance(address_base_no)

    # expected shares
    node_operator_first_rewards_after_fourth_report = calc_no_rewards(
        nor, no_id=tested_no_id_first, report_shares=report_tx.events['TokenRebased']['sharesMintedAsFees'])
    node_operator_second_rewards_after__fourth_report = calc_no_rewards(
        nor, no_id=tested_no_id_second, report_shares=report_tx.events['TokenRebased']['sharesMintedAsFees'])
    node_operator_base_rewards_after__fourth_report = calc_no_rewards(
        nor, no_id=base_no_id, report_shares=report_tx.events['TokenRebased']['sharesMintedAsFees'])

    # Penalty ended for first operator
    # check shares by bad report with penalty for second NO
    # diff by 1 share because of rounding
    assert almostEq(node_operator_first_balance_shares_after -
                    node_operator_first_balance_shares_before, node_operator_first_rewards_after_fourth_report, 1)
    assert almostEq(node_operator_second_balance_shares_after -
                    node_operator_second_balance_shares_before, node_operator_second_rewards_after__fourth_report // 2, 1)
    assert almostEq(node_operator_base_balance_shares_after -
                    node_operator_base_balance_shares_before, node_operator_base_rewards_after__fourth_report, 1)

    assert node_operator_base['stuckPenaltyEndTimestamp'] == 0

    assert node_operator_first['stuckValidatorsCount'] == 0
    assert node_operator_first['totalExitedValidators'] == 7
    assert node_operator_first['refundedValidatorsCount'] == 0
    # Penalty ended for first operator
    assert node_operator_first['stuckPenaltyEndTimestamp'] < chain.time()

    assert node_operator_second['stuckValidatorsCount'] == 2
    assert node_operator_second['totalExitedValidators'] == 5
    assert node_operator_second['refundedValidatorsCount'] == 0
    assert node_operator_second['stuckPenaltyEndTimestamp'] == 0

    assert nor.isOperatorPenalized(tested_no_id_first) == False
    assert nor.isOperatorPenalized(tested_no_id_second) == True
    assert nor.isOperatorPenalized(base_no_id) == False

# Deposite
    (deposited_keys_first_before, deposited_keys_second_before, deposited_keys_base_before,
     deposited_keys_first_after, deposited_keys_second_after, deposited_keys_base_after
     ) = deposit_and_check_keys(nor, tested_no_id_first, tested_no_id_second, base_no_id, 30)

    print('tested_no_id_first------getNodeOperator-', nor.getNodeOperator(tested_no_id_first,
          True))

    print('tested_no_id_first-------getNodeOperatorSummary',
          nor.getNodeOperatorSummary(tested_no_id_first))
    print('base_no_id-------getNodeOperatorSummary',
          nor.getNodeOperatorSummary(base_no_id))
    print('tested_no_id_second-------getNodeOperatorSummary',
          nor.getNodeOperatorSummary(tested_no_id_second))

    print('-------- ', deposited_keys_first_before, deposited_keys_first_after)

    # check don't change deposited keys for penalized NO (only second NO)
    assert deposited_keys_first_before == deposited_keys_first_after  # TODO !=
    assert deposited_keys_second_before == deposited_keys_second_after
    assert deposited_keys_base_before != deposited_keys_base_after

    # # Refund 2 keys Second NO
    contracts.staking_router.updateRefundedValidatorsCount(
        1, tested_no_id_second, 2, {"from": voting_eoa})

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
        nor, no_id=tested_no_id_first, report_shares=report_tx.events['TokenRebased']['sharesMintedAsFees'])
    node_operator_second_rewards_after_fifth_report = calc_no_rewards(
        nor, no_id=tested_no_id_second, report_shares=report_tx.events['TokenRebased']['sharesMintedAsFees'])
    node_operator_base_rewards_after_fifth_report = calc_no_rewards(
        nor, no_id=base_no_id, report_shares=report_tx.events['TokenRebased']['sharesMintedAsFees'])

    # Penalty only for second operator
    # diff by 1 share because of rounding
    assert almostEq(node_operator_first_balance_shares_after -
                    node_operator_first_balance_shares_before, node_operator_first_rewards_after_fifth_report, 1)
    assert almostEq(node_operator_second_balance_shares_after -
                    node_operator_second_balance_shares_before, node_operator_second_rewards_after_fifth_report // 2, 1)
    assert almostEq(node_operator_base_balance_shares_after -
                    node_operator_base_balance_shares_before, node_operator_base_rewards_after_fifth_report, 1)

    assert node_operator_base['stuckPenaltyEndTimestamp'] == 0

    assert node_operator_first['stuckValidatorsCount'] == 0
    assert node_operator_first['totalExitedValidators'] == 7
    assert node_operator_first['refundedValidatorsCount'] == 0
    assert node_operator_first['stuckPenaltyEndTimestamp'] < chain.time()

    assert node_operator_second['stuckValidatorsCount'] == 2
    assert node_operator_second['totalExitedValidators'] == 5
    assert node_operator_second['refundedValidatorsCount'] == 2
    assert node_operator_second['stuckPenaltyEndTimestamp'] > chain.time()

    assert nor.isOperatorPenaltyCleared(
        tested_no_id_first) == False  # TODO True
    assert nor.isOperatorPenaltyCleared(
        tested_no_id_second) == False  # TODO True

    chain.sleep(penalty_delay + 1)
    chain.mine()

    # shares before report
    node_operator_first_balance_shares_before = shares_balance(address_first)
    node_operator_second_balance_shares_before = shares_balance(address_second)
    node_operator_base_balance_shares_before = shares_balance(address_base_no)

# Seventh report
    (report_tx, extra_report_tx) = oracle_report()

    # shares after report
    node_operator_first_balance_shares_after = shares_balance(address_first)
    node_operator_second_balance_shares_after = shares_balance(address_second)
    node_operator_base_balance_shares_after = shares_balance(address_base_no)

    assert nor.isOperatorPenaltyCleared(
        tested_no_id_first) == False  # TODO True
    assert nor.isOperatorPenaltyCleared(
        tested_no_id_second) == False  # TODO True

    node_operator_first = nor.getNodeOperatorSummary(tested_no_id_first)
    node_operator_second = nor.getNodeOperatorSummary(tested_no_id_second)

    # expected shares
    node_operator_first_rewards_after_seventh_report = calc_no_rewards(
        nor, no_id=tested_no_id_first, report_shares=report_tx.events['TokenRebased']['sharesMintedAsFees'])
    node_operator_second_rewards_after_seventh_report = calc_no_rewards(
        nor, no_id=tested_no_id_second, report_shares=report_tx.events['TokenRebased']['sharesMintedAsFees'])
    node_operator_base_rewards_after_seventh_report = calc_no_rewards(
        nor, no_id=base_no_id, report_shares=report_tx.events['TokenRebased']['sharesMintedAsFees'])

    # No penalty
    # diff by 1 share because of rounding
    assert almostEq(node_operator_first_balance_shares_after -
                    node_operator_first_balance_shares_before, node_operator_first_rewards_after_seventh_report, 1)
    assert almostEq(node_operator_second_balance_shares_after -
                    node_operator_second_balance_shares_before, node_operator_second_rewards_after_seventh_report, 1)
    assert almostEq(node_operator_base_balance_shares_after -
                    node_operator_base_balance_shares_before, node_operator_base_rewards_after_seventh_report, 1)

    assert node_operator_first['stuckValidatorsCount'] == 0
    assert node_operator_first['totalExitedValidators'] == 7
    assert node_operator_first['refundedValidatorsCount'] == 0
    assert node_operator_first['stuckPenaltyEndTimestamp'] < chain.time()

    assert node_operator_second['stuckValidatorsCount'] == 2
    assert node_operator_second['totalExitedValidators'] == 5
    assert node_operator_second['refundedValidatorsCount'] == 2
    assert node_operator_second['stuckPenaltyEndTimestamp'] < chain.time()

    # Deposite
    (deposited_keys_first_before, deposited_keys_second_before, deposited_keys_base_before,
     deposited_keys_first_after, deposited_keys_second_after, deposited_keys_base_after
     ) = deposit_and_check_keys(nor, tested_no_id_first, tested_no_id_second, base_no_id, 30)

    # check don't change deposited keys for penalized NO (only second NO)
    assert deposited_keys_first_before == deposited_keys_first_after  # TODO !=
    assert deposited_keys_second_before == deposited_keys_second_after  # TODO !=
    assert deposited_keys_base_before != deposited_keys_base_after
