import pytest
from brownie import interface
from utils.withdrawal_credentials import extract_address_from_eth1_wc
from utils.finance import ZERO_ADDRESS
from utils.shapella_upgrade import prepare_for_shapella_upgrade_voting
from utils.import_current_votes import start_and_execute_votes
from utils.config import (
    contracts,
    oracle_daemon_config,
    gate_seal_address,
    wsteth_token_address,
    dummy_implementation_address,
    lido_dao_acl_address,
    lido_dao_acl_implementation_address,
    lido_dao_node_operators_registry_implementation_v1,
    lido_dao_steth_implementation_address_v1,
    lido_dao_legacy_oracle_implementation_v1,
    lido_dao_withdrawal_vault_implementation_v1,
    lido_dao_acl_implementation_address,
    lido_dao_lido_locator,
    lido_dao_accounting_oracle,
    lido_dao_staking_router,
    lido_dao_validators_exit_bus_oracle,
    lido_dao_withdrawal_queue,
    lido_dao_burner,
    lido_dao_deposit_security_module_address,
    lido_dao_eip712_steth,
    lido_dao_hash_consensus_for_accounting_oracle,
    lido_dao_hash_consensus_for_validators_exit_bus_oracle,
    lido_dao_oracle_report_sanity_checker,
    lido_dao_agent_address,
    lido_dao_lido_repo,
    lido_dao_node_operators_registry_repo,
    lido_dao_legacy_oracle_repo,
    lido_dao_execution_layer_rewards_vault,
    lido_dao_steth_address,
    lido_dao_legacy_oracle,
    lido_dao_legacy_oracle,
    lido_dao_node_operators_registry,
    lido_dao_deposit_security_module_address_v1,
    lido_dao_voting_address,
    lido_dao_withdrawal_vault,
    lido_dao_steth_implementation_address,
    lido_dao_legacy_oracle_implementation,
    lido_dao_node_operators_registry_implementation,
    lido_dao_accounting_oracle_implementation,
    lido_dao_lido_locator_implementation,
    lido_dao_staking_router_implementation,
    lido_dao_validators_exit_bus_oracle_implementation,
    lido_dao_withdrawal_vault_implementation,
    lido_dao_withdrawal_queue_implementation,
)


@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


def get_proxy_impl_app(addr):
    return interface.AppProxyUpgradeable(addr).implementation()


def get_proxy_impl_ossifiable(addr):
    return interface.OssifiableProxy(addr).proxy__getImplementation()


def upgrade_withdrawal_vault():
    vault = interface.WithdrawalVaultManager(lido_dao_withdrawal_vault)
    vault.proxy_upgradeTo(lido_dao_withdrawal_vault_implementation, b"", {"from": contracts.voting.address})


# ElRewardsVault did not changed
def test_el_rewards_vault_did_not_changed():
    template = prepare_for_shapella_upgrade_voting(silent=True)

    locator = interface.LidoLocator(lido_dao_lido_locator)
    core_components = locator.coreComponents()
    oracle_report_components = locator.oracleReportComponentsForLido()

    assert template._elRewardsVault() == lido_dao_execution_layer_rewards_vault
    assert core_components[0] == lido_dao_execution_layer_rewards_vault
    assert oracle_report_components[1] == lido_dao_execution_layer_rewards_vault


# Withdrawals vault addr did not changed
def test_withdrawals_vault_addr_did_not_changed():
    template = prepare_for_shapella_upgrade_voting(silent=True)

    locator = interface.LidoLocator(lido_dao_lido_locator)
    core_components = locator.coreComponents()
    oracle_report_components = locator.oracleReportComponentsForLido()

    assert template._withdrawalVault() == lido_dao_withdrawal_vault.lower()
    assert core_components[5] == lido_dao_withdrawal_vault.lower()
    assert oracle_report_components[5] == lido_dao_withdrawal_vault.lower()


