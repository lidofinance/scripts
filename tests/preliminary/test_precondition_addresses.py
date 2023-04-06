import pytest
from brownie import interface
from utils.withdrawal_credentials import (
    extract_address_from_eth1_wc
)
from utils.shapella_upgrade import prepare_for_shapella_upgrade_voting
import utils.config as conf


@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


def upgrade_withdrawal_vault():
    vault = interface.WithdrawalVaultManager(conf.lido_dao_withdrawal_vault)
    vault.proxy_upgradeTo(conf.lido_dao_withdrawal_vault_implementation, b"", {"from": conf.contracts.voting.address})


# ElRewardsVault did not changed
def test_el_rewards_vault_did_not_changed():
    template = prepare_for_shapella_upgrade_voting(conf.deployer_eoa, silent=True)

    locator = interface.LidoLocator(conf.lido_dao_lido_locator)
    core_components = locator.coreComponents()
    oracle_report_components = locator.oracleReportComponentsForLido()

    assert template._elRewardsVault() == conf.lido_dao_execution_layer_rewards_vault
    assert core_components[0] == conf.lido_dao_execution_layer_rewards_vault
    assert oracle_report_components[1] == conf.lido_dao_execution_layer_rewards_vault


# Withdrawals vault addr did not changed
def test_withdrawals_vault_addr_did_not_changed():
    template = prepare_for_shapella_upgrade_voting(conf.deployer_eoa, silent=True)
    upgrade_withdrawal_vault()

    locator = interface.LidoLocator(conf.lido_dao_lido_locator)
    core_components = locator.coreComponents()
    oracle_report_components = locator.oracleReportComponentsForLido()

    assert template._withdrawalVault() == conf.lido_dao_withdrawal_vault.lower()
    assert core_components[5] == conf.lido_dao_withdrawal_vault.lower()
    assert oracle_report_components[5] == conf.lido_dao_withdrawal_vault.lower()


# WithdrawalVault address is matching with WithdrawalCredentials
def test_withdrawals_vault_addr_matching_with_wc():
    withdrawal_credentials = conf.contracts.lido.getWithdrawalCredentials()
    withdrawal_credentials_addresss = extract_address_from_eth1_wc(str(withdrawal_credentials))
    assert withdrawal_credentials_addresss == conf.lido_dao_withdrawal_vault.lower()

    prepare_for_shapella_upgrade_voting(conf.deployer_eoa, silent=True)
    upgrade_withdrawal_vault()

    withdrawal_credentials = conf.contracts.lido.getWithdrawalCredentials()
    withdrawal_credentials_addresss = extract_address_from_eth1_wc(str(withdrawal_credentials))

    assert withdrawal_credentials_addresss == conf.lido_dao_withdrawal_vault.lower()


