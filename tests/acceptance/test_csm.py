import pytest

from brownie import interface, web3, Wei  # type: ignore
from brownie.convert.datatypes import HexString

from utils.config import (
    contracts,
    ContractsLazyLoader,
    LIDO_LOCATOR,
    LIDO,
    WITHDRAWAL_QUEUE,
    WITHDRAWAL_VAULT,
    WSTETH_TOKEN,
    AGENT,
    BURNER,
    CSM_ADDRESS,
    CS_ACCOUNTING_ADDRESS,
    CS_FEE_DISTRIBUTOR_ADDRESS,
    CS_FEE_ORACLE_ADDRESS,
    CS_ORACLE_HASH_CONSENSUS_ADDRESS,
    CHAIN_SECONDS_PER_SLOT,
    CHAIN_GENESIS_TIME,
    CHAIN_SLOTS_PER_EPOCH,
    CS_ORACLE_EPOCHS_PER_FRAME,
    ORACLE_QUORUM,
    ORACLE_COMMITTEE,
)

contracts: ContractsLazyLoader = contracts


def _str_to_bytes32(s: str) -> str:
    return "0x{:0<64}".format(s.encode("utf-8").hex())


@pytest.fixture(scope="module")
def csm():
    return contracts.csm

@pytest.fixture(scope="module")
def early_adoption():
    return contracts.cs_early_adoption

@pytest.fixture(scope="module")
def fee_distributor():
    return contracts.cs_fee_distributor

@pytest.fixture(scope="module")
def fee_oracle():
    return contracts.cs_fee_oracle

@pytest.fixture(scope="module")
def hash_consensus():
    return contracts.csm_hash_consensus

@pytest.fixture(scope="module")
def accounting():
    return contracts.cs_accounting

@pytest.fixture(scope="module")
def verifier():
    return contracts.cs_verifier


@pytest.fixture(scope="module")
def lido():
    return interface.Lido(LIDO)

def test_proxy(csm, accounting, fee_distributor, fee_oracle):
    assert interface.OssifiableProxy(csm).proxy__getAdmin() == contracts.agent.address
    assert interface.OssifiableProxy(accounting).proxy__getAdmin() == contracts.agent.address
    assert interface.OssifiableProxy(fee_distributor).proxy__getAdmin() == contracts.agent.address
    assert interface.OssifiableProxy(fee_oracle).proxy__getAdmin() == contracts.agent.address


class TestCSM:
    def test_init_state(self, csm):
        assert csm.getType() == _str_to_bytes32("community-onchain-v1")
        assert csm.LIDO_LOCATOR() == LIDO_LOCATOR
        assert csm.accounting() == CS_ACCOUNTING_ADDRESS

        assert not csm.isPaused();
        assert not csm.publicRelease();


class TestAccounting:
    def test_initial_state(self, accounting):
        assert accounting.CSM() == CSM_ADDRESS
        assert accounting.LIDO_LOCATOR() == LIDO_LOCATOR
        assert accounting.LIDO() == LIDO
        assert accounting.WITHDRAWAL_QUEUE() == WITHDRAWAL_QUEUE
        assert accounting.WSTETH() == WSTETH_TOKEN
        assert accounting.feeDistributor() == CS_FEE_DISTRIBUTOR_ADDRESS
        assert accounting.chargePenaltyRecipient() == AGENT
        assert not accounting.isPaused()

    def test_allowances(self, lido):
        uin256_max = 2 ** 256 - 1
        assert lido.allowance(CS_ACCOUNTING_ADDRESS, WSTETH_TOKEN) == uin256_max
        assert lido.allowance(CS_ACCOUNTING_ADDRESS, WITHDRAWAL_QUEUE) == uin256_max
        assert lido.allowance(CS_ACCOUNTING_ADDRESS, BURNER) == uin256_max

class TestFeeDistributor:

    def test_initial_state(self, fee_distributor):
        assert fee_distributor.STETH() == LIDO
        assert fee_distributor.ACCOUNTING() == CS_ACCOUNTING_ADDRESS
        assert fee_distributor.ORACLE() == CS_FEE_ORACLE_ADDRESS


class TestFeeOracle:

    def test_initial_state(self, fee_oracle):
        assert fee_oracle.SECONDS_PER_SLOT() == CHAIN_SECONDS_PER_SLOT
        assert fee_oracle.GENESIS_TIME() == CHAIN_GENESIS_TIME
        assert fee_oracle.feeDistributor() == CS_FEE_DISTRIBUTOR_ADDRESS
        assert fee_oracle.getContractVersion() == 1
        assert fee_oracle.getConsensusContract() == CS_ORACLE_HASH_CONSENSUS_ADDRESS
        assert fee_oracle.getConsensusVersion() == 1
        assert fee_oracle.avgPerfLeewayBP() == 500
        assert not fee_oracle.isPaused()

class TestHashConsensus:

    def test_initial_state(self, hash_consensus):
        chain_config = hash_consensus.getChainConfig()
        assert chain_config["slotsPerEpoch"] == CHAIN_SLOTS_PER_EPOCH
        assert chain_config["secondsPerSlot"] == CHAIN_SECONDS_PER_SLOT
        assert chain_config["genesisTime"] == CHAIN_GENESIS_TIME

        frame_config = hash_consensus.getFrameConfig()
        assert frame_config["initialEpoch"] >= 326715
        assert frame_config["epochsPerFrame"] == CS_ORACLE_EPOCHS_PER_FRAME
        assert frame_config["fastLaneLengthSlots"] == 1800

        assert hash_consensus.getQuorum() == ORACLE_QUORUM

        assert hash_consensus.getInitialRefSlot() >= 326715 * CHAIN_SLOTS_PER_EPOCH - 1

        members = hash_consensus.getMembers()
        assert sorted(members["addresses"]) == sorted(ORACLE_COMMITTEE)

        assert hash_consensus.getReportProcessor() == CS_FEE_ORACLE_ADDRESS

def test_early_adoption_state(early_adoption):
    assert early_adoption.MODULE() == CSM_ADDRESS
    assert early_adoption.CURVE_ID() == 1

def test_verifier_state(verifier):
    assert verifier.WITHDRAWAL_ADDRESS() == WITHDRAWAL_VAULT
    assert verifier.MODULE() == CSM_ADDRESS
    assert verifier.SLOTS_PER_EPOCH() == CHAIN_SLOTS_PER_EPOCH
    print(type(verifier.GI_HISTORICAL_SUMMARIES_PREV()))
    assert verifier.GI_HISTORICAL_SUMMARIES_PREV() == HexString("0x0000000000000000000000000000000000000000000000000000000000003b00", "bytes")
    assert verifier.GI_HISTORICAL_SUMMARIES_CURR() == HexString("0x0000000000000000000000000000000000000000000000000000000000003b00", "bytes")
    assert verifier.GI_FIRST_WITHDRAWAL_PREV() == HexString("0x0000000000000000000000000000000000000000000000000000000000e1c004", "bytes")
    assert verifier.GI_FIRST_WITHDRAWAL_CURR() == HexString("0x0000000000000000000000000000000000000000000000000000000000e1c004", "bytes")
    assert verifier.GI_FIRST_VALIDATOR_PREV() == HexString("0x0000000000000000000000000000000000000000000000000056000000000028", "bytes")
    assert verifier.GI_FIRST_VALIDATOR_CURR() == HexString("0x0000000000000000000000000000000000000000000000000056000000000028", "bytes")
    assert verifier.FIRST_SUPPORTED_SLOT() == 8626176
    assert verifier.PIVOT_SLOT() == 8626176