# WithdrawalVault address is matching with WithdrawalCredentials
def test_withdrawals_vault_addr_matching_with_wc():
    withdrawal_credentials = contracts.lido.getWithdrawalCredentials()
    withdrawal_credentials_address = extract_address_from_eth1_wc(str(withdrawal_credentials))
    assert withdrawal_credentials_address == lido_dao_withdrawal_vault.lower()

    prepare_for_shapella_upgrade_voting(silent=True)

    withdrawal_credentials = contracts.lido.getWithdrawalCredentials()
    withdrawal_credentials_address = extract_address_from_eth1_wc(str(withdrawal_credentials))

    assert withdrawal_credentials_address == lido_dao_withdrawal_vault.lower()


def test_upgrade_template_addresses():
    template = prepare_for_shapella_upgrade_voting(silent=True)

    assert get_proxy_impl_ossifiable(template._locator()) == lido_dao_lido_locator_implementation

    assert template._locator() == lido_dao_lido_locator
    assert template._accountingOracle() == lido_dao_accounting_oracle
    assert template._stakingRouter() == lido_dao_staking_router
    assert template._validatorsExitBusOracle() == lido_dao_validators_exit_bus_oracle
    assert template._withdrawalQueue() == lido_dao_withdrawal_queue
    assert template._burner() == lido_dao_burner
    assert template._depositSecurityModule() == lido_dao_deposit_security_module_address
    assert template._eip712StETH() == lido_dao_eip712_steth
    assert template._gateSeal() == gate_seal_address
    assert template._hashConsensusForAccountingOracle() == lido_dao_hash_consensus_for_accounting_oracle
    assert template._hashConsensusForValidatorsExitBusOracle() == lido_dao_hash_consensus_for_validators_exit_bus_oracle
    assert template._oracleDaemonConfig() == oracle_daemon_config
    assert template._oracleReportSanityChecker() == lido_dao_oracle_report_sanity_checker
    assert template._agent() == lido_dao_agent_address
    assert template._aragonAppLidoRepo() == lido_dao_lido_repo
    assert template._aragonAppNodeOperatorsRegistryRepo() == lido_dao_node_operators_registry_repo
    assert template._aragonAppLegacyOracleRepo() == lido_dao_legacy_oracle_repo
    assert template._elRewardsVault() == lido_dao_execution_layer_rewards_vault
    assert template._lido() == lido_dao_steth_address
    assert template._lidoOracle() == lido_dao_legacy_oracle
    assert template._legacyOracle() == lido_dao_legacy_oracle
    assert template._nodeOperatorsRegistry() == lido_dao_node_operators_registry
    assert template._previousDepositSecurityModule() == lido_dao_deposit_security_module_address_v1
    assert template._voting() == lido_dao_voting_address
    assert template._withdrawalVault() == lido_dao_withdrawal_vault
    assert template._lidoImplementation() == lido_dao_steth_implementation_address
    assert template._legacyOracleImplementation() == lido_dao_legacy_oracle_implementation
    assert template._nodeOperatorsRegistryImplementation() == lido_dao_node_operators_registry_implementation
    assert template._accountingOracleImplementation() == lido_dao_accounting_oracle_implementation
    assert template._dummyImplementation() == dummy_implementation_address
    assert template._locatorImplementation() == lido_dao_lido_locator_implementation
    assert template._stakingRouterImplementation() == lido_dao_staking_router_implementation
    assert template._validatorsExitBusOracleImplementation() == lido_dao_validators_exit_bus_oracle_implementation
    assert template._withdrawalVaultImplementation() == lido_dao_withdrawal_vault_implementation
    assert template._withdrawalQueueImplementation() == lido_dao_withdrawal_queue_implementation


