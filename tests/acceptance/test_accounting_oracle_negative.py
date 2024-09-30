from typing import Callable
from hexbytes import HexBytes
from web3 import Web3

import pytest
from brownie import ZERO_ADDRESS, Contract, MockHashConsensus, accounts, chain, interface, reverts, chain  # type: ignore
from brownie.network.account import Account
from configs.config_mainnet import MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT

from utils.test.helpers import ETH
from utils.config import contracts, ACCOUNTING_ORACLE
from utils.evm_script import encode_error
from utils.test.extra_data import ExtraDataService, ItemType
from utils.test.oracle_report_helpers import (
    ZERO_HASH,
    AccountingReport,
    oracle_report,
    EXTRA_DATA_FORMAT_EMPTY,
    EXTRA_DATA_FORMAT_LIST,
)

NON_ZERO_HASH = ZERO_HASH[:-1] + b"\x01"
FIELDS_WIDTH = ExtraDataService.Lengths


def test_sender_not_allowed(accounting_oracle: Contract, oracle_version: int, stranger: Account) -> None:
    report = oracle_report(dry_run=True)

    with reverts(encode_error("SenderNotAllowed()")):
        accounting_oracle.submitReportExtraDataEmpty({"from": stranger})

    with reverts(encode_error("SenderNotAllowed()")):
        accounting_oracle.submitReportExtraDataList(b"", {"from": stranger})

    with reverts(encode_error("SenderNotAllowed()")):
        accounting_oracle.submitReportData(report.items, oracle_version, {"from": stranger})

    with reverts(encode_error("SenderIsNotTheConsensusContract()")):
        accounting_oracle.submitConsensusReport(report.hash, report.refSlot, chain.time(), {"from": stranger})

    with reverts(encode_error("SenderIsNotTheConsensusContract()")):
        accounting_oracle.discardConsensusReport(report.refSlot, {"from": stranger})


def test_submitConsensusReport(accounting_oracle: Contract, hash_consensus: Contract) -> None:
    last_processing_ref_slot = accounting_oracle.getLastProcessingRefSlot()

    with reverts(
        encode_error(
            "RefSlotCannotDecrease(uint256,uint256)",
            [last_processing_ref_slot - 1, last_processing_ref_slot],
        )
    ):
        accounting_oracle.submitConsensusReport(
            NON_ZERO_HASH,
            last_processing_ref_slot - 1,
            chain.time(),
            {"from": hash_consensus},
        )

    with reverts(
        encode_error(
            "RefSlotMustBeGreaterThanProcessingOne(uint256,uint256)",
            [last_processing_ref_slot, last_processing_ref_slot],
        )
    ):
        accounting_oracle.submitConsensusReport(
            NON_ZERO_HASH,
            last_processing_ref_slot,
            chain.time(),
            {"from": hash_consensus},
        )

    with reverts(encode_error("ProcessingDeadlineMissed(uint256)", [42])):
        accounting_oracle.submitConsensusReport(
            NON_ZERO_HASH,
            last_processing_ref_slot + 1,
            42,
            {"from": hash_consensus},
        )

    with reverts(encode_error("HashCannotBeZero()")):
        accounting_oracle.submitConsensusReport(
            ZERO_HASH,
            last_processing_ref_slot + 1,
            chain.time() + 12,
            {"from": hash_consensus},
        )


def test_discardConsensusReport(accounting_oracle: Contract, hash_consensus: Contract) -> None:
    last_processing_ref_slot = accounting_oracle.getLastProcessingRefSlot()

    with reverts(
        encode_error(
            "RefSlotCannotDecrease(uint256,uint256)",
            [last_processing_ref_slot - 1, last_processing_ref_slot],
        )
    ):
        accounting_oracle.discardConsensusReport(
            last_processing_ref_slot - 1,
            {"from": hash_consensus},
        )

    with reverts(encode_error("RefSlotAlreadyProcessing()")):
        accounting_oracle.discardConsensusReport(
            last_processing_ref_slot,
            {"from": hash_consensus},
        )


def test_setConsensusVersion(accounting_oracle: Contract, aragon_agent: Account) -> None:
    # There is no role holder after upgrade
    accounting_oracle.grantRole(
        accounting_oracle.MANAGE_CONSENSUS_VERSION_ROLE(),
        aragon_agent,
        {"from": aragon_agent},
    )

    with reverts(encode_error("VersionCannotBeSame()")):
        accounting_oracle.setConsensusVersion(
            accounting_oracle.getContractVersion(),
            {"from": aragon_agent},
        )


