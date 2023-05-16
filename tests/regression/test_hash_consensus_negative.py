import pytest

from brownie import reverts, web3, ZERO_ADDRESS

from utils.config import contracts
from utils.evm_script import encode_error
from utils.test.oracle_report_helpers import (
    wait_to_next_available_report_time,
    prepare_accounting_report, prepare_exit_bus_report,
)


@pytest.fixture(params=["accounting", "exit_bus"])
def contract_variants(request):
    if request.param == "accounting":
        return contracts.hash_consensus_for_accounting_oracle, contracts.accounting_oracle
    elif request.param == "exit_bus":
        return contracts.hash_consensus_for_validators_exit_bus_oracle, contracts.validators_exit_bus_oracle


@pytest.fixture
def consensus_contract(contract_variants):
    return contract_variants[0]


@pytest.fixture
def oracle_contract(contract_variants):
    return contract_variants[1]


def valid_report_hash(consensus_contract):
    ref_slot, _ = consensus_contract.getCurrentFrame()
    if consensus_contract == contracts.hash_consensus_for_accounting_oracle:
        prev_report = contracts.lido.getBeaconStat().dict()
        beacon_validators = prev_report["beaconValidators"]
        beacon_balance = prev_report["beaconBalance"]
        (items, hash) = prepare_accounting_report(
            refSlot=ref_slot,
            clBalance=beacon_balance,
            numValidators=beacon_validators,
            withdrawalVaultBalance=0,
            elRewardsVaultBalance=0,
            sharesRequestedToBurn=0,
            simulatedShareRate=0,
        )
    elif consensus_contract == contracts.hash_consensus_for_validators_exit_bus_oracle:
        (items, hash) = prepare_exit_bus_report([], ref_slot)
    else:
        raise ValueError("Unknown consensus contract")
    return items, hash


def test_update_initial_epoch(consensus_contract):
    """
    - InitialEpochRefSlotCannotBeEarlierThanProcessingSlot can not be received after contract initialization
    """
    with reverts(encode_error("InitialEpochAlreadyArrived()")):
        consensus_contract.updateInitialEpoch(1, {"from": contracts.agent})


def test_set_frame_config(consensus_contract, stranger):
    slots_per_epoch, _, _ = consensus_contract.getChainConfig()
    consensus_contract.grantRole(
        web3.keccak(text="MANAGE_FRAME_CONFIG_ROLE"),
        stranger,
        {"from": contracts.agent},
    )

    with reverts(encode_error("EpochsPerFrameCannotBeZero()")):
        consensus_contract.setFrameConfig(0, 1, {"from": stranger})

    with reverts(encode_error("FastLanePeriodCannotBeLongerThanFrame()")):
        epochs_per_frame = 2
        consensus_contract.setFrameConfig(epochs_per_frame, epochs_per_frame * slots_per_epoch + 1, {"from": stranger})


def test_set_fast_lane_length_slots(consensus_contract, stranger):
    slots_per_epoch, _, _ = consensus_contract.getChainConfig()
    _, epochs_per_frame, _ = consensus_contract.getFrameConfig()
    consensus_contract.grantRole(
        web3.keccak(text="MANAGE_FAST_LANE_CONFIG_ROLE"),
        stranger,
        {"from": contracts.agent},
    )

    with reverts(encode_error("FastLanePeriodCannotBeLongerThanFrame()")):
        consensus_contract.setFastLaneLengthSlots(epochs_per_frame * slots_per_epoch + 1, {"from": stranger})


def test_add_member(consensus_contract, stranger):
    consensus_contract.grantRole(
        web3.keccak(text="MANAGE_MEMBERS_AND_QUORUM_ROLE"),
        stranger,
        {"from": contracts.agent},
    )
    current_quorum = consensus_contract.getQuorum()
    members, *_ = consensus_contract.getMembers()

    with reverts(encode_error("DuplicateMember()")):
        consensus_contract.addMember(members[0], current_quorum, {"from": stranger})

    with reverts(encode_error("AddressCannotBeZero()")):
        consensus_contract.addMember(ZERO_ADDRESS, current_quorum, {"from": stranger})

    required_quorum = (len(members) + 1) // 2 + 1  # extra +1 for the new member
    with reverts(encode_error(f"QuorumTooSmall(uint256,uint256)", [required_quorum, required_quorum - 1])):
        consensus_contract.addMember(stranger, required_quorum - 1, {"from": stranger})


