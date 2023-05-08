import pytest
from brownie import interface
from utils.withdrawal_credentials import extract_address_from_eth1_wc
from utils.finance import ZERO_ADDRESS
from utils.shapella_upgrade import prepare_for_shapella_upgrade_voting
from utils.import_current_votes import start_and_execute_votes
from utils.config import (
    contracts,
    LIDO_ORACLE_DAEMON_CONFIG,
    GATE_SEAL,
    LIDO_WSTETH_TOKEN,
    DUMMY_IMPL,
    LIDO_ACL,
    LIDO_NODE_OPERATORS_REGISTRY_IMPL_V1,
    LIDO_LIDO_IMPL_V1,
    LIDO_LEGACY_ORACLE_IMPL_V1,
    LIDO_WITHDRAWAL_VAULT_IMPL_V1,
    LIDO_ACL_IMPL,
    LIDO_LOCATOR,
    LIDO_ACCOUNTING_ORACLE,
    LIDO_STAKING_ROUTER,
    LIDO_VALIDATORS_EXIT_BUS_ORACLE,
    LIDO_WITHDRAWAL_QUEUE,
    LIDO_BURNER,
    LIDO_DEPOSIT_SECURITY_MODULE,
    LIDO_EIP712_STETH,
    LIDO_HASH_CONSENSUS_FOR_AO,
    LIDO_HASH_CONSENSUS_FOR_VEBO,
    LIDO_ORACLE_REPORT_SANITY_CHECKER,
    LIDO_AGENT,
    LIDO_LIDO_REPO,
    LIDO_NODE_OPERATORS_REGISTRY_REPO,
    LIDO_LEGACY_ORACLE_REPO,
    LIDO_EXECUTION_LAYER_REWARDS_VAULT,
    LIDO_LIDO,
    LIDO_LEGACY_ORACLE,
    LIDO_NODE_OPERATORS_REGISTRY,
    LIDO_DEPOSIT_SECURITY_MODULE_V1,
    LIDO_VOTING,
    LIDO_WITHDRAWAL_VAULT,
    LIDO_LIDO_IMPL,
    LIDO_LEGACY_ORACLE_IMPL,
    LIDO_NODE_OPERATORS_REGISTRY_IMPL,
    LIDO_ACCOUNTING_ORACLE_IMPL,
    LIDO_LOCATOR_IMPL,
    LIDO_STAKING_ROUTER_IMPL,
    LIDO_VALIDATORS_EXIT_BUS_ORACLE_IMPL,
    LIDO_WITHDRAWAL_VAULT_IMPL,
    LIDO_WITHDRAWAL_QUEUE_IMPL,
)


@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


def get_proxy_impl_app(addr):
    return interface.AppProxyUpgradeable(addr).implementation()


def get_proxy_impl_ossifiable(addr):
    return interface.OssifiableProxy(addr).proxy__getImplementation()


def upgrade_withdrawal_vault():
    vault = interface.WithdrawalVaultManager(LIDO_WITHDRAWAL_VAULT)
    vault.proxy_upgradeTo(LIDO_WITHDRAWAL_VAULT_IMPL, b"", {"from": contracts.voting.address})


# ElRewardsVault did not changed
def test_el_rewards_vault_did_not_changed():
    template = prepare_for_shapella_upgrade_voting(silent=True)

    locator = interface.LidoLocator(LIDO_LOCATOR)
    core_components = locator.coreComponents()
    oracle_report_components = locator.oracleReportComponentsForLido()

    assert template._elRewardsVault() == LIDO_EXECUTION_LAYER_REWARDS_VAULT
    assert core_components[0] == LIDO_EXECUTION_LAYER_REWARDS_VAULT
    assert oracle_report_components[1] == LIDO_EXECUTION_LAYER_REWARDS_VAULT


# Withdrawals vault addr did not changed
def test_withdrawals_vault_addr_did_not_changed():
    template = prepare_for_shapella_upgrade_voting(silent=True)

    locator = interface.LidoLocator(LIDO_LOCATOR)
    core_components = locator.coreComponents()
    oracle_report_components = locator.oracleReportComponentsForLido()

    assert template._withdrawalVault() == LIDO_WITHDRAWAL_VAULT.lower()
    assert core_components[5] == LIDO_WITHDRAWAL_VAULT.lower()
    assert oracle_report_components[5] == LIDO_WITHDRAWAL_VAULT.lower()