def test_setConsensusContract(accounting_oracle: Contract, aragon_agent: Account, deployer: Account) -> None:
    # There is no role holder after upgrade
    accounting_oracle.grantRole(
        accounting_oracle.MANAGE_CONSENSUS_CONTRACT_ROLE(),
        aragon_agent,
        {"from": aragon_agent},
    )

    with reverts(encode_error("AddressCannotBeZero()")):
        accounting_oracle.setConsensusContract(
            ZERO_ADDRESS,
            {"from": aragon_agent},
        )

    with reverts(encode_error("AddressCannotBeSame()")):
        accounting_oracle.setConsensusContract(
            accounting_oracle.getConsensusContract(),
            {"from": aragon_agent},
        )

    hash_consensus = MockHashConsensus.deploy(
        42,  # slots_per_epoch
        17,  # seconds_per_slot
        100500,  # genesis_time
        0,  # initital_ref_slot
        {"from": deployer},
    )
    with reverts(encode_error("UnexpectedChainConfig()")):
        accounting_oracle.setConsensusContract(
            hash_consensus.address,
            {"from": aragon_agent},
        )

    hash_consensus = MockHashConsensus.deploy(
        99,  # slots_per_epoch
        accounting_oracle.SECONDS_PER_SLOT(),
        accounting_oracle.GENESIS_TIME(),
        13,  # initital_ref_slot
        {"from": deployer},
    )
    with reverts(
        encode_error(
            "InitialRefSlotCannotBeLessThanProcessingOne(uint256,uint256)",
            [13, accounting_oracle.getLastProcessingRefSlot()],
        )
    ):
        accounting_oracle.setConsensusContract(
            hash_consensus.address,
            {"from": aragon_agent},
        )


