import math

import pytest
from brownie import chain, interface, web3  # type: ignore
from eth_abi.abi import encode
from hexbytes import HexBytes

from utils.config import (
    contracts,
    lido_dao_accounting_oracle,
    lido_dao_accounting_oracle_implementation,
    lido_dao_hash_consensus_for_accounting_oracle,
    oracle_committee,
)

ZERO_HASH = bytes([0] * 32)
ZERO_BYTES32 = HexBytes(ZERO_HASH)
ONE_DAY = 1 * 24 * 60 * 60
SHARE_RATE_PRECISION = 10**27


def ETH(amount):
    return math.floor(amount * 10**18)


def SHARES(amount):
    return ETH(amount)


@pytest.fixture(scope="module")
def holder(accounts):
    whale = "0x41318419CFa25396b47A94896FfA2C77c6434040"
    contracts.lido.transfer(accounts[0], ETH(101), {"from": whale})
    return accounts[0]


def steth_balance(account):
    return contracts.lido.balanceOf(account)


def almostEqEth(b1, b2):
    return abs(b1 - b2) < 10


def advance_chain_time(time):
    chain.sleep(time)
    chain.mine(1)


def prepare_report(
    refSlot,
    numValidators,
    clBalance,
    withdrawalVaultBalance,
    elRewardsVaultBalance,
    sharesRequestedToBurn,
    simulatedShareRate,
    stakingModuleIdsWithNewlyExitedValidators=[],
    numExitedValidatorsByStakingModule=[],
    consensusVersion=1,
    withdrawalFinalizationBatches=[],
    isBunkerMode=False,
    extraDataFormat=0,
    extraDataHash=ZERO_BYTES32,
    extraDataItemsCount=0,
):
    items = (
        int(consensusVersion),
        int(refSlot),
        int(numValidators),
        int(clBalance // (10**9)),
        [int(i) for i in stakingModuleIdsWithNewlyExitedValidators],
        [int(i) for i in numExitedValidatorsByStakingModule],
        int(withdrawalVaultBalance),
        int(elRewardsVaultBalance),
        int(sharesRequestedToBurn),
        [int(i) for i in withdrawalFinalizationBatches],
        int(simulatedShareRate),
        bool(isBunkerMode),
        int(extraDataFormat),
        extraDataHash,
        int(extraDataItemsCount),
    )
    report_data_abi = [
        "uint256",
        "uint256",
        "uint256",
        "uint256",
        "uint256[]",
        "uint256[]",
        "uint256",
        "uint256",
        "uint256",
        "uint256[]",
        "uint256",
        "bool",
        "uint256",
        "bytes32",
        "uint256",
    ]
    report_str_abi = ",".join(report_data_abi)
    encoded = encode([f"({report_str_abi})"], [items])
    hash = web3.keccak(encoded)
    return (items, hash)


def get_finalization_batches(share_rate: int, withdrawal_vault_balance, el_rewards_vault_balance) -> list[int]:
    buffered_ether = contracts.lido.getBufferedEther()
    unfinalized_steth = contracts.withdrawal_queue.unfinalizedStETH()
    reserved_buffer = min(buffered_ether, unfinalized_steth)
    available_eth = withdrawal_vault_balance + el_rewards_vault_balance + reserved_buffer
    max_timestamp = chain.time()

    batchesState = contracts.withdrawal_queue.calculateFinalizationBatches(
        share_rate, max_timestamp, 10000, (available_eth, False, [0 for _ in range(36)], 0)
    )

    while not batchesState[1]:  # batchesState.finished
        batchesState = contracts.withdrawal_queue.calculateFinalizationBatches(
            share_rate, max_timestamp, 10000, batchesState
        )

    return list(filter(lambda value: value > 0, batchesState[2]))


def reach_consensus(slot, report, version):
    (members, *_) = contracts.hash_consensus_for_accounting_oracle.getFastLaneMembers()
    for member in members:
        contracts.hash_consensus_for_accounting_oracle.submitReport(slot, report, version, {"from": member})
    (_, hash_, _) = contracts.hash_consensus_for_accounting_oracle.getConsensusState()
    assert hash_ == report.hex(), "HashConsensus points to unexpected report"
    return members[0]


def push_oracle_report(
    clBalance,
    numValidators,
    withdrawalVaultBalance,
    elRewardsVaultBalance,
    sharesRequestedToBurn,
    simulatedShareRate,
    stakingModuleIdsWithNewlyExitedValidators=[],
    numExitedValidatorsByStakingModule=[],
    withdrawalFinalizationBatches=[],
    isBunkerMode=False,
    extraDataFormat=0,
    extraDataHash=ZERO_BYTES32,
    extraDataItemsCount=0,
):
    (refSlot, *_) = contracts.hash_consensus_for_accounting_oracle.getCurrentFrame()
    consensusVersion = contracts.accounting_oracle.getConsensusVersion()
    oracleVersion = contracts.accounting_oracle.getContractVersion()
    (items, hash) = prepare_report(
        refSlot,
        numValidators,
        clBalance,
        withdrawalVaultBalance,
        elRewardsVaultBalance,
        sharesRequestedToBurn,
        simulatedShareRate,
        stakingModuleIdsWithNewlyExitedValidators,
        numExitedValidatorsByStakingModule,
        consensusVersion,
        withdrawalFinalizationBatches,
        isBunkerMode,
        extraDataFormat,
        extraDataHash,
        extraDataItemsCount,
    )
    submitter = reach_consensus(refSlot, hash, consensusVersion)
    report_tx = contracts.accounting_oracle.submitReportData(items, oracleVersion, {"from": submitter})
    extra_report_tx = contracts.accounting_oracle.submitReportExtraDataEmpty({"from": submitter})
    return (report_tx, extra_report_tx)


def oracle_report():
    advance_chain_time(ONE_DAY)
    (SLOTS_PER_EPOCH, SECONDS_PER_SLOT, GENESIS_TIME) = contracts.hash_consensus_for_accounting_oracle.getChainConfig()
    (refSlot, reportProcessingDeadlineSlot) = contracts.hash_consensus_for_accounting_oracle.getCurrentFrame()
    reportTime = GENESIS_TIME + refSlot * SECONDS_PER_SLOT

    elRewardsVaultBalance = web3.eth.getBalance(contracts.execution_layer_rewards_vault.address)
    withdrawalVaultBalance = web3.eth.getBalance(contracts.withdrawal_vault.address)
    totalSharesBefore = contracts.lido.getTotalShares()
    (depositedValidators, beaconValidators, beaconBalance) = contracts.lido.getBeaconStat()
    balanceBufferBefore = contracts.lido.getBufferedEther()
    totalPooledBefore = contracts.lido.getTotalPooledEther()
    withdrawalSharePrice = contracts.lido.getPooledEthByShares(SHARES(1))

    postCLBalance = beaconBalance + ETH(10)

    (postTotalPooledEther, postTotalShares, withdrawals, elRewards) = contracts.lido.handleOracleReport.call(
        reportTime,
        ONE_DAY,
        beaconValidators,
        postCLBalance,
        withdrawalVaultBalance,
        elRewardsVaultBalance,
        0,
        [],
        0,
        {"from": contracts.accounting_oracle.address},
    )
    simulatedShareRate = postTotalPooledEther * SHARE_RATE_PRECISION // postTotalShares
    (coverShares, nonCoverShares) = contracts.burner.getSharesRequestedToBurn()
    sharesRequestedToBurn = coverShares + nonCoverShares

    finalization_batches = get_finalization_batches(simulatedShareRate, withdrawals, elRewards)

    push_oracle_report(
        clBalance=postCLBalance,
        numValidators=beaconValidators,
        withdrawalVaultBalance=withdrawalVaultBalance,
        sharesRequestedToBurn=sharesRequestedToBurn,
        withdrawalFinalizationBatches=finalization_batches,
        elRewardsVaultBalance=elRewardsVaultBalance,
        simulatedShareRate=simulatedShareRate,
    )


def test_withdraw(holder):
    # approve
    contracts.lido.approve(contracts.withdrawal_queue.address, ETH(100), {"from": holder})

    # request
    balance_before = steth_balance(holder)
    request_tx = contracts.withdrawal_queue.requestWithdrawals([ETH(1) for _ in range(10)], holder, {"from": holder})
    balance_after = steth_balance(holder)
    # post request checks
    assert almostEqEth(balance_before - balance_after, ETH(10))
    assert request_tx.events.count("WithdrawalRequested") == 10

    # check each request
    requests_ids = contracts.withdrawal_queue.getWithdrawalRequests(holder, {"from": holder})
    statuses = contracts.withdrawal_queue.getWithdrawalStatus(requests_ids, {"from": holder})
    claimableEther = contracts.withdrawal_queue.getClaimableEther(requests_ids, [0 for _ in requests_ids])
    assert len(requests_ids) == 10
    assert len(statuses) == 10

    for i, request_id in enumerate(requests_ids):
        assert i + 1 == request_id
        (amountOfStETH, amountOfShares, owner, _, isFinalized, isClaimed) = statuses[i]
        assert almostEqEth(amountOfStETH, ETH(1))
        assert almostEqEth(amountOfShares, contracts.lido.getSharesByPooledEth(amountOfStETH))
        assert owner == holder
        assert not isFinalized
        assert not isClaimed
        assert claimableEther[i] == 0

    oracle_report()