# WithdrawalVault address is matching with WithdrawalCredentials
def test_withdrawals_vault_addr_matching_with_wc():
    withdrawal_credentials = contracts.lido.getWithdrawalCredentials()
    withdrawal_credentials_address = extract_address_from_eth1_wc(str(withdrawal_credentials))
    assert withdrawal_credentials_address == LIDO_WITHDRAWAL_VAULT.lower()

    prepare_for_shapella_upgrade_voting(silent=True)

    withdrawal_credentials = contracts.lido.getWithdrawalCredentials()
    withdrawal_credentials_address = extract_address_from_eth1_wc(str(withdrawal_credentials))

    assert withdrawal_credentials_address == LIDO_WITHDRAWAL_VAULT.lower()


def test_upgrade_template_addresses():
    template = prepare_for_shapella_upgrade_voting(silent=True)

    assert get_proxy_impl_ossifiable(template._locator()) == LIDO_LOCATOR_IMPL

    assert template._locator() == LIDO_LOCATOR
    assert template._accountingOracle() == LIDO_ACCOUNTING_ORACLE
    assert template._stakingRouter() == LIDO_STAKING_ROUTER
    assert template._validatorsExitBusOracle() == LIDO_VALIDATORS_EXIT_BUS_ORACLE
    assert template._withdrawalQueue() == LIDO_WITHDRAWAL_QUEUE
    assert template._burner() == LIDO_BURNER
    assert template._depositSecurityModule() == LIDO_DEPOSIT_SECURITY_MODULE
    assert template._eip712StETH() == LIDO_EIP712_STETH
    assert template._gateSeal() == GATE_SEAL
    assert template._hashConsensusForAccountingOracle() == LIDO_HASH_CONSENSUS_FOR_AO
    assert template._hashConsensusForValidatorsExitBusOracle() == LIDO_HASH_CONSENSUS_FOR_VEBO
    assert template._oracleDaemonConfig() == LIDO_ORACLE_DAEMON_CONFIG
    assert template._oracleReportSanityChecker() == LIDO_ORACLE_REPORT_SANITY_CHECKER
    assert template._agent() == LIDO_AGENT
    assert template._aragonAppLidoRepo() == LIDO_LIDO_REPO
    assert template._aragonAppNodeOperatorsRegistryRepo() == LIDO_NODE_OPERATORS_REGISTRY_REPO
    assert template._aragonAppLegacyOracleRepo() == LIDO_LEGACY_ORACLE_REPO
    assert template._elRewardsVault() == LIDO_EXECUTION_LAYER_REWARDS_VAULT
    assert template._lido() == LIDO_LIDO
    assert template._lidoOracle() == LIDO_LEGACY_ORACLE
    assert template._legacyOracle() == LIDO_LEGACY_ORACLE
    assert template._nodeOperatorsRegistry() == LIDO_NODE_OPERATORS_REGISTRY
    assert template._previousDepositSecurityModule() == LIDO_DEPOSIT_SECURITY_MODULE_V1
    assert template._voting() == LIDO_VOTING
    assert template._withdrawalVault() == LIDO_WITHDRAWAL_VAULT
    assert template._lidoImplementation() == LIDO_LIDO_IMPL
    assert template._legacyOracleImplementation() == LIDO_LEGACY_ORACLE_IMPL
    assert template._nodeOperatorsRegistryImplementation() == LIDO_NODE_OPERATORS_REGISTRY_IMPL
    assert template._accountingOracleImplementation() == LIDO_ACCOUNTING_ORACLE_IMPL
    assert template._dummyImplementation() == DUMMY_IMPL
    assert template._locatorImplementation() == LIDO_LOCATOR_IMPL
    assert template._stakingRouterImplementation() == LIDO_STAKING_ROUTER_IMPL
    assert template._validatorsExitBusOracleImplementation() == LIDO_VALIDATORS_EXIT_BUS_ORACLE_IMPL
    assert template._withdrawalVaultImplementation() == LIDO_WITHDRAWAL_VAULT_IMPL
    assert template._withdrawalQueueImplementation() == LIDO_WITHDRAWAL_QUEUE_IMPL


