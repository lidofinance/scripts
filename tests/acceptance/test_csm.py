import pytest

from brownie import interface, web3, Wei  # type: ignore

from utils.config import (
    contracts,
    ContractsLazyLoader,
    LIDO_LOCATOR,
    LIDO,
    WITHDRAWAL_QUEUE,
    WSTETH_TOKEN,
    STAKING_ROUTER,
    AGENT,
    BURNER,
    CSM_ADDRESS,
    CS_ACCOUNTING_ADDRESS,
    CS_GATE_SEAL_ADDRESS,
    CS_VERIFIER_ADDRESS,
    CS_FEE_DISTRIBUTOR_ADDRESS,
    CS_FEE_ORACLE_ADDRESS,
    CS_ORACLE_HASH_CONSENSUS_ADDRESS,
    EASYTRACK_EVMSCRIPT_EXECUTOR,
    CHAIN_SECONDS_PER_SLOT,
    CHAIN_GENESIS_TIME,
    CHAIN_SLOTS_PER_EPOCH,
    CS_ORACLE_EPOCHS_PER_FRAME,
    ORACLE_QUORUM,
    ORACLE_COMMITTEE
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
        assert csm.getNodeOperatorsCount() == 0;


    def test_roles(self, csm):
        assert csm.hasRole(csm.STAKING_ROUTER_ROLE(), STAKING_ROUTER)
        assert csm.hasRole(csm.DEFAULT_ADMIN_ROLE(), AGENT)
        assert csm.hasRole(csm.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS)
        assert csm.hasRole(csm.SETTLE_EL_REWARDS_STEALING_PENALTY_ROLE(), EASYTRACK_EVMSCRIPT_EXECUTOR)
        assert csm.hasRole(csm.VERIFIER_ROLE(), CS_VERIFIER_ADDRESS)

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

    def test_roles(self, accounting):
        assert accounting.hasRole(accounting.SET_BOND_CURVE_ROLE(), CSM_ADDRESS)
        assert accounting.hasRole(accounting.RESET_BOND_CURVE_ROLE(), CSM_ADDRESS)
        assert accounting.hasRole(accounting.DEFAULT_ADMIN_ROLE(), AGENT)
        assert accounting.hasRole(accounting.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS)

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
        assert fee_distributor.totalClaimableShares() == 0
        assert fee_distributor.pendingSharesToDistribute() == 0
        assert fee_distributor.treeRoot() == _str_to_bytes32("")
        assert fee_distributor.treeCid() == ""

    def test_roles(self, fee_distributor):
        assert fee_distributor.hasRole(fee_distributor.DEFAULT_ADMIN_ROLE(), AGENT)


class TestFeeOracle:

    def test_initial_state(self, fee_oracle):
        assert fee_oracle.SECONDS_PER_SLOT() == CHAIN_SECONDS_PER_SLOT
        assert fee_oracle.GENESIS_TIME() == CHAIN_GENESIS_TIME
        assert fee_oracle.feeDistributor() == CS_FEE_DISTRIBUTOR_ADDRESS
        assert fee_oracle.getContractVersion() == 1
        assert fee_oracle.getConsensusContract() == CS_ORACLE_HASH_CONSENSUS_ADDRESS
        assert fee_oracle.getConsensusVersion() == 1
        assert fee_oracle.getLastProcessingRefSlot() == 0
        assert fee_oracle.avgPerfLeewayBP() == 500
        assert not fee_oracle.isPaused()

        report = fee_oracle.getConsensusReport()
        assert report["hash"] == _str_to_bytes32("")
        assert report["refSlot"] == 0
        assert report["processingDeadlineTime"] == 0
        assert not report["processingStarted"]


    def test_roles(self, fee_oracle):
        assert fee_oracle.hasRole(fee_oracle.DEFAULT_ADMIN_ROLE(), AGENT)
        assert fee_oracle.hasRole(fee_oracle.PAUSE_ROLE(), CS_GATE_SEAL_ADDRESS)

class TestHashConsensus:

    def test_initial_state(self, hash_consensus):
        current_frame = hash_consensus.getCurrentFrame()
        # TODO uncomment this when initial ref slot is known
        # assert current_frame["refSlot"] > 5254400
        # assert current_frame["reportProcessingDeadlineSlot"] > 5254400

        chain_config = hash_consensus.getChainConfig()
        assert chain_config["slotsPerEpoch"] == CHAIN_SLOTS_PER_EPOCH
        assert chain_config["secondsPerSlot"] == CHAIN_SECONDS_PER_SLOT
        assert chain_config["genesisTime"] == CHAIN_GENESIS_TIME

        frame_config = hash_consensus.getFrameConfig()
        # TODO uncomment this when initial ref slot is known
        #  assert frame_config["initialEpoch"] > 5254400 / CHAIN_SLOTS_PER_EPOCH
        assert frame_config["epochsPerFrame"] == CS_ORACLE_EPOCHS_PER_FRAME
        assert frame_config["fastLaneLengthSlots"] == 0

        assert hash_consensus.getQuorum() == ORACLE_QUORUM

        # TODO uncomment this when initial ref slot is known
        #  assert hash_consensus.getInitialRefSlot() > 5254400

        members = hash_consensus.getMembers()
        assert members["addresses"] == ORACLE_COMMITTEE

        assert hash_consensus.getReportProcessor() == CS_FEE_ORACLE_ADDRESS

    def test_roles(self, hash_consensus):
        assert hash_consensus.hasRole(hash_consensus.DEFAULT_ADMIN_ROLE(), AGENT)

def test_early_adoption_state(early_adoption):
    assert early_adoption.MODULE() == CSM_ADDRESS
    assert early_adoption.CURVE_ID() == 1

def test_verifier_state(verifier):
    assert verifier.LOCATOR() == LIDO_LOCATOR
    assert verifier.MODULE() == CSM_ADDRESS
    assert verifier.SLOTS_PER_EPOCH() == CHAIN_SLOTS_PER_EPOCH
    # TODO uncomment this when values are known
    # assert verifier.GI_HISTORICAL_SUMMARIES_PREV() == ""
    # assert verifier.GI_HISTORICAL_SUMMARIES_CURR() == ""
    # assert verifier.GI_FIRST_WITHDRAWAL_PREV() == ""
    # assert verifier.GI_FIRST_WITHDRAWAL_CURR() == ""
    # assert verifier.GI_FIRST_VALIDATOR_PREV() == ""
    # assert verifier.GI_FIRST_VALIDATOR_CURR() == ""
    # assert verifier.FIRST_SUPPORTED_SLOT() == ""
