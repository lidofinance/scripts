import warnings
from dataclasses import astuple, dataclass
from typing import List, Literal, overload

from brownie import chain, web3, accounts  # type: ignore
from brownie.exceptions import VirtualMachineError
from brownie.typing import TransactionReceipt  # type: ignore
from eth_abi.abi import encode
from hexbytes import HexBytes

from utils.config import contracts, AO_CONSENSUS_VERSION
from utils.test.exit_bus_data import encode_data
from utils.test.helpers import ETH, GWEI, eth_balance
from utils.test.merkle_tree import Tree

ZERO_HASH = bytes([0] * 32)
ZERO_BYTES32 = HexBytes(ZERO_HASH)
ONE_DAY = 1 * 24 * 60 * 60
SHARE_RATE_PRECISION = 10 ** 27
EXTRA_DATA_FORMAT_EMPTY = 0
EXTRA_DATA_FORMAT_LIST = 1


@dataclass
class AccountingReport:
    """Accounting oracle ReportData struct"""

    consensusVersion: int
    refSlot: int
    numValidators: int
    clBalanceGwei: int
    stakingModuleIdsWithNewlyExitedValidators: list[int]
    numExitedValidatorsByStakingModule: list[int]
    withdrawalVaultBalance: int
    elRewardsVaultBalance: int
    sharesRequestedToBurn: int
    withdrawalFinalizationBatches: list[int]
    simulatedShareRate: int
    isBunkerMode: bool
    extraDataFormat: int
    extraDataHash: HexBytes
    extraDataItemsCount: int

    @property
    def items(self) -> tuple:
        return astuple(self)

    @property
    def hash(self) -> HexBytes:
        data = encode_data_from_abi(
            astuple(self),
            contracts.accounting_oracle.abi,
            "submitReportData",
        )

        return web3.keccak(data)

    def copy(self) -> "AccountingReport":
        return AccountingReport(*self.items)


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
    consensusVersion=AO_CONSENSUS_VERSION,
    withdrawalFinalizationBatches=[],
    isBunkerMode=False,
    extraDataFormat=EXTRA_DATA_FORMAT_EMPTY,
    extraDataHashList=[ZERO_BYTES32],
    extraDataItemsCount=0,
):
    report = AccountingReport(
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
        extraDataHashList[0],
        int(extraDataItemsCount),
    )

    return (report.items, report.hash)


def prepare_exit_bus_report(validators_to_exit, ref_slot):
    consensus_version = contracts.validators_exit_bus_oracle.getConsensusVersion()
    data, data_format = encode_data(validators_to_exit)
    report = (consensus_version, ref_slot, len(validators_to_exit), data_format, data)
    report_data = encode_data_from_abi(report, contracts.validators_exit_bus_oracle.abi, "submitReportData")

    report_hash = web3.keccak(report_data)
    return report, report_hash


def prepare_csm_report(node_operators_rewards: dict, ref_slot):
    consensus_version = contracts.cs_fee_oracle.getConsensusVersion()
    shares = node_operators_rewards.copy()
    if len(shares) < 2:
        # put a stone
        shares[2 ** 64 - 1] = 0

    tree = Tree.new(tuple((no_id, amount) for (no_id, amount) in shares.items()))
    # semi-random values
    log_cid = web3.keccak(tree.root)
    tree_cid = web3.keccak(log_cid)

    report = (
        consensus_version,
        ref_slot,
        tree.root,
        str(tree_cid),
        str(log_cid),
        sum(shares.values()),
        0,  # rebate
        HexBytes(ZERO_HASH),  # strikesTreeRoot
        "",  # strikesTreeCid
    )
    report_data = encode_data_from_abi(report, contracts.cs_fee_oracle.abi, "submitReportData")
    report_hash = web3.keccak(report_data)
    return report, report_hash, tree