def test_proxyfied_implementation_addresses_prepared():
    prepare_for_shapella_upgrade_voting(silent=True)

    assert get_proxy_impl_app(LIDO_ACL) == LIDO_ACL_IMPL
    assert get_proxy_impl_app(LIDO_NODE_OPERATORS_REGISTRY) == LIDO_NODE_OPERATORS_REGISTRY_IMPL_V1
    assert get_proxy_impl_app(LIDO_LIDO) == LIDO_LIDO_IMPL_V1
    assert get_proxy_impl_app(LIDO_LEGACY_ORACLE) == LIDO_LEGACY_ORACLE_IMPL_V1
    assert get_proxy_impl_ossifiable(LIDO_LOCATOR) == LIDO_LOCATOR_IMPL
    assert get_proxy_impl_ossifiable(LIDO_ACCOUNTING_ORACLE) == DUMMY_IMPL  # dummy
    assert get_proxy_impl_ossifiable(LIDO_VALIDATORS_EXIT_BUS_ORACLE) == DUMMY_IMPL  # dummy
    assert get_proxy_impl_ossifiable(LIDO_WITHDRAWAL_QUEUE) == DUMMY_IMPL  # dummy
    assert get_proxy_impl_app(LIDO_WITHDRAWAL_VAULT) == LIDO_WITHDRAWAL_VAULT_IMPL_V1
    assert get_proxy_impl_ossifiable(LIDO_STAKING_ROUTER) == DUMMY_IMPL  # dummy


def test_proxyfied_implementation_addresses_after_upgrade(helpers):
    start_and_execute_votes(contracts.voting, helpers)

    assert get_proxy_impl_app(LIDO_ACL) == LIDO_ACL_IMPL
    assert get_proxy_impl_app(LIDO_NODE_OPERATORS_REGISTRY) == LIDO_NODE_OPERATORS_REGISTRY_IMPL
    assert get_proxy_impl_app(LIDO_LIDO) == LIDO_LIDO_IMPL
    assert get_proxy_impl_app(LIDO_LEGACY_ORACLE) == LIDO_LEGACY_ORACLE_IMPL
    assert get_proxy_impl_ossifiable(LIDO_LOCATOR) == LIDO_LOCATOR_IMPL
    assert get_proxy_impl_ossifiable(LIDO_ACCOUNTING_ORACLE) == LIDO_ACCOUNTING_ORACLE_IMPL
    assert get_proxy_impl_ossifiable(LIDO_VALIDATORS_EXIT_BUS_ORACLE) == LIDO_VALIDATORS_EXIT_BUS_ORACLE_IMPL
    assert get_proxy_impl_ossifiable(LIDO_WITHDRAWAL_QUEUE) == LIDO_WITHDRAWAL_QUEUE_IMPL
    assert get_proxy_impl_app(LIDO_WITHDRAWAL_VAULT) == LIDO_WITHDRAWAL_VAULT_IMPL
    assert get_proxy_impl_ossifiable(LIDO_STAKING_ROUTER) == LIDO_STAKING_ROUTER_IMPL


def test_locator_addresses():
    prepare_for_shapella_upgrade_voting(silent=True)

    locator = interface.LidoLocator(LIDO_LOCATOR)

    assert locator.accountingOracle() == LIDO_ACCOUNTING_ORACLE
    assert locator.depositSecurityModule() == LIDO_DEPOSIT_SECURITY_MODULE
    assert locator.elRewardsVault() == LIDO_EXECUTION_LAYER_REWARDS_VAULT
    assert locator.legacyOracle() == LIDO_LEGACY_ORACLE
    assert locator.lido() == LIDO_LIDO
    assert locator.oracleReportSanityChecker() == LIDO_ORACLE_REPORT_SANITY_CHECKER
    assert locator.postTokenRebaseReceiver() == LIDO_LEGACY_ORACLE
    assert locator.burner() == LIDO_BURNER
    assert locator.stakingRouter() == LIDO_STAKING_ROUTER
    assert locator.treasury() == LIDO_AGENT
    assert locator.validatorsExitBusOracle() == LIDO_VALIDATORS_EXIT_BUS_ORACLE
    assert locator.withdrawalQueue() == LIDO_WITHDRAWAL_QUEUE
    assert locator.withdrawalVault() == LIDO_WITHDRAWAL_VAULT
    assert locator.oracleDaemonConfig() == LIDO_ORACLE_DAEMON_CONFIG

    core_components = locator.coreComponents()
    assert core_components[0] == LIDO_EXECUTION_LAYER_REWARDS_VAULT
    assert core_components[1] == LIDO_ORACLE_REPORT_SANITY_CHECKER
    assert core_components[2] == LIDO_STAKING_ROUTER
    assert core_components[3] == LIDO_AGENT
    assert core_components[4] == LIDO_WITHDRAWAL_QUEUE
    assert core_components[5] == LIDO_WITHDRAWAL_VAULT

    oracle_report_components = locator.oracleReportComponentsForLido()
    assert oracle_report_components[0] == LIDO_ACCOUNTING_ORACLE
    assert oracle_report_components[1] == LIDO_EXECUTION_LAYER_REWARDS_VAULT
    assert oracle_report_components[2] == LIDO_ORACLE_REPORT_SANITY_CHECKER
    assert oracle_report_components[3] == LIDO_BURNER
    assert oracle_report_components[4] == LIDO_WITHDRAWAL_QUEUE
    assert oracle_report_components[5] == LIDO_WITHDRAWAL_VAULT
    assert oracle_report_components[6] == LIDO_LEGACY_ORACLE


