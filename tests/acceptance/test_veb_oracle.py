import pytest
from brownie import interface  # type: ignore

from utils.config import (
    contracts,
    lido_dao_hash_consensus_for_validators_exit_bus_oracle,
    lido_dao_hash_consensus_for_accounting_oracle,
    lido_dao_validators_exit_bus_oracle_implementation,
    lido_dao_validators_exit_bus_oracle,
    oracle_committee,
    CHAIN_SLOTS_PER_EPOCH,
    CHAIN_SECONDS_PER_SLOT,
    CHAIN_GENESIS_TIME,
    VALIDATORS_EXIT_BUS_ORACLE_EPOCHS_PER_FRAME,
    FAST_LANE_LENGTH_SLOTS,
    ORACLE_QUORUM,
)

last_seen_ref_slot = 6189855


@pytest.fixture(scope="module")
def contract() -> interface.ValidatorsExitBusOracle:
    return interface.ValidatorsExitBusOracle(lido_dao_validators_exit_bus_oracle)


def test_proxy(contract):
    proxy = interface.OssifiableProxy(contract)
    assert proxy.proxy__getImplementation() == lido_dao_validators_exit_bus_oracle_implementation
    assert proxy.proxy__getAdmin() == contracts.agent.address


def test_immutables(contract):
    assert contract.SECONDS_PER_SLOT() == CHAIN_SECONDS_PER_SLOT
    assert contract.GENESIS_TIME() == CHAIN_GENESIS_TIME


def test_versioned(contract):
    assert contract.getContractVersion() == 1


def test_consensus(contract):
    assert contract.getConsensusVersion() == 1
    assert contract.getConsensusContract() == lido_dao_hash_consensus_for_validators_exit_bus_oracle


def test_processing_state(contract):
    assert contract.getTotalRequestsProcessed() == 0
    state = contract.getProcessingState()
    assert state["currentFrameRefSlot"] >= last_seen_ref_slot
    assert state["processingDeadlineTime"] == 0
    assert state["dataHash"] == "0x0000000000000000000000000000000000000000000000000000000000000000"
    assert state["dataSubmitted"] == False
    assert state["dataFormat"] == 0
    assert state["requestsCount"] == 0
    assert state["requestsSubmitted"] == 0

    assert contract.getLastProcessingRefSlot() == 0


def test_report(contract):
    report = contract.getConsensusReport()
    assert report["hash"] == "0x0000000000000000000000000000000000000000000000000000000000000000"
    assert report["refSlot"] == 0
    assert report["processingDeadlineTime"] == 0
    assert report["processingStarted"] == False


def test_vebo_hash_consensus_synced_with_accounting_one(contract):
    consensus = interface.HashConsensus(contract.getConsensusContract())
    frameConfig = consensus.getFrameConfig()
    accounting_consensus = interface.HashConsensus(lido_dao_hash_consensus_for_accounting_oracle)

    assert frameConfig["initialEpoch"] == accounting_consensus.getFrameConfig()["initialEpoch"]
    assert frameConfig["epochsPerFrame"] == VALIDATORS_EXIT_BUS_ORACLE_EPOCHS_PER_FRAME
    assert frameConfig["fastLaneLengthSlots"] == FAST_LANE_LENGTH_SLOTS

    assert consensus.getInitialRefSlot() == accounting_consensus.getInitialRefSlot()


def test_vebo_hash_consensus(contract):
    # HashConsensus
    consensus = interface.HashConsensus(contract.getConsensusContract())

    currentFrame = consensus.getCurrentFrame()
    assert currentFrame["refSlot"] >= last_seen_ref_slot
    assert currentFrame["reportProcessingDeadlineSlot"] > last_seen_ref_slot

    chainConfig = consensus.getChainConfig()
    assert chainConfig["slotsPerEpoch"] == CHAIN_SLOTS_PER_EPOCH
    assert chainConfig["secondsPerSlot"] == CHAIN_SECONDS_PER_SLOT
    assert chainConfig["genesisTime"] == CHAIN_GENESIS_TIME

    assert consensus.getQuorum() == ORACLE_QUORUM

    members = consensus.getMembers()
    assert members["addresses"] == oracle_committee
