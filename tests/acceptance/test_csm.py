import pytest

from brownie import interface, web3, Wei, reverts  # type: ignore
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
    CS_PARAMS_REGISTRY_ADDRESS,
    CS_EXIT_PENALTIES_ADDRESS,
    CS_STRIKES_ADDRESS,
    CS_EJECTOR_ADDRESS,
    CS_FEE_ORACLE_CONSENSUS_VERSION,
)
from utils.evm_script import encode_error

contracts: ContractsLazyLoader = contracts


def _str_to_bytes32(s: str) -> str:
    return "0x{:0<64}".format(s.encode("utf-8").hex())


@pytest.fixture(scope="module")
def csm():
    return contracts.csm


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
def permissionless_gate():
    return contracts.cs_permissionless_gate


@pytest.fixture(scope="module")
def vetted_gate():
    return contracts.cs_vetted_gate


@pytest.fixture(scope="module")
def parameters_registry():
    return contracts.cs_parameters_registry


@pytest.fixture(scope="module")
def ejector():
    return contracts.cs_ejector


@pytest.fixture(scope="module")
def strikes():
    return contracts.cs_strikes


@pytest.fixture(scope="module")
def exit_penalties():
    return contracts.cs_exit_penalties


@pytest.fixture(scope="module")
def lido():
    return interface.Lido(LIDO)


def test_proxy(
    csm,
    accounting,
    fee_distributor,
    fee_oracle,
    vetted_gate,
    strikes,
    exit_penalties,
):
    assert interface.OssifiableProxy(csm).proxy__getAdmin() == contracts.agent.address
    assert interface.OssifiableProxy(accounting).proxy__getAdmin() == contracts.agent.address
    assert interface.OssifiableProxy(fee_distributor).proxy__getAdmin() == contracts.agent.address
    assert interface.OssifiableProxy(fee_oracle).proxy__getAdmin() == contracts.agent.address
    assert interface.OssifiableProxy(vetted_gate).proxy__getAdmin() == contracts.agent.address
    assert interface.OssifiableProxy(strikes).proxy__getAdmin() == contracts.agent.address
    assert interface.OssifiableProxy(exit_penalties).proxy__getAdmin() == contracts.agent.address


class TestCSM:
    def test_init_state(self, csm):
        assert csm.getType() == _str_to_bytes32("community-onchain-v1")
        assert csm.LIDO_LOCATOR() == LIDO_LOCATOR
        assert csm.PARAMETERS_REGISTRY() == CS_PARAMS_REGISTRY_ADDRESS
        assert csm.ACCOUNTING() == CS_ACCOUNTING_ADDRESS
        assert csm.EXIT_PENALTIES() == CS_EXIT_PENALTIES_ADDRESS

        assert not csm.isPaused()


class TestAccounting:
    def test_initial_state(self, accounting):
        assert accounting.MODULE() == CSM_ADDRESS
        assert accounting.LIDO_LOCATOR() == LIDO_LOCATOR
        assert accounting.LIDO() == LIDO
        assert accounting.WITHDRAWAL_QUEUE() == WITHDRAWAL_QUEUE
        assert accounting.WSTETH() == WSTETH_TOKEN
        assert accounting.FEE_DISTRIBUTOR() == CS_FEE_DISTRIBUTOR_ADDRESS
        assert accounting.chargePenaltyRecipient() == AGENT
        assert not accounting.isPaused()

    def test_allowances(self, lido):
        uin256_max = 2**256 - 1
        assert lido.allowance(CS_ACCOUNTING_ADDRESS, WSTETH_TOKEN) == uin256_max
        assert lido.allowance(CS_ACCOUNTING_ADDRESS, WITHDRAWAL_QUEUE) == uin256_max
        assert lido.allowance(CS_ACCOUNTING_ADDRESS, BURNER) == uin256_max


class TestFeeDistributor:
    def test_initial_state(self, fee_distributor):
        assert fee_distributor.STETH() == LIDO
        assert fee_distributor.ACCOUNTING() == CS_ACCOUNTING_ADDRESS
        assert fee_distributor.ORACLE() == CS_FEE_ORACLE_ADDRESS
        assert fee_distributor.rebateRecipient() == AGENT


class TestFeeOracle:
    def test_initial_state(self, fee_oracle):
        assert fee_oracle.SECONDS_PER_SLOT() == CHAIN_SECONDS_PER_SLOT
        assert fee_oracle.GENESIS_TIME() == CHAIN_GENESIS_TIME
        assert fee_oracle.FEE_DISTRIBUTOR() == CS_FEE_DISTRIBUTOR_ADDRESS
        assert fee_oracle.STRIKES() == CS_STRIKES_ADDRESS
        assert fee_oracle.getContractVersion() == 3  # SRv3: finalizeUpgradeV3 -> INITIALIZED_VERSION
        assert fee_oracle.getConsensusContract() == CS_ORACLE_HASH_CONSENSUS_ADDRESS
        assert fee_oracle.getConsensusVersion() == CS_FEE_ORACLE_CONSENSUS_VERSION
        assert not fee_oracle.isPaused()

    def test_finalize_upgrade_v3_reverts_when_already_finalized(self, fee_oracle):
        # The vote already ran finalizeUpgradeV3, so the FeeOracle is at contract version 3.
        # finalizeUpgradeV3 has no reinitializer/access-control guard; re-calling it must
        # revert because _updateContractVersion(INITIALIZED_VERSION=3) rejects a bump when
        # already at 3. Pass a different consensus version so we reach the contract-version
        # check (the same version would revert earlier in _setConsensusVersion with
        # VersionCannotBeSame). State rolls back on revert.
        # .call() — anvil does not surface custom-error data for reverted txs.
        with reverts(encode_error("InvalidContractVersionIncrement()")):
            fee_oracle.finalizeUpgradeV3.call(CS_FEE_ORACLE_CONSENSUS_VERSION + 1, {"from": contracts.agent})