def encode_data_from_abi(data, abi, func_name):
    report_function_abi = next(x for x in abi if x.get("name") == func_name)
    report_data_abi = report_function_abi["inputs"][0]["components"]  # type: ignore
    report_str_abi = ",".join(map(lambda x: x["type"], report_data_abi))  # type: ignore
    return encode([f"({report_str_abi})"], [data])


def get_finalization_batches(
    share_rate: int, limited_withdrawal_vault_balance, limited_el_rewards_vault_balance
) -> list[int]:
    (
        _,
        _,
        _,
        _,
        _,
        _,
        _,
        requestTimestampMargin,
        _,
        _,
        _,
        _,
    ) = contracts.oracle_report_sanity_checker.getOracleReportLimits()
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
    extraDataHashList=[ZERO_BYTES32],
    extraDataItemsCount=0,
    silent=False,
    extraDataList: List[bytes] = [],
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
        extraDataHashList=extraDataHashList,
        extraDataItemsCount=extraDataItemsCount,
    )
    submitter = reach_consensus(refSlot, hash, consensusVersion, contracts.hash_consensus_for_accounting_oracle, silent)
    accounts[0].transfer(submitter, 10 ** 19)
    # print(contracts.oracle_report_sanity_checker.getOracleReportLimits())
    report_tx = contracts.accounting_oracle.submitReportData(items, oracleVersion, {"from": submitter})
    if not silent:
        print("Submitted report data")
        print(f"extraDataList {extraDataList}")
    if extraDataFormat == 0:
        extra_report_tx_list = [contracts.accounting_oracle.submitReportExtraDataEmpty({"from": submitter})]
        if not silent:
            print("Submitted empty extra data report")
    else:
        extra_report_tx_list = [
            contracts.accounting_oracle.submitReportExtraDataList(data, {"from": submitter}) for data in extraDataList
        ]
        if not silent:
            print("Submitted NOT empty extra data report")

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
    assert state_extraDataHash == extraDataHashList[-1].hex()
    assert state_extraDataFormat == extraDataFormat
    assert extraDataSubmitted
    assert state_extraDataItemsCount == extraDataItemsCount
    assert extraDataItemsSubmitted == extraDataItemsCount
    return (report_tx, extra_report_tx_list)


def simulate_report(
    *, refSlot, beaconValidators, postCLBalance, withdrawalVaultBalance, elRewardsVaultBalance, block_identifier=None
):
    (_, SECONDS_PER_SLOT, GENESIS_TIME) = contracts.hash_consensus_for_accounting_oracle.getChainConfig()
    reportTime = GENESIS_TIME + refSlot * SECONDS_PER_SLOT

    override_slot = web3.keccak(text="lido.BaseOracle.lastProcessingRefSlot").hex()
    state_override = {
        contracts.accounting_oracle.address: {
            # Fix: Sanity checker uses `lastProcessingRefSlot` from AccountingOracle to
            # properly process negative rebase sanity checks. Since current simulation skips call to AO,
            # setting up `lastProcessingRefSlot` directly.
            #
            # The code is taken from the current production `lido-oracle` implementation
            # source: https://github.com/lidofinance/lido-oracle/blob/da393bf06250344a4d06dce6d1ac6a3ddcb9c7a3/src/providers/execution/contracts/lido.py#L93-L95
            "stateDiff": {
                override_slot: '0x' + refSlot.to_bytes(32, "big").hex(),
            },
        },
    }

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
            override=state_override,
        )
    except VirtualMachineError:
        # workaround for empty revert message from ganache on eth_call

        # override storage value of the processing reference slot to make the simulation sound
        # Since it's not possible to pass an override as a part of the state-changing transaction
        web3.provider.make_request(
            # can assume ganache only here
            "evm_setAccountStorageAt",
            [contracts.accounting_oracle.address, override_slot, refSlot],
        )

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
    try:
        (refSlot, _) = consensus_contract.getCurrentFrame()
    except VirtualMachineError as e:
        if "InitialEpochIsYetToArrive" in str(e):
            frame_config = consensus_contract.getFrameConfig()
            chain.sleep(
                GENESIS_TIME + 1 + (frame_config["initialEpoch"] * SLOTS_PER_EPOCH * SECONDS_PER_SLOT) - chain.time()
            )
            chain.mine(1)
            (refSlot, _) = consensus_contract.getCurrentFrame()
        else:
            raise
    time = web3.eth.get_block("latest").timestamp
    (_, EPOCHS_PER_FRAME, _) = consensus_contract.getFrameConfig()
    frame_start_with_offset = GENESIS_TIME + (refSlot + SLOTS_PER_EPOCH * EPOCHS_PER_FRAME + 1) * SECONDS_PER_SLOT
    chain.sleep(frame_start_with_offset - time)
    chain.mine(1)
    (nextRefSlot, _) = consensus_contract.getCurrentFrame()
    assert nextRefSlot == refSlot + SLOTS_PER_EPOCH * EPOCHS_PER_FRAME, "should be next frame"


