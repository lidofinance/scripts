from brownie import chain, web3  # type: ignore
from eth_abi.abi import encode
from hexbytes import HexBytes

from utils.config import (
    contracts,
)

from utils.test.helpers import ETH, eth_balance


ZERO_HASH = bytes([0] * 32)
ZERO_BYTES32 = HexBytes(ZERO_HASH)
ONE_DAY = 1 * 24 * 60 * 60
SHARE_RATE_PRECISION = 10**27


def prepare_report(
    *,
    refSlot,
    clBalance,
    numValidators,
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
    (_, _, _, _, _, _, _, requestTimestampMargin, _) = contracts.oracle_report_sanity_checker.getOracleReportLimits()
    buffered_ether = contracts.lido.getBufferedEther()
    unfinalized_steth = contracts.withdrawal_queue.unfinalizedStETH()
    reserved_buffer = min(buffered_ether, unfinalized_steth)
    available_eth = withdrawal_vault_balance + el_rewards_vault_balance + reserved_buffer
    max_timestamp = chain.time() - requestTimestampMargin

    batchesState = contracts.withdrawal_queue.calculateFinalizationBatches(
        share_rate, max_timestamp, 10000, (available_eth, False, [0 for _ in range(36)], 0)
    )

    while not batchesState[1]:  # batchesState.finished
        batchesState = contracts.withdrawal_queue.calculateFinalizationBatches(
            share_rate, max_timestamp, 10000, batchesState
        )

    return list(filter(lambda value: value > 0, batchesState[2]))


def reach_consensus(slot, report, version, silent=False):
    (members, *_) = contracts.hash_consensus_for_accounting_oracle.getFastLaneMembers()
    for member in members:
        if not silent:
            print(f"Member ${member} submitting report to hashConsensus")
        contracts.hash_consensus_for_accounting_oracle.submitReport(slot, report, version, {"from": member})
    (_, hash_, _) = contracts.hash_consensus_for_accounting_oracle.getConsensusState()
    assert hash_ == report.hex(), "HashConsensus points to unexpected report"
    return members[0]


def push_oracle_report(
    *,
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
    silent=False,
):
    if not silent:
        print(f"Preparing oracle report for refSlot: {refSlot}")
    consensusVersion = contracts.accounting_oracle.getConsensusVersion()
    oracleVersion = contracts.accounting_oracle.getContractVersion()
    (items, hash) = prepare_report(
        refSlot=refSlot,
        clBalance=clBalance,
        numValidators=numValidators,
        withdrawalVaultBalance=withdrawalVaultBalance,
        elRewardsVaultBalance=elRewardsVaultBalance,
        sharesRequestedToBurn=sharesRequestedToBurn,
        simulatedShareRate=simulatedShareRate,
        stakingModuleIdsWithNewlyExitedValidators=stakingModuleIdsWithNewlyExitedValidators,
        numExitedValidatorsByStakingModule=numExitedValidatorsByStakingModule,
        consensusVersion=consensusVersion,
        withdrawalFinalizationBatches=withdrawalFinalizationBatches,
        isBunkerMode=isBunkerMode,
        extraDataFormat=extraDataFormat,
        extraDataHash=extraDataHash,
        extraDataItemsCount=extraDataItemsCount,
    )
    submitter = reach_consensus(refSlot, hash, consensusVersion, silent)
    # print(contracts.oracle_report_sanity_checker.getOracleReportLimits())
    report_tx = contracts.accounting_oracle.submitReportData(items, oracleVersion, {"from": submitter})
    if not silent:
        print(f"Submitted report data")
    # TODO add support for extra data type 1
    extra_report_tx = contracts.accounting_oracle.submitReportExtraDataEmpty({"from": submitter})
    if not silent:
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


def simulate_report(*, refSlot, beaconValidators, postCLBalance, withdrawalVaultBalance, elRewardsVaultBalance):
    (_, SECONDS_PER_SLOT, GENESIS_TIME) = contracts.hash_consensus_for_accounting_oracle.getChainConfig()
    reportTime = GENESIS_TIME + refSlot * SECONDS_PER_SLOT
    return contracts.lido.handleOracleReport.call(
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


def wait_to_next_available_report_time():
    (SLOTS_PER_EPOCH, SECONDS_PER_SLOT, GENESIS_TIME) = contracts.hash_consensus_for_accounting_oracle.getChainConfig()
    (refSlot, _) = contracts.hash_consensus_for_accounting_oracle.getCurrentFrame()
    time = chain.time()
    (_, EPOCHS_PER_FRAME, _) = contracts.hash_consensus_for_accounting_oracle.getFrameConfig()
    frame_start_with_offset = GENESIS_TIME + (refSlot + SLOTS_PER_EPOCH * EPOCHS_PER_FRAME + 1) * SECONDS_PER_SLOT
    chain.sleep(frame_start_with_offset - time)
    chain.mine(1)
    (nextRefSlot, _) = contracts.hash_consensus_for_accounting_oracle.getCurrentFrame()
    assert nextRefSlot == refSlot + SLOTS_PER_EPOCH * EPOCHS_PER_FRAME, "should be next frame"


# exclude_vaults_balances safely forces LIDO to see vault balances as empty allowing zero/negative rebase
def oracle_report(cl_diff=ETH(10), exclude_vaults_balances=False):
    wait_to_next_available_report_time()

    (refSlot, _) = contracts.hash_consensus_for_accounting_oracle.getCurrentFrame()

    elRewardsVaultBalance = eth_balance(contracts.execution_layer_rewards_vault.address)
    withdrawalVaultBalance = eth_balance(contracts.withdrawal_vault.address)
    if exclude_vaults_balances:
        elRewardsVaultBalance = 0

    (coverShares, nonCoverShares) = contracts.burner.getSharesRequestedToBurn()
    (_, beaconValidators, beaconBalance) = contracts.lido.getBeaconStat()

    postCLBalance = beaconBalance + cl_diff

    (postTotalPooledEther, postTotalShares, withdrawals, elRewards) = simulate_report(
        refSlot=refSlot,
        beaconValidators=beaconValidators,
        postCLBalance=postCLBalance,
        withdrawalVaultBalance=withdrawalVaultBalance,
        elRewardsVaultBalance=elRewardsVaultBalance,
    )
    simulatedShareRate = postTotalPooledEther * SHARE_RATE_PRECISION // postTotalShares
    sharesRequestedToBurn = coverShares + nonCoverShares

    finalization_batches = get_finalization_batches(simulatedShareRate, withdrawals, elRewards)

    # simulate needs proper w-vault balance
    if exclude_vaults_balances:
        withdrawalVaultBalance = 0

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
