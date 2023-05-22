import pytest
from brownie import interface, reverts  # type: ignore

from utils.config import (
    contracts,
    HASH_CONSENSUS_FOR_VEBO,
    HASH_CONSENSUS_FOR_AO,
    VALIDATORS_EXIT_BUS_ORACLE_IMPL,
    VALIDATORS_EXIT_BUS_ORACLE,
    ORACLE_COMMITTEE,
    CHAIN_SLOTS_PER_EPOCH,
    CHAIN_SECONDS_PER_SLOT,
    CHAIN_GENESIS_TIME,
    VEBO_EPOCHS_PER_FRAME,
    VEBO_FAST_LANE_LENGTH_SLOTS,
    ORACLE_QUORUM,
    VEBO_CONSENSUS_VERSION,
)
from utils.evm_script import encode_error

last_seen_ref_slot = 6189855


@pytest.fixture(scope="module")
def contract() -> interface.ValidatorsExitBusOracle:
    return interface.ValidatorsExitBusOracle(VALIDATORS_EXIT_BUS_ORACLE)


def test_proxy(contract):
    proxy = interface.OssifiableProxy(contract)
    assert proxy.proxy__getImplementation() == VALIDATORS_EXIT_BUS_ORACLE_IMPL
    assert proxy.proxy__getAdmin() == contracts.agent.address


def test_immutables(contract):
    assert contract.SECONDS_PER_SLOT() == CHAIN_SECONDS_PER_SLOT
    assert contract.GENESIS_TIME() == CHAIN_GENESIS_TIME


def test_versioned(contract):
    assert contract.getContractVersion() == 1


def test_initialize(contract):
    with reverts(encode_error("NonZeroContractVersionOnInit()")):
        contract.initialize(
            contract.getRoleMember(contract.DEFAULT_ADMIN_ROLE(), 0),
            HASH_CONSENSUS_FOR_AO,
            1,
            1,
            {"from": contracts.voting},
        )


def test_petrified(contract):
    impl = interface.ValidatorsExitBusOracle(VALIDATORS_EXIT_BUS_ORACLE_IMPL)
    with reverts(encode_error("NonZeroContractVersionOnInit()")):
        impl.initialize(
            contract.getRoleMember(contract.DEFAULT_ADMIN_ROLE(), 0),
            HASH_CONSENSUS_FOR_AO,
            1,
            1,
            {"from": contracts.voting},
        )


def test_consensus(contract):
    assert contract.getConsensusVersion() == VEBO_CONSENSUS_VERSION
    assert contract.getConsensusContract() == HASH_CONSENSUS_FOR_VEBO


def test_vebo_hash_consensus_synced_with_accounting_one(contract):
    consensus = interface.HashConsensus(contract.getConsensusContract())
    frameConfig = consensus.getFrameConfig()
    accounting_consensus = interface.HashConsensus(HASH_CONSENSUS_FOR_AO)

    assert frameConfig["initialEpoch"] == accounting_consensus.getFrameConfig()["initialEpoch"]
    assert frameConfig["epochsPerFrame"] == VEBO_EPOCHS_PER_FRAME
    assert frameConfig["fastLaneLengthSlots"] == VEBO_FAST_LANE_LENGTH_SLOTS

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
    assert members["addresses"] == ORACLE_COMMITTEE