class TestHashConsensus:
    def test_initial_state(self, hash_consensus):
        chain_config = hash_consensus.getChainConfig()
        assert chain_config["slotsPerEpoch"] == CHAIN_SLOTS_PER_EPOCH
        assert chain_config["secondsPerSlot"] == CHAIN_SECONDS_PER_SLOT
        assert chain_config["genesisTime"] == CHAIN_GENESIS_TIME

        frame_config = hash_consensus.getFrameConfig()
        assert frame_config["initialEpoch"] == 434490
        assert frame_config["epochsPerFrame"] == CS_ORACLE_EPOCHS_PER_FRAME
        assert frame_config["fastLaneLengthSlots"] == 300

        assert hash_consensus.getQuorum() == ORACLE_QUORUM

        assert hash_consensus.getInitialRefSlot() == 13903679

        members = hash_consensus.getMembers()
        assert sorted(members["addresses"]) == sorted(ORACLE_COMMITTEE)

        assert hash_consensus.getReportProcessor() == CS_FEE_ORACLE_ADDRESS


def test_permissionless_gate_state(permissionless_gate):
    assert permissionless_gate.MODULE() == CSM_ADDRESS
    assert permissionless_gate.CURVE_ID() == 0


def test_vetted_gate_state(vetted_gate):
    assert vetted_gate.MODULE() == CSM_ADDRESS
    assert vetted_gate.curveId() == 2


def test_ejector_state(ejector):
    assert ejector.MODULE() == CSM_ADDRESS
    assert ejector.STRIKES() == CS_STRIKES_ADDRESS
    # v3: the immutable STAKING_MODULE_ID() getter is gone. stakingModuleId is now a mutable
    # storage slot lazily filled from StakingRouter on the first ejection (_getOrCacheStakingModuleId),
    # so right after enactment it is still 0 (will resolve to CS_MODULE_ID == 3 on first use).
    assert ejector.stakingModuleId() == 0


def test_strikes_state(strikes):
    assert strikes.MODULE() == CSM_ADDRESS
    assert strikes.EXIT_PENALTIES() == CS_EXIT_PENALTIES_ADDRESS
    assert strikes.ORACLE() == CS_FEE_ORACLE_ADDRESS
    assert strikes.PARAMETERS_REGISTRY() == CS_PARAMS_REGISTRY_ADDRESS
    assert strikes.ejector() == CS_EJECTOR_ADDRESS


def test_exit_penalties_state(exit_penalties):
    assert exit_penalties.MODULE() == CSM_ADDRESS
    assert exit_penalties.PARAMETERS_REGISTRY() == CS_PARAMS_REGISTRY_ADDRESS
    assert exit_penalties.STRIKES() == CS_STRIKES_ADDRESS


def test_parameters_registry_state(parameters_registry):
    assert parameters_registry.QUEUE_LOWEST_PRIORITY() == 5
    # v3: QUEUE_LEGACY_PRIORITY was removed (chore: remove legacy code). Queue priority is now
    # per-curve via defaultQueueConfig (priority, maxDeposits).
    priority, _max_deposits = parameters_registry.defaultQueueConfig()
    assert priority <= parameters_registry.QUEUE_LOWEST_PRIORITY()


def test_verifier_state(verifier):
    assert verifier.WITHDRAWAL_ADDRESS() == WITHDRAWAL_VAULT
    assert verifier.MODULE() == CSM_ADDRESS
    assert verifier.SLOTS_PER_EPOCH() == CHAIN_SLOTS_PER_EPOCH

    assert verifier.GI_FIRST_WITHDRAWAL_PREV() == HexString(
        "0x000000000000000000000000000000000000000000000000000000000161c004", "bytes"
    )
    assert verifier.GI_FIRST_WITHDRAWAL_CURR() == HexString(
        "0x000000000000000000000000000000000000000000000000000000000161c004", "bytes"
    )
    assert verifier.GI_FIRST_VALIDATOR_PREV() == HexString(
        "0x0000000000000000000000000000000000000000000000000096000000000028", "bytes"
    )
    assert verifier.GI_FIRST_VALIDATOR_CURR() == HexString(
        "0x0000000000000000000000000000000000000000000000000096000000000028", "bytes"
    )
    assert verifier.GI_FIRST_HISTORICAL_SUMMARY_PREV() == HexString(
        "0x000000000000000000000000000000000000000000000000000000b600000018", "bytes"
    )
    assert verifier.GI_FIRST_HISTORICAL_SUMMARY_CURR() == HexString(
        "0x000000000000000000000000000000000000000000000000000000b600000018", "bytes"
    )
    assert verifier.GI_FIRST_BLOCK_ROOT_IN_SUMMARY_PREV() == HexString(
        "0x000000000000000000000000000000000000000000000000000000000040000d", "bytes"
    )
    assert verifier.GI_FIRST_BLOCK_ROOT_IN_SUMMARY_CURR() == HexString(
        "0x000000000000000000000000000000000000000000000000000000000040000d", "bytes"
    )

    assert verifier.FIRST_SUPPORTED_SLOT() == 364032 * CHAIN_SLOTS_PER_EPOCH
    assert verifier.PIVOT_SLOT() == verifier.FIRST_SUPPORTED_SLOT()
    assert verifier.CAPELLA_SLOT() == 194048 * CHAIN_SLOTS_PER_EPOCH