def test_stored_addresses_after_prepared():
    prepare_for_shapella_upgrade_voting(silent=True)

    # EL Rewards Vault
    assert contracts.execution_layer_rewards_vault.LIDO() == LIDO_LIDO
    assert contracts.execution_layer_rewards_vault.TREASURY() == LIDO_AGENT

    # Burner
    assert contracts.burner.STETH() == LIDO_LIDO
    assert contracts.burner.TREASURY() == LIDO_AGENT

    # Oracle Report Sanity Checker
    assert contracts.oracle_report_sanity_checker.getLidoLocator() == LIDO_LOCATOR


def test_stored_addresses_after_upgrade(helpers):
    start_and_execute_votes(contracts.voting, helpers)

    # Lido
    assert contracts.lido.getLidoLocator() == LIDO_LOCATOR
    assert contracts.lido.getOracle() == LIDO_LEGACY_ORACLE

    # EL Rewards Vault
    assert contracts.execution_layer_rewards_vault.LIDO() == LIDO_LIDO
    assert contracts.execution_layer_rewards_vault.TREASURY() == LIDO_AGENT

    # Burner
    assert contracts.burner.STETH() == LIDO_LIDO
    assert contracts.burner.TREASURY() == LIDO_AGENT

    # Oracle Report Sanity Checker
    assert contracts.oracle_report_sanity_checker.getLidoLocator() == LIDO_LOCATOR

    # Node Operators Registry
    assert contracts.node_operators_registry.getLocator() == LIDO_LOCATOR

    # Legacy Oracle
    assert contracts.legacy_oracle.getLido() == LIDO_LIDO
    assert contracts.legacy_oracle.getAccountingOracle() == LIDO_ACCOUNTING_ORACLE

    # Staking Router
    assert contracts.staking_router.getLido() == LIDO_LIDO

    # Withdrawal Queue
    assert contracts.withdrawal_queue.STETH() == LIDO_LIDO
    assert contracts.withdrawal_queue.WSTETH() == LIDO_WSTETH_TOKEN
    assert contracts.withdrawal_queue.getNFTDescriptorAddress() == ZERO_ADDRESS  # TODO: double check this

    # Withdrawal vault
    assert contracts.withdrawal_vault.LIDO() == LIDO_LIDO
    assert contracts.withdrawal_vault.TREASURY() == LIDO_AGENT

    # Accounting Oracle
    assert contracts.accounting_oracle.LIDO() == LIDO_LIDO
    assert contracts.accounting_oracle.LOCATOR() == LIDO_LOCATOR
    assert contracts.accounting_oracle.LEGACY_ORACLE() == LIDO_LEGACY_ORACLE
    assert contracts.accounting_oracle.getConsensusContract() == LIDO_HASH_CONSENSUS_FOR_AO

    # Validators Exit Bus Oracle
    assert contracts.validators_exit_bus_oracle.getConsensusContract() == LIDO_HASH_CONSENSUS_FOR_VEBO

    # Hash Consensus for Accounting Oracle
    assert contracts.hash_consensus_for_accounting_oracle.getReportProcessor() == LIDO_ACCOUNTING_ORACLE

    # Hash Consensus for Validators Exit Bus Oracle
    assert (
        contracts.hash_consensus_for_validators_exit_bus_oracle.getReportProcessor() == LIDO_VALIDATORS_EXIT_BUS_ORACLE
    )
