import pytest
from brownie import interface
from utils.withdrawal_credentials import extract_address_from_eth1_wc
from utils.finance import ZERO_ADDRESS
from utils.config import (
    contracts,
    ORACLE_DAEMON_CONFIG,
    GATE_SEAL,
    WSTETH_TOKEN,
    DUMMY_IMPL,
    ACL,
    NODE_OPERATORS_REGISTRY_IMPL_V1,
    LIDO_IMPL_V1,
    LEGACY_ORACLE_IMPL_V1,
    WITHDRAWAL_VAULT_IMPL_V1,
    ACL_IMPL,
    LIDO_LOCATOR,
    ACCOUNTING_ORACLE,
    STAKING_ROUTER,
    VALIDATORS_EXIT_BUS_ORACLE,
    WITHDRAWAL_QUEUE,
    BURNER,
    DEPOSIT_SECURITY_MODULE,
    EIP712_STETH,
    HASH_CONSENSUS_FOR_AO,
    HASH_CONSENSUS_FOR_VEBO,
    ORACLE_REPORT_SANITY_CHECKER,
    AGENT,
    LIDO_REPO,
    NODE_OPERATORS_REGISTRY_REPO,
    LEGACY_ORACLE_REPO,
    EXECUTION_LAYER_REWARDS_VAULT,
    LIDO,
    LEGACY_ORACLE,
    NODE_OPERATORS_REGISTRY,
    DEPOSIT_SECURITY_MODULE_V1,
    VOTING,
    WITHDRAWAL_VAULT,
    LIDO_IMPL,
    LEGACY_ORACLE_IMPL,
    NODE_OPERATORS_REGISTRY_IMPL,
    ACCOUNTING_ORACLE_IMPL,
    LIDO_LOCATOR_IMPL,
    STAKING_ROUTER_IMPL,
    VALIDATORS_EXIT_BUS_ORACLE_IMPL,
    WITHDRAWAL_VAULT_IMPL,
    WITHDRAWAL_QUEUE_IMPL,
)


@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


def get_proxy_impl_app(addr):
    return interface.AppProxyUpgradeable(addr).implementation()


def get_proxy_impl_ossifiable(addr):
    return interface.OssifiableProxy(addr).proxy__getImplementation()


def upgrade_withdrawal_vault():
    vault = interface.WithdrawalVaultManager(WITHDRAWAL_VAULT)
    vault.proxy_upgradeTo(WITHDRAWAL_VAULT_IMPL, b"", {"from": contracts.voting.address})


# ElRewardsVault did not changed
def test_el_rewards_vault_did_not_changed():
    template = contracts.shapella_upgrade_template

    locator = interface.LidoLocator(LIDO_LOCATOR)
    core_components = locator.coreComponents()
    oracle_report_components = locator.oracleReportComponentsForLido()

    assert template._elRewardsVault() == EXECUTION_LAYER_REWARDS_VAULT
    assert core_components[0] == EXECUTION_LAYER_REWARDS_VAULT
    assert oracle_report_components[1] == EXECUTION_LAYER_REWARDS_VAULT


# Withdrawals vault addr did not changed
def test_withdrawals_vault_addr_did_not_changed():
    template = contracts.shapella_upgrade_template

    locator = interface.LidoLocator(LIDO_LOCATOR)
    core_components = locator.coreComponents()
    oracle_report_components = locator.oracleReportComponentsForLido()

    assert template._withdrawalVault() == WITHDRAWAL_VAULT.lower()
    assert core_components[5] == WITHDRAWAL_VAULT.lower()
    assert oracle_report_components[5] == WITHDRAWAL_VAULT.lower()


# WithdrawalVault address is matching with WithdrawalCredentials
def test_withdrawals_vault_addr_matching_with_wc():
    withdrawal_credentials = contracts.lido.getWithdrawalCredentials()
    withdrawal_credentials_address = extract_address_from_eth1_wc(str(withdrawal_credentials))
    assert withdrawal_credentials_address == WITHDRAWAL_VAULT.lower()

    withdrawal_credentials = contracts.lido.getWithdrawalCredentials()
    withdrawal_credentials_address = extract_address_from_eth1_wc(str(withdrawal_credentials))

    assert withdrawal_credentials_address == WITHDRAWAL_VAULT.lower()


