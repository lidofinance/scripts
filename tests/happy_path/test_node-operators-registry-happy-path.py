import math
import pytest
import random
from brownie import web3, interface, convert, reverts, chain
from utils.mainnet_fork import chain_snapshot
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes
from hexbytes import HexBytes
from typing import TYPE_CHECKING, NewType, Tuple

from utils.test.extra_data import (
    ExtraDataService,
    FormatList,
    ItemType,
    ItemPayload,
)
from utils.test.oracle_report_helpers import (
    ONE_DAY,
    SHARE_RATE_PRECISION,
    push_oracle_report,
    get_finalization_batches,
    simulate_report,
    wait_to_next_available_report_time,
)
from utils.config import (contracts, deposit_contract, lido_dao_node_operators_registry, lido_dao_staking_router,
                          lido_dao_steth_address, lido_dao_voting_address)

PUBKEY_LENGTH = 48
SIGNATURE_LENGTH = 96
INITIAL_TOKEN_HOLDER = "0x000000000000000000000000000000000000dead"
TOTAL_BASIS_POINTS = 10000
ZERO_HASH = bytes([0] * 32)
ZERO_BYTES32 = HexBytes(ZERO_HASH)


def ETH(amount):
    return math.floor(amount * 10**18)


def SHARES(amount):
    return ETH(amount)


def steth_balance(account):
    return contracts.lido.balanceOf(account)


def eth_balance(account):
    return web3.eth.get_balance(account)


def almostEqEth(b1, b2):
    return abs(b1 - b2) <= 10


def random_hexstr(length):
    return "0x" + random.randbytes(length).hex()


def packExtraDataList(extraDataItems):
    return '0x' + ''.join(item[2:] for item in extraDataItems)


@pytest.fixture()
def extra_data_service():
    return ExtraDataService()


@pytest.fixture(scope="module")
def voting_eoa(accounts):
    return accounts.at(contracts.voting.address, force=True)


def oracle_report(increaseBalance=0, extraDataFormat=0, extraDataHash=ZERO_BYTES32, extraDataItemsCount=0, extraDataList=''):
    wait_to_next_available_report_time()

    (refSlot, _) = contracts.hash_consensus_for_accounting_oracle.getCurrentFrame()
    elRewardsVaultBalance = eth_balance(
        contracts.execution_layer_rewards_vault.address)
    withdrawalVaultBalance = eth_balance(contracts.withdrawal_vault.address)
    (coverShares, nonCoverShares) = contracts.burner.getSharesRequestedToBurn()

    prev_report = contracts.lido.getBeaconStat().dict()
    beacon_validators = prev_report["beaconValidators"]
    beacon_balance = prev_report["beaconBalance"]
    # buffered_ether_before = contracts.lido.getBufferedEther()

    print("beaconBalance", beacon_balance)
    print("beaconValidators", beacon_validators)
    print("withdrawalVaultBalance", withdrawalVaultBalance)
    print("elRewardsVaultBalance", elRewardsVaultBalance)

    postCLBalance = beacon_balance + ETH(increaseBalance)

    (postTotalPooledEther, postTotalShares, withdrawals, elRewards) = simulate_report(
        refSlot=refSlot,
        beaconValidators=beacon_validators,
        postCLBalance=postCLBalance,
        withdrawalVaultBalance=withdrawalVaultBalance,
        elRewardsVaultBalance=elRewardsVaultBalance,
    )
    simulatedShareRate = postTotalPooledEther * \
        SHARE_RATE_PRECISION // postTotalShares
    sharesRequestedToBurn = coverShares + nonCoverShares

    finalization_batches = get_finalization_batches(
        simulatedShareRate, withdrawals, elRewards)

    return push_oracle_report(
        refSlot=refSlot,
        clBalance=postCLBalance,
        numValidators=beacon_validators,
        withdrawalVaultBalance=withdrawalVaultBalance,
        sharesRequestedToBurn=sharesRequestedToBurn,
        withdrawalFinalizationBatches=finalization_batches,
        elRewardsVaultBalance=elRewardsVaultBalance,
        simulatedShareRate=simulatedShareRate,
        extraDataFormat=extraDataFormat,
        extraDataHash=extraDataHash,
        extraDataItemsCount=extraDataItemsCount,
        extraDataList=extraDataList
    )