def test_proxyfied_implementation_addresses_prepared():
    prepare_for_shapella_upgrade_voting(silent=True)

    assert get_proxy_impl_app(lido_dao_acl_address) == lido_dao_acl_implementation_address
    assert get_proxy_impl_app(lido_dao_node_operators_registry) == lido_dao_node_operators_registry_implementation_v1
    assert get_proxy_impl_app(lido_dao_steth_address) == lido_dao_steth_implementation_address_v1
    assert get_proxy_impl_app(lido_dao_legacy_oracle) == lido_dao_legacy_oracle_implementation_v1
    assert get_proxy_impl_ossifiable(lido_dao_lido_locator) == lido_dao_lido_locator_implementation
    assert get_proxy_impl_ossifiable(lido_dao_accounting_oracle) == dummy_implementation_address  # dummy
    assert get_proxy_impl_ossifiable(lido_dao_validators_exit_bus_oracle) == dummy_implementation_address  # dummy
    assert get_proxy_impl_ossifiable(lido_dao_withdrawal_queue) == dummy_implementation_address  # dummy
    assert get_proxy_impl_app(lido_dao_withdrawal_vault) == lido_dao_withdrawal_vault_implementation_v1
    assert get_proxy_impl_ossifiable(lido_dao_staking_router) == dummy_implementation_address  # dummy


def test_proxyfied_implementation_addresses_after_upgrade(helpers):
    start_and_execute_votes(contracts.voting, helpers)

    assert get_proxy_impl_app(lido_dao_acl_address) == lido_dao_acl_implementation_address
    assert get_proxy_impl_app(lido_dao_node_operators_registry) == lido_dao_node_operators_registry_implementation
    assert get_proxy_impl_app(lido_dao_steth_address) == lido_dao_steth_implementation_address
    assert get_proxy_impl_app(lido_dao_legacy_oracle) == lido_dao_legacy_oracle_implementation
    assert get_proxy_impl_ossifiable(lido_dao_lido_locator) == lido_dao_lido_locator_implementation
    assert get_proxy_impl_ossifiable(lido_dao_accounting_oracle) == lido_dao_accounting_oracle_implementation
    assert (
        get_proxy_impl_ossifiable(lido_dao_validators_exit_bus_oracle)
        == lido_dao_validators_exit_bus_oracle_implementation
    )
    assert get_proxy_impl_ossifiable(lido_dao_withdrawal_queue) == lido_dao_withdrawal_queue_implementation
    assert get_proxy_impl_app(lido_dao_withdrawal_vault) == lido_dao_withdrawal_vault_implementation
    assert get_proxy_impl_ossifiable(lido_dao_staking_router) == lido_dao_staking_router_implementation


def test_locator_addresses():
    prepare_for_shapella_upgrade_voting(silent=True)

    locator = interface.LidoLocator(lido_dao_lido_locator)

    assert locator.accountingOracle() == lido_dao_accounting_oracle
    assert locator.depositSecurityModule() == lido_dao_deposit_security_module_address
    assert locator.elRewardsVault() == lido_dao_execution_layer_rewards_vault
    assert locator.legacyOracle() == lido_dao_legacy_oracle
    assert locator.lido() == lido_dao_steth_address
    assert locator.oracleReportSanityChecker() == lido_dao_oracle_report_sanity_checker
    assert locator.postTokenRebaseReceiver() == lido_dao_legacy_oracle
    assert locator.burner() == lido_dao_burner
    assert locator.stakingRouter() == lido_dao_staking_router
    assert locator.treasury() == lido_dao_agent_address
    assert locator.validatorsExitBusOracle() == lido_dao_validators_exit_bus_oracle
    assert locator.withdrawalQueue() == lido_dao_withdrawal_queue
    assert locator.withdrawalVault() == lido_dao_withdrawal_vault
    assert locator.oracleDaemonConfig() == oracle_daemon_config

    core_components = locator.coreComponents()
    assert core_components[0] == lido_dao_execution_layer_rewards_vault
    assert core_components[1] == lido_dao_oracle_report_sanity_checker
    assert core_components[2] == lido_dao_staking_router
    assert core_components[3] == lido_dao_agent_address
    assert core_components[4] == lido_dao_withdrawal_queue
    assert core_components[5] == lido_dao_withdrawal_vault

    oracle_report_components = locator.oracleReportComponentsForLido()
    assert oracle_report_components[0] == lido_dao_accounting_oracle
    assert oracle_report_components[1] == lido_dao_execution_layer_rewards_vault
    assert oracle_report_components[2] == lido_dao_oracle_report_sanity_checker
    assert oracle_report_components[3] == lido_dao_burner
    assert oracle_report_components[4] == lido_dao_withdrawal_queue
    assert oracle_report_components[5] == lido_dao_withdrawal_vault
    assert oracle_report_components[6] == lido_dao_legacy_oracle


