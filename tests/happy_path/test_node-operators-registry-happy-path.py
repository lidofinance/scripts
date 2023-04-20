import math
import pytest
import random
from brownie import web3, interface, convert, reverts, chain
from utils.config import contracts
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
from utils.config import (contracts)

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


def oracle_report(extraDataFormat=0, extraDataHash=ZERO_BYTES32, extraDataItemsCount=0, extraDataList=''):
    wait_to_next_available_report_time()

    (refSlot, _) = contracts.hash_consensus_for_accounting_oracle.getCurrentFrame()
    elRewardsVaultBalance = eth_balance(
        contracts.execution_layer_rewards_vault.address)
    withdrawalVaultBalance = eth_balance(contracts.withdrawal_vault.address)
    (coverShares, nonCoverShares) = contracts.burner.getSharesRequestedToBurn()

    prev_report = contracts.lido.getBeaconStat().dict()
    beacon_validators = prev_report["beaconValidators"]
    beacon_balance = prev_report["beaconBalance"]
    buffered_ether_before = contracts.lido.getBufferedEther()

    print("beaconBalance", beacon_balance)
    print("beaconValidators", beacon_validators)
    print("withdrawalVaultBalance", withdrawalVaultBalance)
    print("elRewardsVaultBalance", elRewardsVaultBalance)

    postCLBalance = beacon_balance

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

    tx = push_oracle_report(
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
    print("tx", tx)


StakingModuleId = NewType('StakingModuleId', int)
NodeOperatorId = NewType('NodeOperatorId', int)
NodeOperatorGlobalIndex = Tuple[StakingModuleId, NodeOperatorId]


def node_operator(module_id, node_operator_id) -> NodeOperatorGlobalIndex:
    return module_id, node_operator_id


@pytest.fixture(scope="module")
def nor(accounts, interface):
    return interface.NodeOperatorsRegistry(contracts.node_operators_registry.address)


def test_node_operator_normal_report(
        nor, accounts, extra_data_service
):
    node_operator_first = nor.getNodeOperatorSummary(0)
    address_first = nor.getNodeOperator(0, False)['rewardAddress']

    node_operator_second = nor.getNodeOperatorSummary(1)
    address_second = nor.getNodeOperator(1, False)['rewardAddress']

    assert contracts.lido.balanceOf(address_first) == 21873108333133797622
    assert contracts.lido.balanceOf(address_second) == 113089997075720349764

    oracle_report()

    # TODO: add calc of expected NO balace (now it is + 10 ETH)
    assert contracts.lido.balanceOf(address_first) == 31165004784634247170
    assert contracts.lido.balanceOf(address_second) == 114421525910389078269

    assert contracts.lido.balanceOf(INITIAL_TOKEN_HOLDER) > 0

    node_operator_first = nor.getNodeOperatorSummary(0)
    address_first = nor.getNodeOperator(0, False)['rewardAddress']

    node_operator_second = nor.getNodeOperatorSummary(1)
    address_second = nor.getNodeOperator(1, False)['rewardAddress']

    assert contracts.lido.balanceOf(address_first) == 31165004784634247170
    assert contracts.lido.balanceOf(address_second) == 114421525910389078269

    extraData = {
        'exitedKeys': [{'moduleId': 1, 'nodeOpIds': [0], 'keysCounts': [2]}],
        'stuckKeys': [{'moduleId': 1, 'nodeOpIds': [1, 2], 'keysCounts': [1, 1]}]
    }

    vals_stuck_non_zero = {
        node_operator(1, 0): 1,
    }
    vals_exited_non_zero = {
        node_operator(1, 0): 2,
    }

    extra_data = extra_data_service.collect(
        vals_stuck_non_zero, vals_exited_non_zero, 10, 10)

    oracle_report(1, extra_data.data_hash, 2, extra_data.extra_data)
