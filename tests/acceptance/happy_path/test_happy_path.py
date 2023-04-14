import math

import pytest
from brownie import chain, accounts, web3  # type: ignore
from eth_abi.abi import encode
from hexbytes import HexBytes

from utils.config import (
    contracts,
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
        print(f"Member ${member} submitting report to hashConsensus")
        contracts.hash_consensus_for_accounting_oracle.submitReport(slot, report, version, {"from": member})
    (_, hash_, _) = contracts.hash_consensus_for_accounting_oracle.getConsensusState()
    assert hash_ == report.hex(), "HashConsensus points to unexpected report"
    return members[0]


def push_oracle_report(
    refSlot,
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
    print(f"Preparing oracle report for refSlot: ${refSlot}")
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
    print(f"Submitted report data")
    # TODO add support for extra data type 1
    extra_report_tx = contracts.accounting_oracle.submitReportExtraDataEmpty({"from": submitter})
    print(f"Submitted empty extra data report")

    (
        currentFrameRefSlot,
        _,
        mainDataHash,
        mainDataSubmitted,
        state_extraDataHash,
        state_extraDataFormat,
        extraDataSubmitted,
        state_extraDataItemsCount,
        extraDataItemsSubmitted,
    ) = contracts.accounting_oracle.getProcessingState()

    assert refSlot == currentFrameRefSlot
    assert mainDataHash == hash.hex()
    assert mainDataSubmitted
    assert state_extraDataHash == extraDataHash.hex()
    assert state_extraDataFormat == extraDataFormat
    assert extraDataSubmitted
    assert state_extraDataItemsCount == extraDataItemsCount
    assert extraDataItemsSubmitted == extraDataItemsCount
    return (report_tx, extra_report_tx)


def oracle_report():
    advance_chain_time(ONE_DAY)
    (SLOTS_PER_EPOCH, SECONDS_PER_SLOT, GENESIS_TIME) = contracts.hash_consensus_for_accounting_oracle.getChainConfig()
    (refSlot, reportProcessingDeadlineSlot) = contracts.hash_consensus_for_accounting_oracle.getCurrentFrame()
    reportTime = GENESIS_TIME + refSlot * SECONDS_PER_SLOT

    elRewardsVaultBalance = web3.eth.getBalance(contracts.execution_layer_rewards_vault.address)
    withdrawalVaultBalance = web3.eth.getBalance(contracts.withdrawal_vault.address)
    (_, beaconValidators, beaconBalance) = contracts.lido.getBeaconStat()

    postCLBalance = beaconBalance + ETH(10)

    # simulated report
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

    # calculate batches
    finalization_batches = get_finalization_batches(simulatedShareRate, withdrawals, elRewards)

    push_oracle_report(
        refSlot=refSlot,
        clBalance=postCLBalance,
        numValidators=beaconValidators,
        withdrawalVaultBalance=withdrawalVaultBalance,
        sharesRequestedToBurn=sharesRequestedToBurn,
        withdrawalFinalizationBatches=finalization_batches,
        elRewardsVaultBalance=elRewardsVaultBalance,
        simulatedShareRate=simulatedShareRate,
    )


def test_withdraw(holder):
    account = accounts.at(holder, force=True)
    REQUESTS_COUNT = 10
    REQUEST_AMOUNT = ETH(1)
    REQUESTS_SUM = REQUESTS_COUNT * REQUEST_AMOUNT

    # pre request

    no_requests = contracts.withdrawal_queue.getWithdrawalRequests(holder, {"from": holder})
    assert len(no_requests) == 0

    # request
    contracts.lido.approve(contracts.withdrawal_queue.address, REQUESTS_SUM, {"from": holder})
    steth_balance_before = steth_balance(holder)
    request_tx = contracts.withdrawal_queue.requestWithdrawals(
        [REQUEST_AMOUNT for _ in range(REQUESTS_COUNT)], holder, {"from": holder}
    )
    steth_balance_after = steth_balance(holder)
    # post request checks
    assert almostEqEth(steth_balance_before - steth_balance_after, REQUESTS_SUM)
    assert request_tx.events.count("WithdrawalRequested") == REQUESTS_COUNT

    # check each request
    requests_ids = contracts.withdrawal_queue.getWithdrawalRequests(holder, {"from": holder})
    statuses = contracts.withdrawal_queue.getWithdrawalStatus(requests_ids, {"from": holder})
    claimableEther = contracts.withdrawal_queue.getClaimableEther(requests_ids, [0 for _ in requests_ids])
    assert len(requests_ids) == REQUESTS_COUNT
    assert len(statuses) == REQUESTS_COUNT

    for i, request_id in enumerate(requests_ids):
        assert i + 1 == request_id
        (amountOfStETH, amountOfShares, owner, _, isFinalized, isClaimed) = statuses[i]
        assert almostEqEth(amountOfStETH, REQUEST_AMOUNT)
        assert almostEqEth(amountOfShares, contracts.lido.getSharesByPooledEth(amountOfStETH))
        assert owner == holder
        assert not isFinalized
        assert not isClaimed
        assert claimableEther[i] == 0

    pre_lastCheckpointIndex = contracts.withdrawal_queue.getLastCheckpointIndex()
    assert pre_lastCheckpointIndex == 0

    oracle_report()
    # post report WQ state
    assert contracts.withdrawal_queue.getLastFinalizedRequestId() == requests_ids[-1]
    lastCheckpointIndex = contracts.withdrawal_queue.getLastCheckpointIndex()
    assert lastCheckpointIndex == 1

    # post report requests cehck

    hints = contracts.withdrawal_queue.findCheckpointHints(requests_ids, 1, lastCheckpointIndex)
    assert len(hints) == REQUESTS_COUNT

    post_report_statuses = contracts.withdrawal_queue.getWithdrawalStatus(requests_ids, {"from": holder})
    post_report_claimableEther = contracts.withdrawal_queue.getClaimableEther(requests_ids, hints)

    for i, request_id in enumerate(requests_ids):
        assert i + 1 == request_id
        (amountOfStETH, amountOfShares, owner, _, isFinalized, isClaimed) = post_report_statuses[i]
        assert amountOfStETH == statuses[i][0]  # amountOfShares remains unchanged
        assert amountOfShares == statuses[i][1]  # amountOfShares remains unchanged
        assert owner == holder
        assert isFinalized
        assert not isClaimed
        assert almostEqEth(post_report_claimableEther[i], REQUEST_AMOUNT)
        # single first finalization hint is 1
        assert hints[i] == 1

    # claim
    claim_balance_before = account.balance()
    claim_tx = contracts.withdrawal_queue.claimWithdrawals(requests_ids, hints, {"from": holder})
    assert claim_tx.events.count("WithdrawalClaimed") == REQUESTS_COUNT
    claim_balance_after = account.balance()
    assert almostEqEth(
        claim_balance_after - claim_balance_before + claim_tx.gas_used * claim_tx.gas_price, REQUESTS_SUM
    )

    post_claim_statuses = contracts.withdrawal_queue.getWithdrawalStatus(requests_ids, {"from": holder})
    post_claim_claimableEther = contracts.withdrawal_queue.getClaimableEther(requests_ids, hints)

    for i, request_id in enumerate(requests_ids):
        assert i + 1 == request_id
        (amountOfStETH, amountOfShares, owner, _, isFinalized, isClaimed) = post_claim_statuses[i]
        assert amountOfStETH == statuses[i][0]  # amountOfShares remains unchanged
        assert amountOfShares == statuses[i][1]  # amountOfShares remains unchanged
        assert owner == holder
        assert isFinalized
        assert isClaimed
        assert almostEqEth(post_report_claimableEther[i], REQUEST_AMOUNT)
        assert post_claim_claimableEther[i] == 0
