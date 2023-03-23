from brownie import interface, web3
from utils.config import contracts, lido_dao_withdrawal_vault_implementation

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
    assert contracts.lido.allowance(contracts.withdrawal_queue, contracts.burner) == 2 ** 256 - 1

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
    assert stake_limit[0] == False  # isStakingPaused
    assert stake_limit[1] == True  # isStakingLimitSet
    assert stake_limit[3] == 150_000 * 1e18

    assert contracts.lido.getBufferedEther() > 0

    beacon_stat = contracts.lido.getBeaconStat()
    assert beacon_stat[0] > 0  # deposited validators
    assert beacon_stat[1] > 0  # cl validators
    assert beacon_stat[2] > 0  # cl balance
    assert beacon_stat[0] >= beacon_stat[1]
    assert beacon_stat[2] >= 32 * 1e18 * beacon_stat[1]  # reasonable expectation before first withdrawals

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
