import pytest
from brownie import interface, reverts  # type: ignore

from utils.config import (
    contracts,
    HASH_CONSENSUS_FOR_AO,
    ACCOUNTING_ORACLE_IMPL,
    ACCOUNTING_ORACLE,
    ORACLE_COMMITTEE,
    AO_EPOCHS_PER_FRAME,
    AO_FAST_LANE_LENGTH_SLOTS,
    CHAIN_SLOTS_PER_EPOCH,
    CHAIN_SECONDS_PER_SLOT,
    CHAIN_GENESIS_TIME,
    ORACLE_QUORUM,
    AO_CONSENSUS_VERSION,
)


@pytest.fixture(scope="module")
def contract() -> interface.AccountingOracle:
    return interface.AccountingOracle(ACCOUNTING_ORACLE)


def test_proxy(contract):
    proxy = interface.OssifiableProxy(contract)
    assert proxy.proxy__getImplementation() == ACCOUNTING_ORACLE_IMPL
    assert proxy.proxy__getAdmin() == contracts.agent.address


def test_constants(contract):
    assert contract.LOCATOR() == contracts.lido_locator
    assert contract.EXTRA_DATA_FORMAT_EMPTY() == 0
    assert contract.EXTRA_DATA_FORMAT_LIST() == 1
    assert contract.EXTRA_DATA_TYPE_STUCK_VALIDATORS() == 1
    assert contract.EXTRA_DATA_TYPE_EXITED_VALIDATORS() == 2
    assert contract.SECONDS_PER_SLOT() == CHAIN_SECONDS_PER_SLOT
    assert contract.GENESIS_TIME() == CHAIN_GENESIS_TIME


def test_versioned(contract):
    assert contract.getContractVersion() == 5  # SRv3: finalizeUpgrade_v5


def test_initialize(contract):
    with reverts("NonZeroContractVersionOnInit: "):
        contract.initialize(
            contract.getRoleMember(contract.DEFAULT_ADMIN_ROLE(), 0),
            HASH_CONSENSUS_FOR_AO,
            AO_CONSENSUS_VERSION,
            1,
            {"from": contracts.voting},
        )


def test_petrified(contract):
    impl = interface.AccountingOracle(ACCOUNTING_ORACLE_IMPL)
    with reverts("NonZeroContractVersionOnInit: "):
        impl.initialize(
            contract.getRoleMember(contract.DEFAULT_ADMIN_ROLE(), 0),
            HASH_CONSENSUS_FOR_AO,
            AO_CONSENSUS_VERSION,
            1,
            {"from": contracts.voting},
        )


def test_consensus(contract):
    assert contract.getConsensusVersion() == AO_CONSENSUS_VERSION
    assert contract.getConsensusContract() == HASH_CONSENSUS_FOR_AO


def test_processing_state(contract):
    consensus = interface.HashConsensus(contract.getConsensusContract())
    state = contract.getProcessingState()

    # frame cross-check with the consensus contract
    assert state["currentFrameRefSlot"] == consensus.getCurrentFrame()["refSlot"]
    assert state["currentFrameRefSlot"] > 5254400

    # processing never runs ahead of the current frame
    assert contract.getLastProcessingRefSlot() <= state["currentFrameRefSlot"]

    if state["mainDataSubmitted"]:
        # a submitted report implies processing of the current frame has started
        assert state["mainDataHash"] != "0x" + "00" * 32
        assert contract.getLastProcessingRefSlot() == state["currentFrameRefSlot"]

    # extra data can only follow the main report
    if state["extraDataSubmitted"]:
        assert state["mainDataSubmitted"]
    assert state["extraDataItemsSubmitted"] <= state["extraDataItemsCount"]


def test_report(contract):
    report = contract.getConsensusReport()
    assert report["refSlot"] <= contract.getProcessingState()["currentFrameRefSlot"]


def test_accounting_hash_consensus(contract):
    # HashConsensus
    consensus = interface.HashConsensus(contract.getConsensusContract())

    current_frame = consensus.getCurrentFrame()
    assert current_frame["refSlot"] > 5254400
    assert current_frame["reportProcessingDeadlineSlot"] > 5254400

    chain_config = consensus.getChainConfig()
    assert chain_config["slotsPerEpoch"] == CHAIN_SLOTS_PER_EPOCH
    assert chain_config["secondsPerSlot"] == CHAIN_SECONDS_PER_SLOT
    assert chain_config["genesisTime"] == CHAIN_GENESIS_TIME

    frame_config = consensus.getFrameConfig()
    assert frame_config["initialEpoch"] > 5254400 / CHAIN_SLOTS_PER_EPOCH
    assert frame_config["epochsPerFrame"] == AO_EPOCHS_PER_FRAME
    assert frame_config["fastLaneLengthSlots"] == AO_FAST_LANE_LENGTH_SLOTS

    assert consensus.getInitialRefSlot() > 5254400

    assert consensus.getQuorum() == ORACLE_QUORUM

    members = consensus.getMembers()
    assert sorted(members["addresses"]) == sorted(ORACLE_COMMITTEE)