def test_stored_addresses_after_prepared():
    prepare_for_shapella_upgrade_voting(silent=True)

    # EL Rewards Vault
    assert contracts.execution_layer_rewards_vault.LIDO() == lido_dao_steth_address
    assert contracts.execution_layer_rewards_vault.TREASURY() == lido_dao_agent_address

    # Burner
    assert contracts.burner.STETH() == lido_dao_steth_address
    assert contracts.burner.TREASURY() == lido_dao_agent_address

    # Oracle Report Sanity Checker
    assert contracts.oracle_report_sanity_checker.getLidoLocator() == lido_dao_lido_locator


def test_stored_addresses_after_upgrade(helpers):
    start_and_execute_votes(contracts.voting, helpers)

    # Lido
    assert contracts.lido.getLidoLocator() == lido_dao_lido_locator
    assert contracts.lido.getOracle() == lido_dao_legacy_oracle

    # EL Rewards Vault
    assert contracts.execution_layer_rewards_vault.LIDO() == lido_dao_steth_address
    assert contracts.execution_layer_rewards_vault.TREASURY() == lido_dao_agent_address

    # Burner
    assert contracts.burner.STETH() == lido_dao_steth_address
    assert contracts.burner.TREASURY() == lido_dao_agent_address

    # Oracle Report Sanity Checker
    assert contracts.oracle_report_sanity_checker.getLidoLocator() == lido_dao_lido_locator

    # Node Operators Registry
    assert contracts.node_operators_registry.getLocator() == lido_dao_lido_locator

    # Legacy Oracle
    assert contracts.legacy_oracle.getLido() == lido_dao_steth_address
    assert contracts.legacy_oracle.getAccountingOracle() == lido_dao_accounting_oracle

    # Staking Router
    assert contracts.staking_router.getLido() == lido_dao_steth_address

    # Withdrawal Queue
    assert contracts.withdrawal_queue.STETH() == lido_dao_steth_address
    assert contracts.withdrawal_queue.WSTETH() == wsteth_token_address
    assert contracts.withdrawal_queue.getNFTDescriptorAddress() == ZERO_ADDRESS  # TODO: double check this

    # Withdrawal vault
    assert contracts.withdrawal_vault.LIDO() == lido_dao_steth_address
    assert contracts.withdrawal_vault.TREASURY() == lido_dao_agent_address

    # Accounting Oracle
    assert contracts.accounting_oracle.LIDO() == lido_dao_steth_address
    assert contracts.accounting_oracle.LOCATOR() == lido_dao_lido_locator
    assert contracts.accounting_oracle.LEGACY_ORACLE() == lido_dao_legacy_oracle
    assert contracts.accounting_oracle.getConsensusContract() == lido_dao_hash_consensus_for_accounting_oracle

    # Validators Exit Bus Oracle
    assert (
        contracts.validators_exit_bus_oracle.getConsensusContract()
        == lido_dao_hash_consensus_for_validators_exit_bus_oracle
    )

    # Hash Consensus for Accounting Oracle
    assert contracts.hash_consensus_for_accounting_oracle.getReportProcessor() == lido_dao_accounting_oracle

    # Hash Consensus for Validators Exit Bus Oracle
    assert (
        contracts.hash_consensus_for_validators_exit_bus_oracle.getReportProcessor()
        == lido_dao_validators_exit_bus_oracle
    )
