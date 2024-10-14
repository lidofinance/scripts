import dataclasses

from brownie.convert.datatypes import HexString

from utils.config import contracts
from utils.test.exit_bus_data import LidoValidator
from utils.test.oracle_report_helpers import (
    wait_to_next_available_report_time,
    reach_consensus,
    prepare_exit_bus_report,
)
from utils.test.simple_dvt_helpers import simple_dvt_add_node_operators, simple_dvt_add_keys, simple_dvt_vet_keys


@dataclasses.dataclass
class ProcessingState:
    current_frame_ref_slot: int
    processing_deadline_slot: int
    data_hash: HexString
    data_submitted: bool
    data_format: int
    requests_count: int
    requests_submitted: int


def _wait_for_next_ref_slot():
    wait_to_next_available_report_time(contracts.hash_consensus_for_validators_exit_bus_oracle)
    ref_slot, _ = contracts.hash_consensus_for_validators_exit_bus_oracle.getCurrentFrame()
    return ref_slot


def send_report_with_consensus(ref_slot, report, report_hash):
    consensus_version = contracts.validators_exit_bus_oracle.getConsensusVersion()
    contract_version = contracts.validators_exit_bus_oracle.getContractVersion()

    submitter = reach_consensus(
        ref_slot, report_hash, consensus_version, contracts.hash_consensus_for_validators_exit_bus_oracle
    )

    return contracts.validators_exit_bus_oracle.submitReportData(report, contract_version, {"from": submitter})


def test_send_zero_validators_to_exit(helpers):
    ref_slot = _wait_for_next_ref_slot()
    report, report_hash = prepare_exit_bus_report([], ref_slot)
    report_hash_hex = HexString(report_hash, "bytes")

    # Collect state before
    total_requests_before = contracts.validators_exit_bus_oracle.getTotalRequestsProcessed()
    last_processing_ref_slot_before = contracts.validators_exit_bus_oracle.getLastProcessingRefSlot()
    processing_state_before = ProcessingState(*contracts.validators_exit_bus_oracle.getProcessingState())

    tx = send_report_with_consensus(ref_slot, report, report_hash)

    # Collect state after
    total_requests_after = contracts.validators_exit_bus_oracle.getTotalRequestsProcessed()
    last_processing_ref_slot_after = contracts.validators_exit_bus_oracle.getLastProcessingRefSlot()
    processing_state_after = ProcessingState(*contracts.validators_exit_bus_oracle.getProcessingState())

    # Asserts
    helpers.assert_single_event_named("ProcessingStarted", tx, {"refSlot": ref_slot, "hash": report_hash_hex})
    helpers.assert_event_not_emitted("ValidatorExitRequest", tx)

    assert total_requests_after == total_requests_before

    assert last_processing_ref_slot_after != last_processing_ref_slot_before
    assert last_processing_ref_slot_after == ref_slot

    assert processing_state_before != processing_state_after
    assert processing_state_after.data_hash == report_hash_hex
    assert processing_state_after.data_submitted
    assert processing_state_after.data_format == contracts.validators_exit_bus_oracle.DATA_FORMAT_LIST()
    assert processing_state_after.requests_count == processing_state_before.requests_count
    assert processing_state_after.requests_submitted == processing_state_before.requests_submitted


def test_send_validator_to_exit(helpers, web3):
    no_global_index = (module_id, no_id) = (1, 33)
    validator_id = 1
    validator_key = contracts.node_operators_registry.getSigningKey(no_id, validator_id)[0]

    # set validator index to the next one to avoid NodeOpValidatorIndexMustIncrease error
    last_requested_validator_index = contracts.validators_exit_bus_oracle.getLastRequestedValidatorIndices(
        module_id, [no_id]
    )[0]
    validator = LidoValidator(index=last_requested_validator_index + 1, pubkey=validator_key)

    ref_slot = _wait_for_next_ref_slot()
    report, report_hash = prepare_exit_bus_report([(no_global_index, validator)], ref_slot)
    report_hash_hex = HexString(report_hash, "bytes")

    # Collect state before
    total_requests_before = contracts.validators_exit_bus_oracle.getTotalRequestsProcessed()
    last_processing_ref_slot_before = contracts.validators_exit_bus_oracle.getLastProcessingRefSlot()
    processing_state_before = ProcessingState(*contracts.validators_exit_bus_oracle.getProcessingState())

    tx = send_report_with_consensus(ref_slot, report, report_hash)

    # Collect state after
    total_requests_after = contracts.validators_exit_bus_oracle.getTotalRequestsProcessed()
    last_processing_ref_slot_after = contracts.validators_exit_bus_oracle.getLastProcessingRefSlot()
    processing_state_after = ProcessingState(*contracts.validators_exit_bus_oracle.getProcessingState())
    last_requested_validator_index_after = contracts.validators_exit_bus_oracle.getLastRequestedValidatorIndices(
        module_id, [no_id]
    )

    # Asserts
    helpers.assert_single_event_named("ProcessingStarted", tx, {"refSlot": ref_slot, "hash": report_hash_hex})
    helpers.assert_single_event_named(
        "ValidatorExitRequest",
        tx,
        {
            "stakingModuleId": module_id,
            "nodeOperatorId": no_id,
            "validatorIndex": last_requested_validator_index + 1,
            "validatorPubkey": validator_key,
            "timestamp": web3.eth.get_block(web3.eth.block_number).timestamp,
        },
    )

    assert total_requests_after == total_requests_before + 1

    assert last_requested_validator_index_after == (last_requested_validator_index + 1,)
    assert last_processing_ref_slot_after != last_processing_ref_slot_before
    assert last_processing_ref_slot_after == ref_slot

    assert processing_state_before != processing_state_after
    assert processing_state_after.data_hash == report_hash_hex
    assert processing_state_after.data_submitted
    assert processing_state_after.data_format == contracts.validators_exit_bus_oracle.DATA_FORMAT_LIST()
    assert processing_state_after.requests_count == processing_state_before.requests_count + 1
    assert processing_state_after.requests_submitted == processing_state_before.requests_submitted + 1