def test_upgrade_template_addresses():
    template = contracts.shapella_upgrade_template

    assert get_proxy_impl_ossifiable(template._locator()) == LIDO_LOCATOR_IMPL

    assert template._locator() == LIDO_LOCATOR
    assert template._accountingOracle() == ACCOUNTING_ORACLE
    assert template._stakingRouter() == STAKING_ROUTER
    assert template._validatorsExitBusOracle() == VALIDATORS_EXIT_BUS_ORACLE
    assert template._withdrawalQueue() == WITHDRAWAL_QUEUE
    assert template._burner() == BURNER
    assert template._depositSecurityModule() == DEPOSIT_SECURITY_MODULE
    assert template._eip712StETH() == EIP712_STETH
    assert template._gateSeal() == GATE_SEAL
    assert template._hashConsensusForAccountingOracle() == HASH_CONSENSUS_FOR_AO
    assert template._hashConsensusForValidatorsExitBusOracle() == HASH_CONSENSUS_FOR_VEBO
    assert template._oracleDaemonConfig() == ORACLE_DAEMON_CONFIG
    assert template._oracleReportSanityChecker() == ORACLE_REPORT_SANITY_CHECKER
    assert template._agent() == AGENT
    assert template._aragonAppLidoRepo() == LIDO_REPO
    assert template._aragonAppNodeOperatorsRegistryRepo() == NODE_OPERATORS_REGISTRY_REPO
    assert template._aragonAppLegacyOracleRepo() == LEGACY_ORACLE_REPO
    assert template._elRewardsVault() == EXECUTION_LAYER_REWARDS_VAULT
    assert template._lido() == LIDO
    assert template._lidoOracle() == LEGACY_ORACLE
    assert template._legacyOracle() == LEGACY_ORACLE
    assert template._nodeOperatorsRegistry() == NODE_OPERATORS_REGISTRY
    assert template._previousDepositSecurityModule() == DEPOSIT_SECURITY_MODULE_V1
    assert template._voting() == VOTING
    assert template._withdrawalVault() == WITHDRAWAL_VAULT
    assert template._lidoImplementation() == LIDO_IMPL
    assert template._legacyOracleImplementation() == LEGACY_ORACLE_IMPL
    assert template._nodeOperatorsRegistryImplementation() == NODE_OPERATORS_REGISTRY_IMPL
    assert template._accountingOracleImplementation() == ACCOUNTING_ORACLE_IMPL
    assert template._dummyImplementation() == DUMMY_IMPL
    assert template._locatorImplementation() == LIDO_LOCATOR_IMPL
    assert template._stakingRouterImplementation() == STAKING_ROUTER_IMPL
    assert template._validatorsExitBusOracleImplementation() == VALIDATORS_EXIT_BUS_ORACLE_IMPL
    assert template._withdrawalVaultImplementation() == WITHDRAWAL_VAULT_IMPL
    assert template._withdrawalQueueImplementation() == WITHDRAWAL_QUEUE_IMPL


def test_proxyfied_implementation_addresses_prepared():

    assert get_proxy_impl_app(ACL) == ACL_IMPL
    assert get_proxy_impl_app(NODE_OPERATORS_REGISTRY) == NODE_OPERATORS_REGISTRY_IMPL_V1
    assert get_proxy_impl_app(LIDO) == LIDO_IMPL_V1
    assert get_proxy_impl_app(LEGACY_ORACLE) == LEGACY_ORACLE_IMPL_V1
    assert get_proxy_impl_ossifiable(LIDO_LOCATOR) == LIDO_LOCATOR_IMPL
    assert get_proxy_impl_ossifiable(ACCOUNTING_ORACLE) == DUMMY_IMPL  # dummy
    assert get_proxy_impl_ossifiable(VALIDATORS_EXIT_BUS_ORACLE) == DUMMY_IMPL  # dummy
    assert get_proxy_impl_ossifiable(WITHDRAWAL_QUEUE) == DUMMY_IMPL  # dummy
    assert get_proxy_impl_app(WITHDRAWAL_VAULT) == WITHDRAWAL_VAULT_IMPL_V1
    assert get_proxy_impl_ossifiable(STAKING_ROUTER) == DUMMY_IMPL  # dummy


def test_locator_addresses():

    locator = interface.LidoLocator(LIDO_LOCATOR)

    assert locator.accountingOracle() == ACCOUNTING_ORACLE
    assert locator.depositSecurityModule() == DEPOSIT_SECURITY_MODULE
    assert locator.elRewardsVault() == EXECUTION_LAYER_REWARDS_VAULT
    assert locator.legacyOracle() == LEGACY_ORACLE
    assert locator.lido() == LIDO
    assert locator.oracleReportSanityChecker() == ORACLE_REPORT_SANITY_CHECKER
    assert locator.postTokenRebaseReceiver() == LEGACY_ORACLE
    assert locator.burner() == BURNER
    assert locator.stakingRouter() == STAKING_ROUTER
    assert locator.treasury() == AGENT
    assert locator.validatorsExitBusOracle() == VALIDATORS_EXIT_BUS_ORACLE
    assert locator.withdrawalQueue() == WITHDRAWAL_QUEUE
    assert locator.withdrawalVault() == WITHDRAWAL_VAULT
    assert locator.oracleDaemonConfig() == ORACLE_DAEMON_CONFIG

    core_components = locator.coreComponents()
    assert core_components[0] == EXECUTION_LAYER_REWARDS_VAULT
    assert core_components[1] == ORACLE_REPORT_SANITY_CHECKER
    assert core_components[2] == STAKING_ROUTER
    assert core_components[3] == AGENT
    assert core_components[4] == WITHDRAWAL_QUEUE
    assert core_components[5] == WITHDRAWAL_VAULT

    oracle_report_components = locator.oracleReportComponentsForLido()
    assert oracle_report_components[0] == ACCOUNTING_ORACLE
    assert oracle_report_components[1] == EXECUTION_LAYER_REWARDS_VAULT
    assert oracle_report_components[2] == ORACLE_REPORT_SANITY_CHECKER
    assert oracle_report_components[3] == BURNER
    assert oracle_report_components[4] == WITHDRAWAL_QUEUE
    assert oracle_report_components[5] == WITHDRAWAL_VAULT
    assert oracle_report_components[6] == LEGACY_ORACLE


def test_stored_addresses_after_prepared():

    # EL Rewards Vault
    assert contracts.execution_layer_rewards_vault.LIDO() == LIDO
    assert contracts.execution_layer_rewards_vault.TREASURY() == AGENT

    # Burner
    assert contracts.burner.STETH() == LIDO
    assert contracts.burner.TREASURY() == AGENT

    # Oracle Report Sanity Checker
    assert contracts.oracle_report_sanity_checker.getLidoLocator() == LIDO_LOCATOR
