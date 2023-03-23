from brownie import interface, web3, ZERO_ADDRESS
from utils.config import (
    contracts,
    lido_dao_withdrawal_vault_implementation,
    oracle_daemon_config_values,
    lido_dao_lido_locator_implementation,
)

from test_upgrade_shapella_goerli import lido_app_id

INITIAL_TOKEN_HOLDER = "0x000000000000000000000000000000000000dead"


def test_lido_state():
    # address in locator
    assert contracts.lido_locator.lido() == contracts.lido

    # AppProxyUpgradeable
    proxy = interface.AppProxyUpgradeable(contracts.lido)
    assert proxy.implementation() == "0xEE227CC91A769881b1e81350224AEeF7587eBe76"

    # Pausable
    assert contracts.lido.isStopped() == False

    # StETHPermit
    assert contracts.lido.getEIP712StETH() == contracts.eip712_steth

    # AppStorage
    assert contracts.lido.kernel() == contracts.kernel
    assert contracts.lido.appId() == lido_app_id

    # Versioned
    assert contracts.lido.getContractVersion() == 2

    # StETH
    # stone
    assert contracts.lido.balanceOf(INITIAL_TOKEN_HOLDER) > 0
    assert contracts.lido.sharesOf(INITIAL_TOKEN_HOLDER) > 0

    assert contracts.lido.getTotalShares() > contracts.lido.sharesOf(INITIAL_TOKEN_HOLDER)
    # unlimited allowance for burner to burn shares from withdrawal queue
    assert contracts.lido.allowance(contracts.withdrawal_queue, contracts.burner) == 2**256 - 1
    assert contracts.lido.allowance(contracts.node_operators_registry, contracts.burner) == 2**256 - 1

    # Lido
    # permissions is tested in test_permissions
    # but roles can have a wrong keccak

    assert contracts.lido.PAUSE_ROLE() == web3.keccak(text="PAUSE_ROLE").hex()
    assert contracts.lido.RESUME_ROLE() == web3.keccak(text="RESUME_ROLE").hex()
    assert contracts.lido.STAKING_PAUSE_ROLE() == web3.keccak(text="STAKING_PAUSE_ROLE").hex()
    assert contracts.lido.STAKING_CONTROL_ROLE() == web3.keccak(text="STAKING_CONTROL_ROLE").hex()
    assert (
        contracts.lido.UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE()
        == web3.keccak(text="UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE").hex()
    )

    # dependencies
    assert contracts.lido.getLidoLocator() == contracts.lido_locator

    # state
    stake_limit = contracts.lido.getStakeLimitFullInfo()
    assert stake_limit["isStakingPaused"] == False
    assert stake_limit["isStakingLimitSet"] == True
    assert stake_limit["maxStakeLimit"] == 150_000 * 1e18

    assert contracts.lido.getBufferedEther() > 0

    beacon_stat = contracts.lido.getBeaconStat()
    assert beacon_stat["depositedValidators"] > 0
    assert beacon_stat["beaconValidators"] > 0
    assert beacon_stat["beaconBalance"] > 0
    assert beacon_stat["depositedValidators"] >= beacon_stat["beaconValidators"]
    assert beacon_stat["beaconBalance"] >= 32 * 1e18 * beacon_stat[1]  # reasonable expectation before first withdrawals

    assert contracts.lido.getTotalELRewardsCollected() > 0


def test_withdrawal_vault_state():
    # address in locator
    assert contracts.lido_locator.withdrawalVault() == contracts.withdrawal_vault

    # WithdrawalVaultManager
    proxy = interface.WithdrawalVaultManager(contracts.withdrawal_vault)
    assert proxy.implementation() == lido_dao_withdrawal_vault_implementation
    assert proxy.proxy_getAdmin() == contracts.voting.address

    # Versioned
    assert contracts.withdrawal_vault.getContractVersion() == 1

    # WithdrawalsVault
    assert contracts.withdrawal_vault.LIDO() == contracts.lido
    assert contracts.withdrawal_vault.TREASURY() == contracts.agent
    assert contracts.withdrawal_vault.LIDO() == contracts.lido_locator.lido()
    assert contracts.withdrawal_vault.TREASURY() == contracts.lido_locator.treasury()


