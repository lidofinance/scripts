import pytest
from brownie import chain
from hexbytes import HexBytes
from typing import NewType, Tuple

from utils.test.extra_data import (
    ExtraDataService,
)
from utils.test.helpers import (
    ETH,
    eth_balance,
    steth_balance
)
from utils.test.oracle_report_helpers import (
    ONE_DAY,
    SHARE_RATE_PRECISION,
    push_oracle_report,
    get_finalization_batches,
    simulate_report,
    wait_to_next_available_report_time,
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


def test_node_operators(
        nor, accounts, extra_data_service, voting_eoa
):
    penalty_delay = nor.getStuckPenaltyDelay()

    node_operator_first = nor.getNodeOperatorSummary(0)
    address_first = nor.getNodeOperator(0, False)['rewardAddress']

    node_operator_second = nor.getNodeOperatorSummary(1)
    address_second = nor.getNodeOperator(1, False)['rewardAddress']

    node_operator_third = nor.getNodeOperatorSummary(2)
    address_base_no = nor.getNodeOperator(2, False)['rewardAddress']

    assert steth_balance(address_first) == 16358968722850069260
    assert steth_balance(address_second) == 1
    assert steth_balance(address_base_no) == 36971193293606281302

# First report - base
    oracle_report()

    # print('------------', 25640665277143807417 - 16358968722850069260)
    # print('------------', 1254316635151645834 - 1)
    # print('------------', 46266803099485279902 - 36971193293606281302)

    # TODO: add calc of expected NO balace (now it is + ~10)
    # increase 9281696554293738157 ~ 9.28
    assert steth_balance(address_first) == 25640665277143807417
    # increase 9281696554293738157 ~ 1.25
    assert steth_balance(address_second) == 1254316635151645834
    # increase 9295609805878998600 ~ 9.29
    assert steth_balance(address_base_no) == 46266803099485279902

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

# Second report - 0 NO and 1 NO has stuck/exited
    (report_tx, extra_report_tx) = oracle_report(
        1000, 1, extra_data.data_hash, 2, extra_data.extra_data)

    node_operator_first = nor.getNodeOperatorSummary(0)
    node_operator_second = nor.getNodeOperatorSummary(1)
    node_operator_base = nor.getNodeOperatorSummary(2)

    assert node_operator_base['stuckValidatorsCount'] == 0
    assert node_operator_base['totalExitedValidators'] == 0
    assert node_operator_base['refundedValidatorsCount'] == 0
    assert node_operator_base['totalDepositedValidators'] == 7391
    assert node_operator_base['stuckPenaltyEndTimestamp'] == 0

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

    # print('------------', 25657972726205879487 - 25640665277143807417)
    # print('------------', 1255163298880373195 - 1254316635151645834)
    # print('------------', 46298033191577432466 - 46266803099485279902)

    # increase 17307449062072070 ~ 0.017
    assert steth_balance(address_first) == 25657972726205879487
    # increase 846663728727361 ~ 0.0008
    assert steth_balance(address_second) == 1255163298880373195
    # increase 31230092092152564 ~ 0.031
    assert steth_balance(address_base_no) == 46298033191577432466

# Deposite TODO

    # depositCallCountBefore = deposit_contract.totalCalls()
    # stakingModuleSummaryBefore = nor.getStakingModuleSummary()

    # lido = interface.Lido(lido_dao_steth_address)
    # lido.depositBufferedEther(
    #     {'from': accounts[0]})

    # depositCallCount = deposit_contract.totalCalls()
    # stakingModuleSummary = nor.getStakingModuleSummary()

    # balances after deposit
    assert steth_balance(address_first) == 25657972726205879487
    assert steth_balance(address_second) == 1255163298880373195
    assert steth_balance(address_base_no) == 46298033191577432466

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

# Third report - 0 NO: increase stuck to 0, desc exited to 7 = 5 + 2
# 1 NO: same as prev report
    (report_tx, extra_report_tx) = oracle_report(
        1000, 1, extra_data.data_hash, 2, extra_data.extra_data)

    node_operator_first = nor.getNodeOperatorSummary(0)
    node_operator_second = nor.getNodeOperatorSummary(1)

    assert node_operator_base['stuckPenaltyEndTimestamp'] == 0

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

    # print('------------', 25675291857796068456 - 25657972726205879487)
    # print('------------', 1256010534107117447 - 1255163298880373195)
    # print('------------', 46329284363981747233 - 46298033191577432466)

    # TODO: clac balances after report
    # increase 17319131590188969 ~ 0.017
    assert steth_balance(address_first) == 25675291857796068456
    # increase 847235226744252 ~ 0.0008
    assert steth_balance(address_second) == 1256010534107117447
    # increase 31251172404314767 ~ 0.031
    assert steth_balance(address_base_no) == 46329284363981747233


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

# Fourth report - 1 NO: has stuck 2 keys
    (report_tx, extra_report_tx) = oracle_report(
        1000, 1, extra_data.data_hash, 2, extra_data.extra_data)

    node_operator_first = nor.getNodeOperatorSummary(0)
    node_operator_second = nor.getNodeOperatorSummary(1)

    assert node_operator_base['stuckPenaltyEndTimestamp'] == 0

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

    # print('------------', 25692622679800080802 - 25675291857796068456)
    # print('------------', 1256858341217639752 - 1256010534107117447)
    # print('------------', 46360556630927434913 - 46329284363981747233)

    # TODO: clac balances after report
    # increase 17330822004012346 ~ 0.017
    assert steth_balance(address_first) == 25692622679800080802
    # increase 847807110522305 ~ 0.0008
    assert steth_balance(address_second) == 1256858341217639752
    # increase 31272266945687680 ~ 0.031
    assert steth_balance(address_base_no) == 46360556630927434913

# Deposite TODO

    # Refund keys 1 NO
    nor.updateRefundedValidatorsCount(
        1, 2, {"from": lido_dao_staking_router})

# Fifth report
    (report_tx, extra_report_tx) = oracle_report(1000)

    print('5 ------ extra_report_tx', extra_report_tx.events)

    node_operator_first = nor.getNodeOperatorSummary(0)
    node_operator_second = nor.getNodeOperatorSummary(1)

    assert node_operator_base['stuckPenaltyEndTimestamp'] == 0

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

    # print('------------', 25709965200108945857 - 25692622679800080802)
    # print('------------', 1257706720597961658 - 1256858341217639752)
    # print('------------', 46391850006653310931 - 46360556630927434913)

    # TODO: clac balances after report
    # increase 17342520308865055 ~ 0.017
    assert steth_balance(address_first) == 25709965200108945857
    # increase 848379380321906 ~ 0.0008
    assert steth_balance(address_second) == 1257706720597961658
    # increase 31293375725876018 ~ 0.031
    assert steth_balance(address_base_no) == 46391850006653310931

    # getStuckPenaltyDelay
    # isOperatorPenaltyCleared
    print('------------ getStuckPenaltyDelay', nor.getStuckPenaltyDelay())

    chain.sleep(penalty_delay + 1)
    chain.mine()

# Seventh report
    (report_tx, extra_report_tx) = oracle_report(1000)

    node_operator_first = nor.getNodeOperatorSummary(0)
    node_operator_second = nor.getNodeOperatorSummary(1)

    assert node_operator_base['stuckPenaltyEndTimestamp'] == 0

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

    # print('------------', 25727319426619019395 - 25692622679800080802)
    # print('------------', 1258555672634365283 - 1256858341217639752)
    # print('------------', 46423164505407801916 - 46360556630927434913)

    # TODO: clac balances after report
    # increase 34696746818938593 ~ 0.034
    assert steth_balance(address_first) == 25727319426619019395
    # increase 1697331416725531 ~ 0.0001
    assert steth_balance(address_second) == 1258555672634365283
    # increase 62607874480367003 ~ 0.062
    assert steth_balance(address_base_no) == 46423164505407801916

# Deposite TODO