def test_remove_member(consensus_contract, stranger):
    consensus_contract.grantRole(
        web3.keccak(text="MANAGE_MEMBERS_AND_QUORUM_ROLE"),
        stranger,
        {"from": contracts.agent},
    )
    members, *_ = consensus_contract.getMembers()

    with reverts(encode_error("NonMember()")):
        consensus_contract.removeMember(stranger, 1, {"from": stranger})

    required_quorum = (len(members) - 1) // 2 + 1  # -1 for the removed member
    with reverts(encode_error(f"QuorumTooSmall(uint256,uint256)", [required_quorum, required_quorum - 1])):
        consensus_contract.removeMember(members[0], required_quorum - 1, {"from": stranger})


def test_set_quorum(consensus_contract, stranger):
    consensus_contract.grantRole(
        web3.keccak(text="MANAGE_MEMBERS_AND_QUORUM_ROLE"),
        stranger,
        {"from": contracts.agent},
    )
    members, *_ = consensus_contract.getMembers()

    required_quorum = len(members) // 2 + 1
    with reverts(encode_error(f"QuorumTooSmall(uint256,uint256)", [required_quorum, required_quorum - 1])):
        consensus_contract.removeMember(members[0], required_quorum - 1, {"from": stranger})


def test_set_report_processor(consensus_contract, stranger):
    consensus_contract.grantRole(
        web3.keccak(text="MANAGE_REPORT_PROCESSOR_ROLE"),
        stranger,
        {"from": contracts.agent},
    )
    prev_report_processor = consensus_contract.getReportProcessor()

    with reverts(encode_error("ReportProcessorCannotBeZero()")):
        consensus_contract.setReportProcessor(ZERO_ADDRESS, {"from": stranger})

    with reverts(encode_error("NewProcessorCannotBeTheSame()")):
        consensus_contract.setReportProcessor(prev_report_processor, {"from": stranger})


def test_submit_report(consensus_contract, oracle_contract, stranger):

    """
    - StaleReport can not be received because DEADLINE_SLOT_OFFSET is zero
    """
    wait_to_next_available_report_time(consensus_contract)
    valid_report, valid_hash = valid_report_hash(consensus_contract)
    consensus_version = oracle_contract.getConsensusVersion()
    contract_version = oracle_contract.getContractVersion()
    members, _ = consensus_contract.getMembers()
    member = members[0]
    fast_lane_members, _ = consensus_contract.getFastLaneMembers()
    fast_lane_member = fast_lane_members[0]
    non_fast_lane_members = [m for m in members if m not in fast_lane_members]
    # we get the second in order to receive a non-zero fast lane subset
    second_non_fastlane_member = non_fast_lane_members[1]

    with reverts(encode_error("InvalidSlot()")):
        consensus_contract.submitReport(0, valid_hash, consensus_version, {"from": member})

    with reverts(encode_error("NumericOverflow()")):
        consensus_contract.submitReport(2 ** 64, valid_hash, consensus_version, {"from": member})

    with reverts(encode_error("EmptyReport()")):
        consensus_contract.submitReport(1, int.to_bytes(0, 32, 'big'), consensus_version, {"from": member})

    with reverts(encode_error("NonMember()")):
        consensus_contract.submitReport(1, valid_hash, consensus_version, {"from": stranger})

    with reverts(
        encode_error("UnexpectedConsensusVersion(uint256,uint256)", (consensus_version, consensus_version + 1))):
        consensus_contract.submitReport(1, valid_hash, consensus_version + 1, {"from": member})

    with reverts(encode_error("InvalidSlot()")):
        consensus_contract.submitReport(1, valid_hash, consensus_version, {"from": member})

    # reaching consensus
    ref_slot, _ = consensus_contract.getCurrentFrame()
    for m in fast_lane_members:
        consensus_contract.submitReport(ref_slot, valid_hash, consensus_version, {"from": m})

    with reverts(encode_error("DuplicateReport()")):
        consensus_contract.submitReport(ref_slot, valid_hash, consensus_version, {"from": fast_lane_member})

    # start processing
    oracle_contract.submitReportData(valid_report, contract_version, {"from": member})
    with reverts(encode_error("ConsensusReportAlreadyProcessing()")):
        consensus_contract.submitReport(ref_slot, valid_hash, consensus_version, {"from": fast_lane_member})

    wait_to_next_available_report_time(consensus_contract)
    ref_slot, _ = consensus_contract.getCurrentFrame()
    with reverts(encode_error("NonFastLaneMemberCannotReportWithinFastLaneInterval()")):
        consensus_contract.submitReport(ref_slot, valid_hash, consensus_version, {"from": second_non_fastlane_member})