def test_upgrade_template_addresses():
    template = prepare_for_shapella_upgrade_voting(conf.deployer_eoa, silent=True)
    upgrade_withdrawal_vault()

    assert template._locator() == conf.lido_dao_lido_locator
    assert template._accountingOracle() == conf.lido_dao_accounting_oracle
    assert template._stakingRouter() == conf.lido_dao_staking_router
    assert template._validatorsExitBusOracle() == conf.lido_dao_validators_exit_bus_oracle
    assert template._withdrawalQueue() == conf.lido_dao_withdrawal_queue
    assert template._burner() == conf.lido_dao_burner
    assert template._depositSecurityModule() == conf.lido_dao_deposit_security_module_address
    assert template._eip712StETH() == conf.lido_dao_eip712_steth
    assert template._gateSeal() == conf.gate_seal
    assert template._hashConsensusForAccountingOracle() == conf.lido_dao_hash_consensus_for_accounting_oracle
    assert template._hashConsensusForValidatorsExitBusOracle() == conf.lido_dao_hash_consensus_for_validators_exit_bus_oracle
    assert template._oracleDaemonConfig() == conf.oracle_daemon_config
    assert template._oracleReportSanityChecker() == conf.lido_dao_oracle_report_sanity_checker
    assert template._agent() == conf.lido_dao_agent_address
    assert template._aragonAppLidoRepo() == conf.lido_dao_lido_repo
    assert template._aragonAppNodeOperatorsRegistryRepo() == conf.lido_dao_node_operators_registry_repo
    assert template._aragonAppLegacyOracleRepo() == conf.lido_dao_legacy_oracle_repo
    assert template._elRewardsVault() == conf.lido_dao_execution_layer_rewards_vault
    assert template._lido() == conf.lido_dao_steth_address
    assert template._lidoOracle() == conf.lido_dao_legacy_oracle
    assert template._legacyOracle() == conf.lido_dao_legacy_oracle
    assert template._nodeOperatorsRegistry() == conf.lido_dao_node_operators_registry
    assert template._previousDepositSecurityModule() == conf.lido_dao_deposit_security_module_address_old
    assert template._voting() == conf.lido_dao_voting_address
    assert template._withdrawalVault() == conf.lido_dao_withdrawal_vault
    assert template._lidoImplementation() == conf.lido_dao_steth_implementation_address
    assert template._legacyOracleImplementation() == conf.lido_dao_legacy_oracle_implementation
    assert template._nodeOperatorsRegistryImplementation() == conf.lido_dao_node_operators_registry_implementation
    assert template._accountingOracleImplementation() == conf.lido_dao_accounting_oracle_implementation
    # assert template._dummyImplementation() == conf.
    assert template._locatorImplementation() == conf.lido_dao_lido_locator_implementation
    assert template._stakingRouterImplementation() == conf.lido_dao_staking_router_implementation
    assert template._validatorsExitBusOracleImplementation() == conf.lido_dao_validators_exit_bus_oracle_implementation
    assert template._withdrawalVaultImplementation() == conf.lido_dao_withdrawal_vault_implementation
    assert template._withdrawalQueueImplementation() == conf.lido_dao_withdrawal_queue_implementation

def test_locator_addresses():
    prepare_for_shapella_upgrade_voting(conf.deployer_eoa, silent=True)
    upgrade_withdrawal_vault()

    locator = interface.LidoLocator(conf.lido_dao_lido_locator)

    core_components = locator.coreComponents()
    assert core_components[0] == conf.lido_dao_execution_layer_rewards_vault
    assert core_components[1] == conf.lido_dao_oracle_report_sanity_checker
    assert core_components[2] == conf.lido_dao_staking_router
    assert core_components[3] == conf.lido_dao_agent_address
    assert core_components[4] == conf.lido_dao_withdrawal_queue
    assert core_components[5] == conf.lido_dao_withdrawal_vault

    oracle_report_components = locator.oracleReportComponentsForLido()
    assert oracle_report_components[0] == conf.lido_dao_accounting_oracle
    assert oracle_report_components[1] == conf.lido_dao_execution_layer_rewards_vault
    assert oracle_report_components[2] == conf.lido_dao_oracle_report_sanity_checker
    assert oracle_report_components[3] == conf.lido_dao_burner
    assert oracle_report_components[4] == conf.lido_dao_withdrawal_queue
    assert oracle_report_components[5] == conf.lido_dao_withdrawal_vault
    assert oracle_report_components[6] == conf.lido_dao_legacy_oracle


def test_lido_execution_layer_rewards_vault_addresses():
    prepare_for_shapella_upgrade_voting(conf.deployer_eoa, silent=True)
    contract = conf.contracts.execution_layer_rewards_vault
    assert contract.LIDO() == conf.lido_dao_steth_address
    assert contract.TREASURY() == conf.lido_dao_agent_address


def test_burner_addresses():
    prepare_for_shapella_upgrade_voting(conf.deployer_eoa, silent=True)
    contract = conf.contracts.burner
    assert contract.STETH() == conf.lido_dao_steth_address
    assert contract.TREASURY() == conf.lido_dao_agent_address


def test_oracle_report_sanity_checker_addresses():
    prepare_for_shapella_upgrade_voting(conf.deployer_eoa, silent=True)
    contract = conf.contracts.oracle_report_sanity_checker
    assert contract.getLidoLocator() == conf.lido_dao_lido_locator