StakingModuleId = NewType('StakingModuleId', int)
NodeOperatorId = NewType('NodeOperatorId', int)
NodeOperatorGlobalIndex = Tuple[StakingModuleId, NodeOperatorId]


def node_operator(module_id, node_operator_id) -> NodeOperatorGlobalIndex:
    return module_id, node_operator_id


@pytest.fixture(scope="module")
def nor(accounts, interface):
    return interface.NodeOperatorsRegistry(contracts.node_operators_registry.address)


def test_node_operator_normal_report(
        nor, accounts, extra_data_service, voting_eoa
):
    penalty_delay = nor.getStuckPenaltyDelay()

    node_operator_first = nor.getNodeOperatorSummary(0)
    address_first = nor.getNodeOperator(0, False)['rewardAddress']

    node_operator_second = nor.getNodeOperatorSummary(1)
    address_second = nor.getNodeOperator(1, False)['rewardAddress']

    node_operator_third = nor.getNodeOperatorSummary(2)
    address_third = nor.getNodeOperator(2, False)['rewardAddress']

    assert contracts.lido.balanceOf(address_first) == 21873108333133797622
    assert contracts.lido.balanceOf(address_second) == 113089997075720349764
    assert contracts.lido.balanceOf(address_third) == 32478609417541091991

# First report - base
    oracle_report()

    # TODO: add calc of expected NO balace (now it is + ~10)
    assert contracts.lido.balanceOf(address_first) == 31165004784634247170
    assert contracts.lido.balanceOf(address_second) == 114421525910389078269
    assert contracts.lido.balanceOf(address_third) == 41777664582273516463

    vals_stuck_non_zero = {
        node_operator(1, 0): 2,
        node_operator(1, 1): 2,
    }
    vals_exited_non_zero = {
        node_operator(1, 0): 5,
        node_operator(1, 1): 5,
    }

    extra_data = extra_data_service.collect(
        vals_stuck_non_zero, vals_exited_non_zero, 10, 10)

# Second report - 0 and 1 has stuck/exited
    (report_tx, extra_report_tx) = oracle_report(
        1000, 1, extra_data.data_hash, 2, extra_data.extra_data)

    node_operator_first = nor.getNodeOperatorSummary(0)
    node_operator_second = nor.getNodeOperatorSummary(1)

    assert node_operator_first['stuckValidatorsCount'] == 2
    assert node_operator_first['totalExitedValidators'] == 5
    assert node_operator_first['refundedValidatorsCount'] == 0
    assert node_operator_first['totalDepositedValidators'] == 7391
    assert node_operator_first['stuckPenaltyEndTimestamp'] == 0

    assert node_operator_second['stuckValidatorsCount'] == 2
    assert node_operator_second['totalExitedValidators'] == 5
    assert node_operator_second['refundedValidatorsCount'] == 0
    assert node_operator_second['totalDepositedValidators'] == 1000
    assert node_operator_first['stuckPenaltyEndTimestamp'] == 0

    print('2 ------ extra_report_tx', extra_report_tx.events)

    assert extra_report_tx.events['ExitedSigningKeysCountChanged'][0]['nodeOperatorId'] == 0
    assert extra_report_tx.events['ExitedSigningKeysCountChanged'][0]['exitedValidatorsCount'] == 5

    assert extra_report_tx.events['ExitedSigningKeysCountChanged'][1]['nodeOperatorId'] == 1
    assert extra_report_tx.events['ExitedSigningKeysCountChanged'][1]['exitedValidatorsCount'] == 5

    assert extra_report_tx.events['StuckPenaltyStateChanged'][0]['nodeOperatorId'] == 0
    assert extra_report_tx.events['StuckPenaltyStateChanged'][0]['stuckValidatorsCount'] == 2

    assert extra_report_tx.events['StuckPenaltyStateChanged'][1]['nodeOperatorId'] == 1
    assert extra_report_tx.events['StuckPenaltyStateChanged'][1]['stuckValidatorsCount'] == 2

    # print('------------', 31186041162863875287 - 31165004784634247170)
    # print('------------', 114498760440378590897 - 114421525910389078269)
    # print('------------', 41805864505866551087 - 41777664582273516463)

    # increase 21036378229628117 ~ 0.021
    assert contracts.lido.balanceOf(address_first) == 31186041162863875287
    # increase 77234529989512628 ~ 0.077
    assert contracts.lido.balanceOf(address_second) == 114498760440378590897
    # increase 28199923593034624 ~ 0.028
    assert contracts.lido.balanceOf(address_third) == 41805864505866551087