class TestSubmitReportExtraDataList:
    def test_too_short_extra_data_item(self):
        extra_data = b"".join(
            (
                build_extra_data_item(0, ItemType.EXTRA_DATA_TYPE_STUCK_VALIDATORS, 1, [2], [2]),
                build_extra_data_item(1, ItemType.EXTRA_DATA_TYPE_STUCK_VALIDATORS, 2, [2], [2])[:36],
            )
        )

        with reverts(encode_error("InvalidExtraDataItem(uint256)", [1])):
            self.report(extra_data)

        extra_data = b"".join(
            (
                build_extra_data_item(0, ItemType.EXTRA_DATA_TYPE_STUCK_VALIDATORS, 1, [2, 3, 4, 5], [2]),
                build_extra_data_item(1, ItemType.EXTRA_DATA_TYPE_STUCK_VALIDATORS, 2, [2], [2]),
            )
        )

        with reverts(encode_error("InvalidExtraDataItem(uint256)", [0])):
            self.report(extra_data)

    def test_nos_count_zero(self):
        extra_data = b"".join(
            (
                build_extra_data_item(0, ItemType.EXTRA_DATA_TYPE_STUCK_VALIDATORS, 1, [2], [2]),
                build_extra_data_item(1, ItemType.EXTRA_DATA_TYPE_STUCK_VALIDATORS, 2, [], [1]),
            )
        )

        with reverts(encode_error("InvalidExtraDataItem(uint256)", [1])):
            self.report(extra_data)

    def test_module_id_zero(self):
        extra_data = b"".join(
            (
                build_extra_data_item(0, ItemType.EXTRA_DATA_TYPE_STUCK_VALIDATORS, 1, [2], [2]),
                build_extra_data_item(1, ItemType.EXTRA_DATA_TYPE_STUCK_VALIDATORS, 0, [2], [1]),
            )
        )

        with reverts(encode_error("InvalidExtraDataItem(uint256)", [1])):
            self.report(extra_data)

    def test_unexpected_extra_data_index(self):
        extra_data = b"".join(
            (
                build_extra_data_item(1, ItemType.EXTRA_DATA_TYPE_STUCK_VALIDATORS, 1, [2], [1]),
                build_extra_data_item(2, ItemType.EXTRA_DATA_TYPE_STUCK_VALIDATORS, 2, [2], [1]),
            )
        )

        with reverts(encode_error("UnexpectedExtraDataIndex(uint256,uint256)", [0, 1])):
            self.report(extra_data)

        extra_data = b"".join(
            (
                build_extra_data_item(0, ItemType.EXTRA_DATA_TYPE_STUCK_VALIDATORS, 1, [2], [1]),
                build_extra_data_item(3, ItemType.EXTRA_DATA_TYPE_STUCK_VALIDATORS, 1, [2], [1]),
            )
        )

        with reverts(encode_error("UnexpectedExtraDataIndex(uint256,uint256)", [1, 3])):
            self.report(extra_data)

        extra_data = b"".join(
            (
                build_extra_data_item(0, ItemType.EXTRA_DATA_TYPE_STUCK_VALIDATORS, 1, [2], [1]),
                build_extra_data_item(0, ItemType.EXTRA_DATA_TYPE_STUCK_VALIDATORS, 1, [2], [1]),
            )
        )

        with reverts(encode_error("UnexpectedExtraDataIndex(uint256,uint256)", [1, 0])):
            self.report(extra_data)

    def test_unsupported_extra_data_type(self):
        extra_data = build_extra_data_item(0, ItemType.UNSUPPORTED, 1, [1], [1])

        with reverts(
            encode_error(
                "UnsupportedExtraDataType(uint256,uint256)",
                [0, ItemType.UNSUPPORTED.value],
            )
        ):
            self.report(extra_data, items_count=1)

    def test_invalid_extra_data_sort_order(self):
        extra_data = b"".join(
            (
                build_extra_data_item(0, ItemType.EXTRA_DATA_TYPE_STUCK_VALIDATORS, 1, [2], [1]),
                build_extra_data_item(1, ItemType.EXTRA_DATA_TYPE_STUCK_VALIDATORS, 1, [2], [1]),
            )
        )

        with reverts(
            encode_error(
                "InvalidExtraDataSortOrder(uint256)",
                [1],
            )
        ):
            self.report(extra_data)

        extra_data = b"".join(
            (
                build_extra_data_item(0, ItemType.EXTRA_DATA_TYPE_EXITED_VALIDATORS, 1, [33], [250]),
                build_extra_data_item(1, ItemType.EXTRA_DATA_TYPE_EXITED_VALIDATORS, 1, [33], [1]),
            )
        )

        with reverts(
            encode_error(
                "InvalidExtraDataSortOrder(uint256)",
                [1],
            )
        ):
            self.report(extra_data)

    def test_unexpected_extra_data_item(self, extra_data_service: ExtraDataService) -> None:
        extra_data = extra_data_service.collect(
            {(1, 38): 1},
            {(1, 33): 250},
            MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT,
            1,
        )

        with reverts(
            encode_error(
                "UnexpectedExtraDataItemsCount(uint256,uint256)",
                [
                    extra_data.items_count - 1,
                    extra_data.items_count,
                ],
            )
        ):
            self.report(
                extra_data.extra_data,
                items_count=extra_data.items_count - 1,
            )

    def test_already_processed(
        self,
        accounting_oracle: Contract,
        consensus_member: Account,
        extra_data_service: ExtraDataService,
    ):
        extra_data = extra_data_service.collect(
            {(1, 38): 1},
            {(1, 33): 250},
            MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT,
            1,
        )

        self.report(extra_data.extra_data, extra_data.items_count)
        with reverts(encode_error("ExtraDataAlreadyProcessed()")):
            accounting_oracle.submitReportExtraDataList(b"", {"from": consensus_member})

    @pytest.fixture(scope="function")
    def extra_data_service(self):
        return ExtraDataService()

    def report(self, extra_data: bytes, items_count: int = 2):
        oracle_report(
            extraDataHash=Web3.keccak(extra_data),
            extraDataItemsCount=items_count,
            extraDataFormat=EXTRA_DATA_FORMAT_LIST,
            extraDataList=extra_data,
        )