def test_withdrawal_queue_state():
    contract = contracts.withdrawal_queue
    # address in locator
    assert contract == contracts.lido_locator.withdrawalQueue()

    # Versioned
    assert contract.getContractVersion() == 1

    # OssifiableProxy
    proxy = interface.OssifiableProxy(contract)
    assert proxy.proxy__getImplementation() == "0xF7a378BB9E911550baA5e729f5Ab1592aDD905A5"
    assert proxy.proxy__getAdmin() == contracts.agent.address

    # WithdrawalQueueERC721
    assert contract.name() == "stETH Withdrawal NFT"
    assert contract.symbol() == "unstETH"
    assert contract.getBaseURI() == ""
    assert contract.getNFTDescriptorAddress() == ZERO_ADDRESS

    # WithdrawalQueue
    assert contract.WSTETH() == contracts.wsteth
    assert contract.STETH() == contracts.lido
    assert contract.bunkerModeSinceTimestamp() == contract.BUNKER_MODE_DISABLED_TIMESTAMP()

    # PausableUntil
    assert contract.isPaused() == False
    assert contract.getResumeSinceTimestamp() > 0

    # WithdrawalQueueBase

    assert contract.getLastRequestId() == 0
    assert contract.getLastFinalizedRequestId() == 0
    assert contract.getLockedEtherAmount() == 0
    assert contract.getLastCheckpointIndex() == 0
    assert contract.unfinalizedStETH() == 0


def test_oracle_daemon_config_state():
    contract = contracts.oracle_daemon_config
    # address in locator
    assert contract == contracts.lido_locator.oracleDaemonConfig()

    for key, value in oracle_daemon_config_values.items():
        assert int(str(contract.get(key)), 16) == value


def test_locator_state():
    # All immutable addresses are tested in respective functions

    # OssifiableProxy
    proxy = interface.OssifiableProxy(contracts.lido_locator)
    assert proxy.proxy__getImplementation() == lido_dao_lido_locator_implementation
    assert proxy.proxy__getAdmin() == contracts.agent.address


def test_veb_oracle_state():
    contract = contracts.validators_exit_bus_oracle
    # address in locator
    assert contract == contracts.lido_locator.validatorsExitBusOracle()

    # Versioned
    assert contract.getContractVersion() == 1

    # OssifiableProxy
    proxy = interface.OssifiableProxy(contract)
    assert proxy.proxy__getImplementation() == "0xBE378f865Ab69f51d8874aeB9508cbbC42B3FBDE"
    assert proxy.proxy__getAdmin() == contracts.agent.address

    # PausableUntil
    assert contract.isPaused() == False
    assert contract.getResumeSinceTimestamp() > 0

    # BaseOracle
    assert contract.SECONDS_PER_SLOT() == 12
    assert contract.GENESIS_TIME() == 1616508000
    assert contract.getConsensusVersion() == 1
    assert contract.getConsensusContract() == "0x8374B4aC337D7e367Ea1eF54bB29880C3f036A51"

    report = contract.getConsensusReport()
    assert report["hash"] == "0x0000000000000000000000000000000000000000000000000000000000000000"
    assert report["refSlot"] == 0
    assert report["processingDeadlineTime"] == 0
    assert report["processingStarted"] == False

    assert contract.getLastProcessingRefSlot() == 0

    # ValidatorExitBusOracle

    assert contract.getTotalRequestsProcessed() == 0
    state = contract.getProcessingState()
    assert state["currentFrameRefSlot"] > 5254400
    assert state["processingDeadlineTime"] == 0
    assert state["dataHash"] == "0x0000000000000000000000000000000000000000000000000000000000000000"
    assert state["dataSubmitted"] == False
    assert state["dataFormat"] == 0
    assert state["requestsCount"] == 0
    assert state["requestsSubmitted"] == 0