# Deposite TODO

    # depositCallCountBefore = deposit_contract.totalCalls()
    # stakingModuleSummaryBefore = nor.getStakingModuleSummary()

    # lido = interface.Lido(lido_dao_steth_address)
    # lido.depositBufferedEther(
    #     {'from': accounts[0]})

    # depositCallCount = deposit_contract.totalCalls()
    # stakingModuleSummary = nor.getStakingModuleSummary()

    # balances after deposit
    assert contracts.lido.balanceOf(address_first) == 31186041162863875287
    assert contracts.lido.balanceOf(address_second) == 114498760440378590897
    assert contracts.lido.balanceOf(address_third) == 41805864505866551087

    # Report with node operator 0 exited 2 + 5 keys an stuck 0
    vals_stuck_non_zero = {
        node_operator(1, 0): 0,
        node_operator(1, 1): 2,
    }
    vals_exited_non_zero = {
        node_operator(1, 0): 7,
    }
    extra_data = extra_data_service.collect(
        vals_stuck_non_zero, vals_exited_non_zero, 10, 10)

# Third report - 0: increase stuck to 0, desc exited to 7 = 5 + 2
# 1: same as prev report
    (report_tx, extra_report_tx) = oracle_report(
        1000, 1, extra_data.data_hash, 2, extra_data.extra_data)

    node_operator_first = nor.getNodeOperatorSummary(0)
    node_operator_second = nor.getNodeOperatorSummary(1)

    assert node_operator_first['stuckValidatorsCount'] == 0
    assert node_operator_first['totalExitedValidators'] == 7
    assert node_operator_first['refundedValidatorsCount'] == 0
    assert node_operator_first['totalDepositedValidators'] == 7391
    assert node_operator_first['stuckPenaltyEndTimestamp'] > 0

    assert node_operator_second['stuckValidatorsCount'] == 2
    assert node_operator_second['totalExitedValidators'] == 5
    assert node_operator_second['refundedValidatorsCount'] == 0
    assert node_operator_second['totalDepositedValidators'] == 1000
    assert node_operator_first['stuckPenaltyEndTimestamp'] > 0

    print('3 ------ extra_report_tx', extra_report_tx.events)

    assert extra_report_tx.events['ExitedSigningKeysCountChanged'][0]['nodeOperatorId'] == 0
    assert extra_report_tx.events['ExitedSigningKeysCountChanged'][0]['exitedValidatorsCount'] == 7

    assert extra_report_tx.events['StuckPenaltyStateChanged'][0]['nodeOperatorId'] == 0
    assert extra_report_tx.events['StuckPenaltyStateChanged'][0]['stuckValidatorsCount'] == 0

    stuckPenaltyEndTimestamp = extra_report_tx.events[
        'StuckPenaltyStateChanged'][0]['stuckPenaltyEndTimestamp']

    # TODO: clac balances after report
    # increase 21050577784933116 ~ 0.021
    assert contracts.lido.balanceOf(address_first) == 31207091740648808403
    # increase 77286663297255549 ~ 0.077
    assert contracts.lido.balanceOf(address_second) == 114576047103675846446
    # increase 28218958541459922 ~ 0.028
    assert contracts.lido.balanceOf(address_third) == 41834083464408011009


# sleep PENALTY_DELAY time
    # chain.sleep(stuckPenaltyEndTimestamp -
    #             web3.eth.get_block("latest").timestamp + 1)
    chain.sleep(penalty_delay + 1)
    chain.mine()

    vals_stuck_non_zero = {
        node_operator(1, 1): 2,
    }
    vals_exited_non_zero = {
        node_operator(1, 1): 5,
    }
    extra_data = extra_data_service.collect(
        vals_stuck_non_zero, vals_exited_non_zero, 10, 10)