class TestSubmitReportData:
    def test_simple(
        self,
        accounting_oracle: Contract,
        consensus_member: Account,
        hash_consensus: Contract,
    ) -> None:
        report = oracle_report(dry_run=True)
        deadline = chain.time() + 100
        # store the report
        accounting_oracle.submitConsensusReport(
            report.hash,
            report.refSlot,
            deadline,
            {"from": hash_consensus},
        )

        with reverts(
            encode_error(
                "UnexpectedContractVersion(uint256,uint256)",
                [accounting_oracle.getContractVersion(), 42],
            )
        ):
            accounting_oracle.submitReportData(
                report.items,
                42,
                {"from": consensus_member},
            )

        broken_report = report.copy()
        broken_report.refSlot = 42

        with reverts(
            encode_error(
                "UnexpectedRefSlot(uint256,uint256)",
                [
                    report.refSlot,
                    broken_report.refSlot,
                ],
            )
        ):
            accounting_oracle.submitReportData(
                broken_report.items,
                accounting_oracle.getContractVersion(),
                {"from": consensus_member},
            )

        broken_report = report.copy()
        broken_report.consensusVersion = 66

        with reverts(
            encode_error(
                "UnexpectedConsensusVersion(uint256,uint256)",
                [
                    accounting_oracle.getConsensusVersion(),
                    broken_report.consensusVersion,
                ],
            )
        ):
            accounting_oracle.submitReportData(
                broken_report.items,
                accounting_oracle.getContractVersion(),
                {"from": consensus_member},
            )

        broken_report = report.copy()
        broken_report.simulatedShareRate = 0  # just change some field

        with reverts(
            encode_error(
                "UnexpectedDataHash(bytes32,bytes32)",
                [
                    report.hash,
                    broken_report.hash,
                ],
            )
        ):
            accounting_oracle.submitReportData(
                broken_report.items,
                accounting_oracle.getContractVersion(),
                {"from": consensus_member},
            )

        # NOTE: NoConsensusReportToProcess skipped

        with reverts(encode_error("RefSlotAlreadyProcessing()")):
            accounting_oracle.submitReportData(
                report.items,
                accounting_oracle.getContractVersion(),
                {"from": consensus_member},
            )
            accounting_oracle.submitReportData(
                report.items,
                accounting_oracle.getContractVersion(),
                {"from": consensus_member},
            )

        chain.sleep(deadline - chain.time() + 42)
        chain.mine()

        with reverts(
            encode_error(
                "ProcessingDeadlineMissed(uint256)",
                [deadline],
            )
        ):
            accounting_oracle.submitReportData(
                report.items,
                accounting_oracle.getContractVersion(),
                {"from": consensus_member},
            )

    def test_extra_data_broken(
        self,
        accounting_oracle: Contract,
        consensus_member: Account,
        push_report: Callable,
    ):
        report = oracle_report(
            extraDataHash=HexBytes(NON_ZERO_HASH),
            dry_run=True,
        )
        push_report(report)

        with reverts(
            encode_error(
                "UnexpectedExtraDataHash(bytes32,bytes32)",
                [HexBytes(ZERO_HASH), HexBytes(NON_ZERO_HASH)],
            )
        ):
            accounting_oracle.submitReportData(
                report.items,
                accounting_oracle.getContractVersion(),
                {"from": consensus_member},
            )

        report = oracle_report(
            extraDataItemsCount=42,
            dry_run=True,
        )
        push_report(report)

        with reverts(
            encode_error(
                "UnexpectedExtraDataItemsCount(uint256,uint256)",
                [0, 42],
            )
        ):
            accounting_oracle.submitReportData(
                report.items,
                accounting_oracle.getContractVersion(),
                {"from": consensus_member},
            )

        report = oracle_report(
            extraDataFormat=66,
            dry_run=True,
        )
        push_report(report)

        with reverts(
            encode_error(
                "UnsupportedExtraDataFormat(uint256)",
                [66],
            )
        ):
            accounting_oracle.submitReportData(
                report.items,
                accounting_oracle.getContractVersion(),
                {"from": consensus_member},
            )

        report = oracle_report(
            extraDataFormat=EXTRA_DATA_FORMAT_LIST,
            dry_run=True,
        )
        push_report(report)

        with reverts(encode_error("ExtraDataItemsCountCannotBeZeroForNonEmptyData()")):
            accounting_oracle.submitReportData(
                report.items,
                accounting_oracle.getContractVersion(),
                {"from": consensus_member},
            )

        report = oracle_report(
            extraDataFormat=EXTRA_DATA_FORMAT_LIST,
            extraDataHash=HexBytes(ZERO_HASH),
            extraDataItemsCount=42,
            dry_run=True,
        )
        push_report(report)

        with reverts(encode_error("ExtraDataHashCannotBeZeroForNonEmptyData()")):
            accounting_oracle.submitReportData(
                report.items,
                accounting_oracle.getContractVersion(),
                {"from": consensus_member},
            )

    def test_processStakingRouterExitedValidatorsByModule(
        self,
        accounting_oracle: Contract,
        consensus_member: Account,
        push_report: Callable,
    ):
        report = oracle_report(
            stakingModuleIdsWithNewlyExitedValidators=[0, 0],
            numExitedValidatorsByStakingModule=[0],
            dry_run=True,
        )
        push_report(report)

        with reverts(encode_error("InvalidExitedValidatorsData()")):
            accounting_oracle.submitReportData(
                report.items,
                accounting_oracle.getContractVersion(),
                {"from": consensus_member},
            )

        report = oracle_report(
            stakingModuleIdsWithNewlyExitedValidators=[2, 1],
            numExitedValidatorsByStakingModule=[0, 0],
            dry_run=True,
        )
        push_report(report)

        with reverts(encode_error("InvalidExitedValidatorsData()")):
            accounting_oracle.submitReportData(
                report.items,
                accounting_oracle.getContractVersion(),
                {"from": consensus_member},
            )

        report = oracle_report(
            stakingModuleIdsWithNewlyExitedValidators=[1, 2],
            numExitedValidatorsByStakingModule=[1, 0],
            dry_run=True,
        )
        push_report(report)

        with reverts(encode_error("InvalidExitedValidatorsData()")):
            accounting_oracle.submitReportData(
                report.items,
                accounting_oracle.getContractVersion(),
                {"from": consensus_member},
            )


