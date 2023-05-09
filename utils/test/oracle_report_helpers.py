import warnings
from brownie import chain, web3  # type: ignore
from brownie.exceptions import VirtualMachineError  # type: ignore
from eth_abi import encode
from hexbytes import HexBytes

from utils.config import contracts
from utils.test.exit_bus_data import encode_data
from utils.test.helpers import ETH, eth_balance, GWEI

ZERO_HASH = bytes([0] * 32)
ZERO_BYTES32 = HexBytes(ZERO_HASH)
ONE_DAY = 1 * 24 * 60 * 60
SHARE_RATE_PRECISION = 10**27


def prepare_accounting_report(
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
        int(clBalance // GWEI),
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

    data = encode_data_from_abi(items, contracts.accounting_oracle.abi, "submitReportData")

    hash = web3.keccak(data)
    return (items, hash)


def prepare_exit_bus_report(validators_to_exit, ref_slot):
    consensus_version = contracts.validators_exit_bus_oracle.getConsensusVersion()
    data, data_format = encode_data(validators_to_exit)
    report = (consensus_version, ref_slot, len(validators_to_exit), data_format, data)
    report_data = encode_data_from_abi(report, contracts.validators_exit_bus_oracle.abi, "submitReportData")
    if not validators_to_exit:
        report_data = report_data[:-32]
        assert len(report_data) == 224, (
            "We cut off the last 32 bytes because there is a problem with the encoding of empty bytes array in the eth_abi package. "
            "Remove this condition when eth_abi is bumped to the latest version."
        )
    report_hash = web3.keccak(report_data)
    return report, report_hash


def encode_data_from_abi(data, abi, func_name):
    report_function_abi = next(x for x in abi if x.get("name") == func_name)
    report_data_abi = report_function_abi["inputs"][0]["components"]  # type: ignore
    report_str_abi = ",".join(map(lambda x: x["type"], report_data_abi))  # type: ignore
    return encode([f"({report_str_abi})"], [data])


def get_finalization_batches(
    share_rate: int, limited_withdrawal_vault_balance, limited_el_rewards_vault_balance
) -> list[int]:
    (_, _, _, _, _, _, _, requestTimestampMargin, _) = contracts.oracle_report_sanity_checker.getOracleReportLimits()
    buffered_ether = contracts.lido.getBufferedEther()
    unfinalized_steth = contracts.withdrawal_queue.unfinalizedStETH()
    reserved_buffer = min(buffered_ether, unfinalized_steth)
    available_eth = limited_withdrawal_vault_balance + limited_el_rewards_vault_balance + reserved_buffer
    max_timestamp = chain.time() - requestTimestampMargin
    MAX_REQUESTS_PER_CALL = 1000

    if not available_eth:
        return []

    batchesState = contracts.withdrawal_queue.calculateFinalizationBatches(
        share_rate, max_timestamp, MAX_REQUESTS_PER_CALL, (available_eth, False, [0 for _ in range(36)], 0)
    )

    while not batchesState[1]:  # batchesState.finished
        batchesState = contracts.withdrawal_queue.calculateFinalizationBatches(
            share_rate, max_timestamp, MAX_REQUESTS_PER_CALL, batchesState
        )

    return list(filter(lambda value: value > 0, batchesState[2]))


def reach_consensus(slot, report, version, oracle_contract, silent=False):
    (members, *_) = oracle_contract.getFastLaneMembers()
    for member in members:
        if not silent:
            print(f"Member ${member} submitting report to hashConsensus")
        oracle_contract.submitReport(slot, report, version, {"from": member})
    (_, hash_, _) = oracle_contract.getConsensusState()
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
    extraDataList="",
):
    if not silent:
        print(f"Preparing oracle report for refSlot: {refSlot}")
    consensusVersion = contracts.accounting_oracle.getConsensusVersion()
    oracleVersion = contracts.accounting_oracle.getContractVersion()
    (items, hash) = prepare_accounting_report(
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
    submitter = reach_consensus(refSlot, hash, consensusVersion, contracts.hash_consensus_for_accounting_oracle, silent)
    # print(contracts.oracle_report_sanity_checker.getOracleReportLimits())
    report_tx = contracts.accounting_oracle.submitReportData(items, oracleVersion, {"from": submitter})
    if not silent:
        print(f"Submitted report data")
        print(f"extraDataList {extraDataList}")
    if extraDataFormat == 0:
        extra_report_tx = contracts.accounting_oracle.submitReportExtraDataEmpty({"from": submitter})
        if not silent:
            print(f"Submitted empty extra data report")
    else:
        extra_report_tx = contracts.accounting_oracle.submitReportExtraDataList(extraDataList, {"from": submitter})
        if not silent:
            print(f"Submitted NOT empty extra data report")

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


def simulate_report(
    *, refSlot, beaconValidators, postCLBalance, withdrawalVaultBalance, elRewardsVaultBalance, block_identifier=None
):
    (_, SECONDS_PER_SLOT, GENESIS_TIME) = contracts.hash_consensus_for_accounting_oracle.getChainConfig()
    reportTime = GENESIS_TIME + refSlot * SECONDS_PER_SLOT
    try:
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
            block_identifier=block_identifier,
        )
    except VirtualMachineError:
        # workaround for empty revert message from ganache on eth_call
        contracts.lido.handleOracleReport(
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
        raise  # unreachable, for static analysis only


def wait_to_next_available_report_time(consensus_contract):
    (SLOTS_PER_EPOCH, SECONDS_PER_SLOT, GENESIS_TIME) = consensus_contract.getChainConfig()
    (refSlot, _) = consensus_contract.getCurrentFrame()
    time = chain.time()
    (_, EPOCHS_PER_FRAME, _) = consensus_contract.getFrameConfig()
    frame_start_with_offset = GENESIS_TIME + (refSlot + SLOTS_PER_EPOCH * EPOCHS_PER_FRAME + 1) * SECONDS_PER_SLOT
    chain.sleep(frame_start_with_offset - time)
    chain.mine(1)
    (nextRefSlot, _) = consensus_contract.getCurrentFrame()
    assert nextRefSlot == refSlot + SLOTS_PER_EPOCH * EPOCHS_PER_FRAME, "should be next frame"


def oracle_report(
    *,
    cl_diff=ETH(10),
    cl_appeared_validators=0,
    exclude_vaults_balances=False,
    report_el_vault=True,
    elRewardsVaultBalance=None,
    report_withdrawals_vault=True,
    withdrawalVaultBalance=None,
    simulation_block_identifier=None,
    skip_withdrawals=False,
    wait_to_next_report_time=True,
    extraDataFormat=0,
    extraDataHash=ZERO_BYTES32,
    extraDataItemsCount=0,
    extraDataList="",
    stakingModuleIdsWithNewlyExitedValidators=[],
    numExitedValidatorsByStakingModule=[],
    silent=False,
    sharesRequestedToBurn=None,
    withdrawalFinalizationBatches=[],
    simulatedShareRate=None,
    refSlot=None,
):
    if wait_to_next_report_time:
        """fast forwards time to next report, compiles report, pushes through consensus and to AccountingOracle"""
        wait_to_next_available_report_time(contracts.hash_consensus_for_accounting_oracle)
    if refSlot is None:
        (refSlot, _) = contracts.hash_consensus_for_accounting_oracle.getCurrentFrame()

    (_, beaconValidators, beaconBalance) = contracts.lido.getBeaconStat()

    postCLBalance = beaconBalance + cl_diff
    postBeaconValidators = beaconValidators + cl_appeared_validators

    elRewardsVaultBalance = (
        eth_balance(contracts.execution_layer_rewards_vault.address)
        if elRewardsVaultBalance is None
        else elRewardsVaultBalance
    )
    withdrawalVaultBalance = (
        eth_balance(contracts.withdrawal_vault.address) if withdrawalVaultBalance is None else withdrawalVaultBalance
    )

    # exclude_vaults_balances safely forces LIDO to see vault balances as empty allowing zero/negative rebase
    # simulate_reports needs proper withdrawal and elRewards vaults balances
    if exclude_vaults_balances:
        if not report_withdrawals_vault or not report_el_vault:
            warnings.warn("exclude_vaults_balances overrides report_withdrawals_vault and report_el_vault")

        report_withdrawals_vault = False
        report_el_vault = False

    if not report_withdrawals_vault:
        withdrawalVaultBalance = 0
    if not report_el_vault:
        elRewardsVaultBalance = 0

    if sharesRequestedToBurn is None:
        (coverShares, nonCoverShares) = contracts.burner.getSharesRequestedToBurn()
        sharesRequestedToBurn = coverShares + nonCoverShares

    is_bunker = False

    if not skip_withdrawals:
        (postTotalPooledEther, postTotalShares, withdrawals, elRewards) = simulate_report(
            refSlot=refSlot,
            beaconValidators=postBeaconValidators,
            postCLBalance=postCLBalance,
            withdrawalVaultBalance=withdrawalVaultBalance,
            elRewardsVaultBalance=elRewardsVaultBalance,
            block_identifier=simulation_block_identifier,
        )
        if simulatedShareRate is None:
            simulatedShareRate = postTotalPooledEther * SHARE_RATE_PRECISION // postTotalShares

        withdrawalFinalizationBatches = (
            get_finalization_batches(simulatedShareRate, withdrawals, elRewards)
            if withdrawalFinalizationBatches == []
            else withdrawalFinalizationBatches
        )

        preTotalPooledEther = contracts.lido.getTotalPooledEther()
        is_bunker = preTotalPooledEther > postTotalPooledEther
    elif simulatedShareRate is None:
        simulatedShareRate = 0

    return push_oracle_report(
        refSlot=refSlot,
        clBalance=postCLBalance,
        numValidators=postBeaconValidators,
        withdrawalVaultBalance=withdrawalVaultBalance,
        sharesRequestedToBurn=sharesRequestedToBurn,
        withdrawalFinalizationBatches=withdrawalFinalizationBatches,
        elRewardsVaultBalance=elRewardsVaultBalance,
        simulatedShareRate=simulatedShareRate,
        extraDataFormat=extraDataFormat,
        extraDataHash=extraDataHash,
        extraDataItemsCount=extraDataItemsCount,
        extraDataList=extraDataList,
        stakingModuleIdsWithNewlyExitedValidators=stakingModuleIdsWithNewlyExitedValidators,
        numExitedValidatorsByStakingModule=numExitedValidatorsByStakingModule,
        silent=silent,
        isBunkerMode=is_bunker,
    )
