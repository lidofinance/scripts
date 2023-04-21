import pytest
from brownie import chain
from hexbytes import HexBytes
from typing import NewType, Tuple

from utils.test.extra_data import (
    ExtraDataService,
)
from utils.test.helpers import (
    steth_balance
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


def test_node_operators(
        nor, accounts, extra_data_service, voting_eoa
):
    first_tested_no_id = 0
    second_tested_no_id = 4
    base_no_id = 2

    first_tested_no_keys = 7391
    second_tested_no_keys = 7391
    base_no_keys = 7391

    penalty_delay = nor.getStuckPenaltyDelay()

    node_operator_first = nor.getNodeOperatorSummary(first_tested_no_id)
    address_first = nor.getNodeOperator(
        first_tested_no_id, False)['rewardAddress']

    node_operator_second = nor.getNodeOperatorSummary(second_tested_no_id)
    address_second = nor.getNodeOperator(
        second_tested_no_id, False)['rewardAddress']

    node_operator_base = nor.getNodeOperatorSummary(base_no_id)
    address_base_no = nor.getNodeOperator(base_no_id, False)['rewardAddress']

    assert steth_balance(address_first) == 16358968722850069260
    assert steth_balance(address_second) == 97610994862333549973
    assert steth_balance(address_base_no) == 36971193293606281302

# First report - base
    oracle_report()

    # print('------------', 25640665277143807417 - 16358968722850069260)
    # print('------------', 106947536534271439480 - 97610994862333549973)
    # print('------------', 46266803099485279902 - 36971193293606281302)

    # TODO: add calc of expected NO balace (now it is + ~10)
    # increase 9281696554293738157 ~ 9.28
    assert steth_balance(address_first) == 25640665277143807417
    # increase 9336541671937889507> ~ 9.33
    assert steth_balance(address_second) == 106947536534271439480
    # increase 9295609805878998600 ~ 9.29
    assert steth_balance(address_base_no) == 46266803099485279902

    vals_stuck_non_zero = {
        node_operator(1, first_tested_no_id): 2,
        node_operator(1, second_tested_no_id): 2,
    }
    vals_exited_non_zero = {
        node_operator(1, first_tested_no_id): 5,
        node_operator(1, second_tested_no_id): 5,
    }

    extra_data = extra_data_service.collect(
        vals_stuck_non_zero, vals_exited_non_zero, 10, 10)

# Second report - 0 NO and 1 NO has stuck/exited
    (report_tx, extra_report_tx) = oracle_report(
        1000, False, None, 1, extra_data.data_hash, 2, extra_data.extra_data)

    node_operator_first = nor.getNodeOperatorSummary(first_tested_no_id)
    node_operator_second = nor.getNodeOperatorSummary(second_tested_no_id)
    node_operator_base = nor.getNodeOperatorSummary(base_no_id)

    assert node_operator_base['stuckValidatorsCount'] == 0
    assert node_operator_base['totalExitedValidators'] == 0
    assert node_operator_base['refundedValidatorsCount'] == 0
    assert node_operator_base['totalDepositedValidators'] == base_no_keys
    assert node_operator_base['stuckPenaltyEndTimestamp'] == 0

    assert node_operator_first['stuckValidatorsCount'] == 2
    assert node_operator_first['totalExitedValidators'] == 5
    assert node_operator_first['refundedValidatorsCount'] == 0
    assert node_operator_first['totalDepositedValidators'] == first_tested_no_keys
    assert node_operator_first['stuckPenaltyEndTimestamp'] == 0

    assert node_operator_second['stuckValidatorsCount'] == 2
    assert node_operator_second['totalExitedValidators'] == 5
    assert node_operator_second['refundedValidatorsCount'] == 0
    assert node_operator_second['totalDepositedValidators'] == second_tested_no_keys
    assert node_operator_second['stuckPenaltyEndTimestamp'] == 0

    print('2 ------ extra_report_tx', extra_report_tx.events)

    assert extra_report_tx.events['ExitedSigningKeysCountChanged'][0]['nodeOperatorId'] == first_tested_no_id
    assert extra_report_tx.events['ExitedSigningKeysCountChanged'][0]['exitedValidatorsCount'] == 5

    assert extra_report_tx.events['ExitedSigningKeysCountChanged'][1]['nodeOperatorId'] == second_tested_no_id
    assert extra_report_tx.events['ExitedSigningKeysCountChanged'][1]['exitedValidatorsCount'] == 5

    assert extra_report_tx.events['StuckPenaltyStateChanged'][0]['nodeOperatorId'] == first_tested_no_id
    assert extra_report_tx.events['StuckPenaltyStateChanged'][0]['stuckValidatorsCount'] == 2

    assert extra_report_tx.events['StuckPenaltyStateChanged'][1]['nodeOperatorId'] == second_tested_no_id
    assert extra_report_tx.events['StuckPenaltyStateChanged'][1]['stuckValidatorsCount'] == 2

    # print('------------', 25657972726205879487 - 25640665277143807417)
    # print('------------', 107019726121432072702 - 106947536534271439480)
    # print('------------', 46298033191577432466 - 46266803099485279902)

    # increase 17307449062072070 ~ 0.017
    assert steth_balance(address_first) == 25657972726205879487
    # increase 72189587160633222 ~ 0.72
    assert steth_balance(address_second) == 107019726121432072702
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
    assert steth_balance(address_second) == 107019726121432072702
    assert steth_balance(address_base_no) == 46298033191577432466

    # Report with node operator 0 exited 2 + 5 keys an stuck 0
    vals_stuck_non_zero = {
        node_operator(1, first_tested_no_id): 0,
        node_operator(1, second_tested_no_id): 2,
    }
    vals_exited_non_zero = {
        node_operator(1, first_tested_no_id): 7,
    }
    extra_data = extra_data_service.collect(
        vals_stuck_non_zero, vals_exited_non_zero, 10, 10)

# Third report - 0 NO: increase stuck to 0, desc exited to 7 = 5 + 2
# 1 NO: same as prev report
    (report_tx, extra_report_tx) = oracle_report(
        1000, False, None, 1, extra_data.data_hash, 2, extra_data.extra_data)

    node_operator_first = nor.getNodeOperatorSummary(first_tested_no_id)
    node_operator_second = nor.getNodeOperatorSummary(second_tested_no_id)

    assert node_operator_base['stuckPenaltyEndTimestamp'] == 0

    assert node_operator_first['stuckValidatorsCount'] == 0
    assert node_operator_first['totalExitedValidators'] == 7
    assert node_operator_first['refundedValidatorsCount'] == 0
    assert node_operator_first['totalDepositedValidators'] == first_tested_no_keys
    assert node_operator_first['stuckPenaltyEndTimestamp'] > 0

    assert node_operator_second['stuckValidatorsCount'] == 2
    assert node_operator_second['totalExitedValidators'] == 5
    assert node_operator_second['refundedValidatorsCount'] == 0
    assert node_operator_second['totalDepositedValidators'] == second_tested_no_keys
    assert node_operator_second['stuckPenaltyEndTimestamp'] == 0  # WHY??

    print('3 ------ extra_report_tx', extra_report_tx.events)

    assert extra_report_tx.events['ExitedSigningKeysCountChanged'][0]['nodeOperatorId'] == first_tested_no_id
    assert extra_report_tx.events['ExitedSigningKeysCountChanged'][0]['exitedValidatorsCount'] == 7

    assert extra_report_tx.events['StuckPenaltyStateChanged'][0]['nodeOperatorId'] == first_tested_no_id
    assert extra_report_tx.events['StuckPenaltyStateChanged'][0]['stuckValidatorsCount'] == 0

    stuckPenaltyEndTimestamp = extra_report_tx.events[
        'StuckPenaltyStateChanged'][0]['stuckPenaltyEndTimestamp']

    # print('------------', 25675291857796068456 - 25657972726205879487)
    # print('------------', 107091964436564039351 - 107019726121432072702)
    # print('------------', 46329284363981747233 - 46298033191577432466)

    # TODO: clac balances after report
    # increase 17319131590188969 ~ 0.017
    assert steth_balance(address_first) == 25675291857796068456
    # increase 72238315131966649 ~ 0.072
    assert steth_balance(address_second) == 107091964436564039351
    # increase 31251172404314767 ~ 0.031
    assert steth_balance(address_base_no) == 46329284363981747233


# sleep PENALTY_DELAY time
    # chain.sleep(stuckPenaltyEndTimestamp -
    #             web3.eth.get_block("latest").timestamp + 1)
    chain.sleep(penalty_delay + 1)
    chain.mine()

    vals_stuck_non_zero = {
        node_operator(1, second_tested_no_id): 2,
    }
    vals_exited_non_zero = {
        node_operator(1, second_tested_no_id): 5,
    }
    extra_data = extra_data_service.collect(
        vals_stuck_non_zero, vals_exited_non_zero, 10, 10)

# Fourth report - 1 NO: has stuck 2 keys
    (report_tx, extra_report_tx) = oracle_report(
        1000, False, None, 1, extra_data.data_hash, 2, extra_data.extra_data)

    node_operator_first = nor.getNodeOperatorSummary(first_tested_no_id)
    node_operator_second = nor.getNodeOperatorSummary(second_tested_no_id)

    assert node_operator_base['stuckPenaltyEndTimestamp'] == 0

    assert node_operator_first['stuckValidatorsCount'] == 0
    assert node_operator_first['totalExitedValidators'] == 7
    assert node_operator_first['refundedValidatorsCount'] == 0
    assert node_operator_first['totalDepositedValidators'] == first_tested_no_keys
    assert node_operator_first['stuckPenaltyEndTimestamp'] > 0

    assert node_operator_second['stuckValidatorsCount'] == 2
    assert node_operator_second['totalExitedValidators'] == 5
    assert node_operator_second['refundedValidatorsCount'] == 0
    assert node_operator_second['totalDepositedValidators'] == second_tested_no_keys
    assert node_operator_second['stuckPenaltyEndTimestamp'] == 0  # WHY??

    print('4 ------ extra_report_tx', extra_report_tx.events)

    # print('------------', 25692622679800080802 - 25675291857796068456)
    # print('------------', 107164251512558720077 - 107091964436564039351)
    # print('------------', 46360556630927434913 - 46329284363981747233)

    # TODO: clac balances after report
    # increase 17330822004012346 ~ 0.017
    assert steth_balance(address_first) == 25692622679800080802
    # increase 72238315131966649 ~ 0.072
    assert steth_balance(address_second) == 107164251512558720077
    # increase 31272266945687680 ~ 0.031
    assert steth_balance(address_base_no) == 46360556630927434913

# Deposite TODO

    # Refund keys 1 NO
    nor.updateRefundedValidatorsCount(
        4, 2, {"from": lido_dao_staking_router})

# Fifth report
    (report_tx, extra_report_tx) = oracle_report(1000)

    print('5 ------ extra_report_tx', extra_report_tx.events)

    node_operator_first = nor.getNodeOperatorSummary(first_tested_no_id)
    node_operator_second = nor.getNodeOperatorSummary(second_tested_no_id)

    assert node_operator_base['stuckPenaltyEndTimestamp'] == 0

    assert node_operator_first['stuckValidatorsCount'] == 0
    assert node_operator_first['totalExitedValidators'] == 7
    assert node_operator_first['refundedValidatorsCount'] == 0
    assert node_operator_first['totalDepositedValidators'] == first_tested_no_keys
    assert node_operator_first['stuckPenaltyEndTimestamp'] > 0

    assert node_operator_second['stuckValidatorsCount'] == 2
    assert node_operator_second['totalExitedValidators'] == 5
    assert node_operator_second['refundedValidatorsCount'] == 2
    assert node_operator_second['totalDepositedValidators'] == second_tested_no_keys
    assert node_operator_second['stuckPenaltyEndTimestamp'] > 0

    # print('------------', 25709965200108945857 - 25692622679800080802)
    # print('------------', 107236587382329697213 - 107164251512558720077)
    # print('------------', 46391850006653310931 - 46360556630927434913)

    # TODO: clac balances after report
    # increase 17342520308865055 ~ 0.017
    assert steth_balance(address_first) == 25709965200108945857
    # increase 72287075994680726 ~ 0.072
    assert steth_balance(address_second) == 107236587382329697213
    # increase 31293375725876018 ~ 0.031
    assert steth_balance(address_base_no) == 46391850006653310931

    # getStuckPenaltyDelay
    # isOperatorPenaltyCleared
    print('------------ getStuckPenaltyDelay', nor.getStuckPenaltyDelay())

    chain.sleep(penalty_delay + 1)
    chain.mine()

# Seventh report
    (report_tx, extra_report_tx) = oracle_report(1000)

    node_operator_first = nor.getNodeOperatorSummary(first_tested_no_id)
    node_operator_second = nor.getNodeOperatorSummary(second_tested_no_id)

    assert node_operator_base['stuckPenaltyEndTimestamp'] == 0

    assert node_operator_first['stuckValidatorsCount'] == 0
    assert node_operator_first['totalExitedValidators'] == 7
    assert node_operator_first['refundedValidatorsCount'] == 0
    assert node_operator_first['totalDepositedValidators'] == first_tested_no_keys
    assert node_operator_first['stuckPenaltyEndTimestamp'] > 0

    assert node_operator_second['stuckValidatorsCount'] == 2
    assert node_operator_second['totalExitedValidators'] == 5
    assert node_operator_second['refundedValidatorsCount'] == 2
    assert node_operator_second['totalDepositedValidators'] == second_tested_no_keys
    assert node_operator_second['stuckPenaltyEndTimestamp'] > 0

    # print('------------', 25727319426619019395 - 25692622679800080802)
    # print('------------', 924997828491045603113 - 107236587382329697213)
    # print('------------', 46423164505407801916 - 46360556630927434913)

    # TODO: clac balances after report
    # increase 34696746818938593 ~ 0.034
    assert steth_balance(address_first) == 25727319426619019395
    # increase 72335869770977136 ~ 0.072
    assert steth_balance(address_second) == 107308972078812769759
    # increase 62607874480367003 ~ 0.062
    assert steth_balance(address_base_no) == 46423164505407801916

# Deposite TODO and check balances
