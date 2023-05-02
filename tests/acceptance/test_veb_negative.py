import pytest
from hexbytes import HexBytes

from brownie import interface, reverts, accounts, web3  # type: ignore

from utils.test.exit_bus_data import LidoValidator
from utils.config import (
    contracts,
    lido_dao_validators_exit_bus_oracle,
)
from utils.test.exit_bus_data import encode_data
from utils.evm_script import encode_error
from utils.test.oracle_report_helpers import (
    encode_data_from_abi,
    reach_consensus,
    prepare_exit_bus_report,
    wait_to_next_available_report_time,
)


@pytest.fixture(scope="module")
def contract() -> interface.ValidatorsExitBusOracle:
    return interface.ValidatorsExitBusOracle(lido_dao_validators_exit_bus_oracle)


@pytest.fixture(scope="function")
def ref_slot():
    wait_to_next_available_report_time(contracts.hash_consensus_for_validators_exit_bus_oracle)
    ref_slot, _ = contracts.hash_consensus_for_validators_exit_bus_oracle.getCurrentFrame()
    return ref_slot


def test_get_last_requested_validator_indices(contract):
    with reverts():  # ArgumentOutOfBounds()
        contract.getLastRequestedValidatorIndices(2**24 + 1, [])

    with reverts():  # ArgumentOutOfBounds()
        contract.getLastRequestedValidatorIndices(1, [2**40 + 1])


def test_submit_report_data_checks(contract, ref_slot):
    stranger = accounts[0]

    contract_version = contract.getContractVersion()
    consensus_version = contract.getConsensusVersion()

    report, report_hash = prepare_exit_bus_report([], ref_slot)

    submitter = reach_consensus(
        ref_slot,
        report_hash,
        consensus_version,
        contracts.hash_consensus_for_validators_exit_bus_oracle,
    )

    with reverts(encode_error("SenderNotAllowed()")):
        contract.submitReportData(report, contract_version, {"from": stranger})

    with reverts(
        encode_error(
            "UnexpectedContractVersion(uint256,uint256)", (contract_version, contract_version + 1)
        )
    ):
        contract.submitReportData(report, contract_version + 1, {"from": submitter})

    with reverts(encode_error("UnexpectedRefSlot(uint256,uint256)", (ref_slot, ref_slot - 1))):
        wrong_report = (report[0], ref_slot - 1, report[2], report[3], report[4])
        contract.submitReportData(wrong_report, contract_version, {"from": submitter})

    with reverts(
        encode_error(
            "UnexpectedConsensusVersion(uint256,uint256)",
            (consensus_version, consensus_version + 1),
        )
    ):
        wrong_report = (consensus_version + 1, report[1], report[2], report[3], report[4])
        contract.submitReportData(wrong_report, contract_version, {"from": submitter})

    with reverts():  # encode_error("UnexpectedDataHash(bytes32,bytes32)",(report_hash, report_hash))
        wrong_report = (
            report[0],
            report[1],
            report[2],
            report[3],
            HexBytes(42).hex(),
        )
        contract.submitReportData(wrong_report, contract_version, {"from": submitter})


def test_submit_report_data_processing(contract, ref_slot):
    contract_version = contract.getContractVersion()
    consensus_version = contract.getConsensusVersion()

    report, report_hash = prepare_exit_bus_report([], ref_slot)

    submitter = reach_consensus(
        ref_slot,
        report_hash,
        consensus_version,
        contracts.hash_consensus_for_validators_exit_bus_oracle,
    )

    contract.submitReportData(report, contract_version, {"from": submitter})

    with reverts(encode_error("RefSlotAlreadyProcessing()")):
        contract.submitReportData(report, contract_version, {"from": submitter})


def test_handle_consensus_report_data_wrong_format(contract, ref_slot):
    no_global_index = (_, no_id) = (1, 1)
    validator_id = 1
    validator_key = contracts.node_operators_registry.getSigningKey(no_id, validator_id)[0]
    validator = LidoValidator(validator_id, validator_key)

    contract_version = contract.getContractVersion()
    consensus_version = contract.getConsensusVersion()

    data, data_format = encode_data([(no_global_index, validator)])
    report = (
        consensus_version,
        ref_slot,
        len([(no_global_index, validator)]),
        data_format + 1,
        data,
    )
    report_data = encode_data_from_abi(
        report, contracts.validators_exit_bus_oracle.abi, "submitReportData"
    )
    report_hash = web3.keccak(report_data)
    submitter = reach_consensus(
        ref_slot,
        report_hash,
        consensus_version,
        contracts.hash_consensus_for_validators_exit_bus_oracle,
    )

    with reverts(encode_error("UnsupportedRequestsDataFormat(uint256)", [data_format + 1])):
        contract.submitReportData(report, contract_version, {"from": submitter})


def test_handle_consensus_report_data_wrong_data_length(contract, ref_slot):
    no_global_index = (_, no_id) = (1, 1)
    validator_id = 1
    validator_key = contracts.node_operators_registry.getSigningKey(no_id, validator_id)[0]
    validator = LidoValidator(validator_id, validator_key)

    contract_version = contract.getContractVersion()
    consensus_version = contract.getConsensusVersion()

    data, data_format = encode_data([(no_global_index, validator)])
    report = (
        consensus_version,
        ref_slot,
        len([(no_global_index, validator)]),
        data_format,
        data[:30],
    )
    report_data = encode_data_from_abi(
        report, contracts.validators_exit_bus_oracle.abi, "submitReportData"
    )
    report_hash = web3.keccak(report_data)
    submitter = reach_consensus(
        ref_slot,
        report_hash,
        consensus_version,
        contracts.hash_consensus_for_validators_exit_bus_oracle,
    )

    with reverts(encode_error("InvalidRequestsDataLength()")):
        contract.submitReportData(report, contract_version, {"from": submitter})