@overload
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
    extraDataHashList=[ZERO_BYTES32],
    extraDataItemsCount=0,
    extraDataList: List[bytes] = [],
    stakingModuleIdsWithNewlyExitedValidators=[],
    numExitedValidatorsByStakingModule=[],
    silent=False,
    sharesRequestedToBurn=None,
    withdrawalFinalizationBatches=[],
    simulatedShareRate=None,
    dry_run: Literal[False] = False,
) -> tuple[TransactionReceipt, TransactionReceipt]:
    ...


@overload
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
    extraDataHashList=[ZERO_BYTES32],
    extraDataItemsCount=0,
    extraDataList: List[bytes] = [],
    stakingModuleIdsWithNewlyExitedValidators=[],
    numExitedValidatorsByStakingModule=[],
    silent=False,
    sharesRequestedToBurn=None,
    withdrawalFinalizationBatches=[],
    simulatedShareRate=None,
    refSlot=None,
    dry_run: Literal[True],
) -> AccountingReport:
    ...


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
    extraDataHashList=[ZERO_BYTES32],
    extraDataItemsCount=0,
    extraDataList: List[bytes] = [],
    stakingModuleIdsWithNewlyExitedValidators=[],
    numExitedValidatorsByStakingModule=[],
    silent=False,
    sharesRequestedToBurn=None,
    withdrawalFinalizationBatches=[],
    simulatedShareRate=None,
    refSlot=None,
    dry_run=False,
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

    if dry_run:
        return AccountingReport(
            consensusVersion=contracts.accounting_oracle.getConsensusVersion(),
            refSlot=refSlot,
            numValidators=postBeaconValidators,
            clBalanceGwei=postCLBalance // GWEI,
            stakingModuleIdsWithNewlyExitedValidators=stakingModuleIdsWithNewlyExitedValidators,
            numExitedValidatorsByStakingModule=numExitedValidatorsByStakingModule,
            withdrawalVaultBalance=withdrawalVaultBalance,
            elRewardsVaultBalance=elRewardsVaultBalance,
            sharesRequestedToBurn=sharesRequestedToBurn,
            withdrawalFinalizationBatches=withdrawalFinalizationBatches,
            simulatedShareRate=simulatedShareRate,
            isBunkerMode=is_bunker,
            extraDataFormat=extraDataFormat,
            extraDataHash=extraDataHashList[0],
            extraDataItemsCount=extraDataItemsCount,
        )

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
        extraDataHashList=extraDataHashList,
        extraDataItemsCount=extraDataItemsCount,
        extraDataList=extraDataList,
        stakingModuleIdsWithNewlyExitedValidators=stakingModuleIdsWithNewlyExitedValidators,
        numExitedValidatorsByStakingModule=numExitedValidatorsByStakingModule,
        silent=silent,
        isBunkerMode=is_bunker,
    )