def test_send_multiple_validators_to_exit(helpers, web3, stranger):
    """
    The same as test above but with multiple validators on different node operators and modules
    """
    # Fill SDVT
    simple_dvt_add_node_operators(
        contracts.simple_dvt, stranger, [("SDVT Operator", f"0xab{'1' * 38}", f"0xcd{'1' * 38}")]
    )
    simple_dvt_add_keys(contracts.simple_dvt, 0, 2)
    simple_dvt_vet_keys(0, stranger)

    first_no_global_index = (first_module_id, first_no_id) = (1, 30)
    second_no_global_index = (second_module_id, second_no_id) = (1, 33)
    third_no_global_index = (third_module_id, third_no_id) = (2, 0)
    first_validator_id = 2
    second_validator_id = 3
    third_validator_id = 0
    first_validator_index = (
        contracts.validators_exit_bus_oracle.getLastRequestedValidatorIndices(first_module_id, [first_no_id])[0] + 1
    )
    second_validator_index = (
        contracts.validators_exit_bus_oracle.getLastRequestedValidatorIndices(second_module_id, [second_no_id])[0] + 1
    )
    third_validator_index = (
        contracts.validators_exit_bus_oracle.getLastRequestedValidatorIndices(third_module_id, [third_no_id])[0] + 1
    )

    first_validator_key = contracts.node_operators_registry.getSigningKey(first_no_id, first_validator_id)[0]
    second_validator_key = contracts.node_operators_registry.getSigningKey(second_no_id, second_validator_id)[0]
    third_validator_key = contracts.simple_dvt.getSigningKey(third_no_id, third_validator_id)[0]
    first_validator = LidoValidator(index=first_validator_index, pubkey=first_validator_key)
    second_validator = LidoValidator(index=second_validator_index, pubkey=second_validator_key)
    third_validator = LidoValidator(index=third_validator_index, pubkey=third_validator_key)

    ref_slot = _wait_for_next_ref_slot()
    report, report_hash = prepare_exit_bus_report(
        [
            (first_no_global_index, first_validator),
            (second_no_global_index, second_validator),
            (third_no_global_index, third_validator),
        ],
        ref_slot,
    )
    report_hash_hex = HexString(report_hash, "bytes")

    # Collect state before
    total_requests_before = contracts.validators_exit_bus_oracle.getTotalRequestsProcessed()
    last_processing_ref_slot_before = contracts.validators_exit_bus_oracle.getLastProcessingRefSlot()
    processing_state_before = ProcessingState(*contracts.validators_exit_bus_oracle.getProcessingState())

    tx = send_report_with_consensus(ref_slot, report, report_hash)

    # Collect state after
    total_requests_after = contracts.validators_exit_bus_oracle.getTotalRequestsProcessed()
    last_processing_ref_slot_after = contracts.validators_exit_bus_oracle.getLastProcessingRefSlot()
    processing_state_after = ProcessingState(*contracts.validators_exit_bus_oracle.getProcessingState())
    first_last_requested_validator_index_after = contracts.validators_exit_bus_oracle.getLastRequestedValidatorIndices(
        first_module_id, [first_no_id]
    )
    second_last_requested_validator_index_after = contracts.validators_exit_bus_oracle.getLastRequestedValidatorIndices(
        second_module_id, [second_no_id]
    )
    third_last_requested_validator_index_after = contracts.validators_exit_bus_oracle.getLastRequestedValidatorIndices(
        third_module_id, [third_no_id]
    )

    # Asserts
    helpers.assert_single_event_named("ProcessingStarted", tx, {"refSlot": ref_slot, "hash": report_hash_hex})
    events = helpers.filter_events_from(tx.receiver, tx.events["ValidatorExitRequest"])
    assert len(events) == 3
    assert dict(events[0]) == {
        "stakingModuleId": first_module_id,
        "nodeOperatorId": first_no_id,
        "validatorIndex": first_validator_index,
        "validatorPubkey": first_validator_key,
        "timestamp": web3.eth.get_block(web3.eth.block_number).timestamp,
    }
    assert dict(events[1]) == {
        "stakingModuleId": second_module_id,
        "nodeOperatorId": second_no_id,
        "validatorIndex": second_validator_index,
        "validatorPubkey": second_validator_key,
        "timestamp": web3.eth.get_block(web3.eth.block_number).timestamp,
    }
    assert dict(events[2]) == {
        "stakingModuleId": third_module_id,
        "nodeOperatorId": third_no_id,
        "validatorIndex": third_validator_index,
        "validatorPubkey": third_validator_key,
        "timestamp": web3.eth.get_block(web3.eth.block_number).timestamp,
    }

    assert total_requests_after == total_requests_before + 3

    assert first_last_requested_validator_index_after == (first_validator_index,)
    assert second_last_requested_validator_index_after == (second_validator_index,)
    assert third_last_requested_validator_index_after == (third_validator_index,)
    assert last_processing_ref_slot_after != last_processing_ref_slot_before
    assert last_processing_ref_slot_after == ref_slot

    assert processing_state_before != processing_state_after
    assert processing_state_after.data_hash == report_hash_hex
    assert processing_state_after.data_submitted
    assert processing_state_after.data_format == contracts.validators_exit_bus_oracle.DATA_FORMAT_LIST()
    assert processing_state_after.requests_count == processing_state_before.requests_count + 3
    assert processing_state_after.requests_submitted == processing_state_before.requests_submitted + 3
