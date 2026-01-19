import pytest
from brownie import interface  # type: ignore

from utils.config import contracts, LIDO_LOCATOR, LIDO_LOCATOR_IMPL


@pytest.fixture(scope="module")
def contract() -> interface.LidoLocator:
    return interface.LidoLocator(LIDO_LOCATOR)


def test_proxy(contract):
    proxy = interface.OssifiableProxy(contract)
    assert proxy.proxy__getImplementation() == LIDO_LOCATOR_IMPL
    assert proxy.proxy__getAdmin() == contracts.agent.address


def test_addresses(contract):
    assert contract.accountingOracle() == contracts.accounting_oracle
    assert contract.depositSecurityModule() == contracts.deposit_security_module
    assert contract.elRewardsVault() == contracts.execution_layer_rewards_vault
    assert contract.lido() == contracts.lido
    assert contract.oracleReportSanityChecker() == contracts.oracle_report_sanity_checker
    assert contract.postTokenRebaseReceiver() == contracts.token_rate_notifier
    assert contract.burner() == contracts.burner
    assert contract.stakingRouter() == contracts.staking_router
    assert contract.treasury() == contracts.agent
    assert contract.validatorsExitBusOracle() == contracts.validators_exit_bus_oracle
    assert contract.withdrawalQueue() == contracts.withdrawal_queue
    assert contract.withdrawalVault() == contracts.withdrawal_vault
    assert contract.oracleDaemonConfig() == contracts.oracle_daemon_config

    assert contract.coreComponents() == (
        contracts.execution_layer_rewards_vault,
        contracts.oracle_report_sanity_checker,
        contracts.staking_router,
        contracts.agent,
        contracts.withdrawal_queue,
        contracts.withdrawal_vault,
    )

    assert contract.oracleReportComponents() == (
        contracts.accounting_oracle,
        contracts.oracle_report_sanity_checker,
        contracts.burner,
        contracts.withdrawal_queue,
        contracts.token_rate_notifier,
        contracts.staking_router,
        contracts.vault_hub,
    )