def test_handle_consensus_report_data_wrong_request_length(contract, ref_slot):
    no_global_index = (_, no_id) = (1, 1)
    validator_id = 1
    validator_key = contracts.node_operators_registry.getSigningKey(no_id, validator_id)[0]
    validator = LidoValidator(validator_id, validator_key)

    contract_version = contract.getContractVersion()
    consensus_version = contract.getConsensusVersion()

    data, data_format = encode_data([(no_global_index, validator)])
    report = (
        consensus_version,
        ref_slot,
        0,
        data_format,
        data,
    )
    report_data = encode_data_from_abi(
        report, contracts.validators_exit_bus_oracle.abi, "submitReportData"
    )
    report_hash = web3.keccak(report_data)
    submitter = reach_consensus(
        ref_slot,
        report_hash,
        consensus_version,
        contracts.hash_consensus_for_validators_exit_bus_oracle,
    )

    with reverts(encode_error("UnexpectedRequestsDataLength()")):
        contract.submitReportData(report, contract_version, {"from": submitter})


def test_handle_consensus_report_data_wrong_module_id(contract, ref_slot):
    no_global_index = (_, no_id) = (0, 1)
    validator_id = 1
    validator_key = contracts.node_operators_registry.getSigningKey(no_id, validator_id)[0]
    validator = LidoValidator(validator_id, validator_key)

    contract_version = contract.getContractVersion()
    consensus_version = contract.getConsensusVersion()

    data, data_format = encode_data([(no_global_index, validator)])
    report = (
        consensus_version,
        ref_slot,
        len([(no_global_index, validator)]),
        data_format,
        data,
    )
    report_data = encode_data_from_abi(
        report, contracts.validators_exit_bus_oracle.abi, "submitReportData"
    )
    report_hash = web3.keccak(report_data)
    submitter = reach_consensus(
        ref_slot,
        report_hash,
        consensus_version,
        contracts.hash_consensus_for_validators_exit_bus_oracle,
    )

    with reverts(encode_error("InvalidRequestsData()")):
        contract.submitReportData(report, contract_version, {"from": submitter})


def test_handle_consensus_report_data_second_exit(contract, ref_slot):
    no_global_index = (module_id, no_id) = (1, 1)
    validator_id = 1
    validator_key = contracts.node_operators_registry.getSigningKey(no_id, validator_id)[0]
    validator = LidoValidator(validator_id, validator_key)

    contract_version = contract.getContractVersion()
    consensus_version = contract.getConsensusVersion()

    data, data_format = encode_data([(no_global_index, validator)])
    report = (
        consensus_version,
        ref_slot,
        len([(no_global_index, validator)]),
        data_format,
        data,
    )
    report_data = encode_data_from_abi(
        report, contracts.validators_exit_bus_oracle.abi, "submitReportData"
    )
    report_hash = web3.keccak(report_data)
    submitter = reach_consensus(
        ref_slot,
        report_hash,
        consensus_version,
        contracts.hash_consensus_for_validators_exit_bus_oracle,
    )

    contract.submitReportData(report, contract_version, {"from": submitter})

    last_requested_validator_index_before = (
        contracts.validators_exit_bus_oracle.getLastRequestedValidatorIndices(module_id, [no_id])
    )

    wait_to_next_available_report_time(contracts.hash_consensus_for_validators_exit_bus_oracle)
    ref_slot, _ = contracts.hash_consensus_for_validators_exit_bus_oracle.getCurrentFrame()

    data, data_format = encode_data([(no_global_index, validator)])
    report = (
        consensus_version,
        ref_slot,
        len([(no_global_index, validator)]),
        data_format,
        data,
    )
    report_data = encode_data_from_abi(
        report, contracts.validators_exit_bus_oracle.abi, "submitReportData"
    )
    report_hash = web3.keccak(report_data)
    submitter = reach_consensus(
        ref_slot,
        report_hash,
        consensus_version,
        contracts.hash_consensus_for_validators_exit_bus_oracle,
    )

    with reverts(
        encode_error(
            "NodeOpValidatorIndexMustIncrease(uint256,uint256,uint256,uint256)",
            (
                module_id,
                no_id,
                last_requested_validator_index_before[0],
                last_requested_validator_index_before[0],
            ),
        )
    ):
        contract.submitReportData(report, contract_version, {"from": submitter})


def test_handle_consensus_report_data_invalid_request_order(contract, ref_slot):
    no_global_index = (_, no_id) = (1, 1)
    validator_id = 1
    validator_key = contracts.node_operators_registry.getSigningKey(no_id, validator_id)[0]
    validator = LidoValidator(validator_id, validator_key)
    validator_2 = LidoValidator(
        2, contracts.node_operators_registry.getSigningKey(no_id, validator_id + 1)[0]
    )

    contract_version = contract.getContractVersion()
    consensus_version = contract.getConsensusVersion()

    data, data_format = encode_data(
        [(no_global_index, validator_2), ((no_global_index), validator)], sort=False
    )
    report = (
        consensus_version,
        ref_slot,
        2,
        data_format,
        data,
    )
    report_data = encode_data_from_abi(
        report, contracts.validators_exit_bus_oracle.abi, "submitReportData"
    )
    report_hash = web3.keccak(report_data)
    submitter = reach_consensus(
        ref_slot,
        report_hash,
        consensus_version,
        contracts.hash_consensus_for_validators_exit_bus_oracle,
    )

    with reverts(encode_error("InvalidRequestsDataSortOrder()")):
        contract.submitReportData(report, contract_version, {"from": submitter})