# === Fixtures ===
@pytest.fixture(scope="module")
def accounting_oracle() -> interface.AccountingOracle:
    return interface.AccountingOracle(ACCOUNTING_ORACLE)


@pytest.fixture(scope="module")
def oracle_version(accounting_oracle: Contract) -> int:
    return accounting_oracle.getContractVersion()


@pytest.fixture(scope="module")
def aragon_agent() -> Account:
    return contracts.agent


@pytest.fixture(scope="function")
def consensus_member():
    return accounts.at(
        contracts.hash_consensus_for_accounting_oracle.getFastLaneMembers()[0][0],
        force=True,
    )


@pytest.fixture(scope="module")
def hash_consensus() -> Contract:
    return contracts.hash_consensus_for_accounting_oracle


@pytest.fixture(scope="module")
def push_report(accounting_oracle: Contract, hash_consensus: Contract) -> Callable[[AccountingReport], int]:
    def wrapped(report: AccountingReport) -> int:
        deadline = chain.time() + 100
        accounting_oracle.submitConsensusReport(
            report.hash,
            report.refSlot,
            deadline,
            {"from": hash_consensus},
        )
        return deadline

    return wrapped


@pytest.fixture(scope="module")
def submit_main_data(accounting_oracle: Contract, consensus_member: Account) -> Callable[[AccountingReport], None]:
    def wrapped(report: AccountingReport) -> None:
        accounting_oracle.submitReportData(
            report.items,
            accounting_oracle.getContractVersion(),
            {"from": consensus_member},
        )

    return wrapped


# === Helpers ===


def build_extra_data_item(
    index: int,
    type_: ItemType,
    module_id: int,
    nos_ids: list[int],
    vals_count: list[int],
) -> bytes:
    """Build bytes representation of extra data item"""

    opts = {"byteorder": "big"}  # required arg until py3.11
    return b"".join(
        (
            index.to_bytes(FIELDS_WIDTH.ITEM_INDEX, **opts),
            type_.value.to_bytes(FIELDS_WIDTH.ITEM_TYPE, **opts),
            module_id.to_bytes(FIELDS_WIDTH.MODULE_ID, **opts),
            len(nos_ids).to_bytes(FIELDS_WIDTH.NODE_OPS_COUNT, **opts),
            b"".join(i.to_bytes(FIELDS_WIDTH.NODE_OPERATOR_IDS, **opts) for i in nos_ids),
            b"".join(i.to_bytes(FIELDS_WIDTH.STUCK_OR_EXITED_VALS_COUNT, **opts) for i in vals_count),
        )
    )