# Fourth report - 1: has stuck 2 keys
    (report_tx, extra_report_tx) = oracle_report(
        1000, 1, extra_data.data_hash, 2, extra_data.extra_data)

    node_operator_first = nor.getNodeOperatorSummary(0)
    node_operator_second = nor.getNodeOperatorSummary(1)

    assert node_operator_first['stuckValidatorsCount'] == 0
    assert node_operator_first['totalExitedValidators'] == 7
    assert node_operator_first['refundedValidatorsCount'] == 0
    assert node_operator_first['totalDepositedValidators'] == 7391
    assert node_operator_first['stuckPenaltyEndTimestamp'] > 0

    assert node_operator_second['stuckValidatorsCount'] == 2
    assert node_operator_second['totalExitedValidators'] == 5
    assert node_operator_second['refundedValidatorsCount'] == 0
    assert node_operator_second['totalDepositedValidators'] == 1000
    assert node_operator_first['stuckPenaltyEndTimestamp'] > 0

    print('4 ------ extra_report_tx', extra_report_tx.events)

    # print('------------', 31228156527573746349 - 31207091740648808403)
    # print('------------', 114653385935470827642 - 114576047103675846446)
    # print('------------', 41862321470746486416 - 41834083464408011009)

    # TODO: clac balances after report
    # increase 21064786924937946 ~ 0.021
    assert contracts.lido.balanceOf(address_first) == 31228156527573746349
    # increase 77338831794981196 ~ 0.077
    assert contracts.lido.balanceOf(address_second) == 114653385935470827642
    # increase 28238006338475407 ~ 0.028
    assert contracts.lido.balanceOf(address_third) == 41862321470746486416

# Deposite TODO

    # Refund keys
    nor.updateRefundedValidatorsCount(
        1, 2, {"from": lido_dao_staking_router})

# Fifth report
    (report_tx, extra_report_tx) = oracle_report(1000)

    print('5 ------ extra_report_tx', extra_report_tx.events)

    node_operator_first = nor.getNodeOperatorSummary(0)
    node_operator_second = nor.getNodeOperatorSummary(1)

    assert node_operator_first['stuckValidatorsCount'] == 0
    assert node_operator_first['totalExitedValidators'] == 7
    assert node_operator_first['refundedValidatorsCount'] == 0
    assert node_operator_first['totalDepositedValidators'] == 7391
    assert node_operator_first['stuckPenaltyEndTimestamp'] > 0

    assert node_operator_second['stuckValidatorsCount'] == 2
    assert node_operator_second['totalExitedValidators'] == 5
    assert node_operator_second['refundedValidatorsCount'] == 2
    assert node_operator_second['totalDepositedValidators'] == 1000
    assert node_operator_first['stuckPenaltyEndTimestamp'] > 0

    # print('------------', 31249235533229858627 - 31228156527573746349)
    # print('------------', 114730776970977270451 - 114653385935470827642)
    # print('------------', 41890578537739240295 - 41862321470746486416)

    # TODO: clac balances after report
    # increase 21079005656112278 ~ 0.021
    assert contracts.lido.balanceOf(address_first) == 31249235533229858627
    # increase 77391035506442809 ~ 0.077
    assert contracts.lido.balanceOf(address_second) == 114730776970977270451
    # increase 28257066992753879 ~ 0.028
    assert contracts.lido.balanceOf(address_third) == 41890578537739240295

    # getStuckPenaltyDelay
    # isOperatorPenaltyCleared
    print('------------ getStuckPenaltyDelay', nor.getStuckPenaltyDelay())

    chain.sleep(penalty_delay + 1)

# Seventh report
    (report_tx, extra_report_tx) = oracle_report(1000)

    node_operator_first = nor.getNodeOperatorSummary(0)
    node_operator_second = nor.getNodeOperatorSummary(1)

    assert node_operator_first['stuckValidatorsCount'] == 0
    assert node_operator_first['totalExitedValidators'] == 7
    assert node_operator_first['refundedValidatorsCount'] == 0
    assert node_operator_first['totalDepositedValidators'] == 7391
    assert node_operator_first['stuckPenaltyEndTimestamp'] > 0

    assert node_operator_second['stuckValidatorsCount'] == 2
    assert node_operator_second['totalExitedValidators'] == 5
    assert node_operator_second['refundedValidatorsCount'] == 2
    assert node_operator_second['totalDepositedValidators'] == 1000
    assert node_operator_first['stuckPenaltyEndTimestamp'] > 0

    # TODO: clac balances after report
    # increase 21079005656112278 ~ 0.021
    assert contracts.lido.balanceOf(address_first) == 31249235533229858627
    # increase 77391035506442809 ~ 0.077
    assert contracts.lido.balanceOf(address_second) == 114730776970977270451
    # increase 28257066992753879 ~ 0.028
    assert contracts.lido.balanceOf(address_third) == 41890578537739240295

# Deposite TODO
