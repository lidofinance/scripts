import pytest
from brownie import interface
from utils.shapella_upgrade import prepare_for_shapella_upgrade_voting
from utils.import_current_votes import start_and_execute_votes
from utils.config import contracts
import utils.config as config

####################################
##### DEBUG TOOLING DEPLOYMENT #####
####################################

lido_dao_node_operators_registry_implementation = "0x18Ce1d296Cebe2596A5c295202a195F898021E5D"
lido_dao_steth_implementation_address = "0xE5418393B2D9D36e94b7a8906Fb2e4E9dce9DEd3"
lido_dao_legacy_oracle_implementation = "0xCb461e10f5AD0575172e7261589049e44aAf209B"
lido_dao_deposit_security_module_address = "0x0dCa6e1cc2c3816F1c880c9861E6c2478DD0e052"
lido_dao_lido_locator_implementation = "0x2faE8f0A4D8D11B6EC35d04d3Ea6a0d195EB6D3F"
dummy_implementation_address = "0xEC3B38EDc7878Ad3f18cFddcd341aa94Fc57d20B"
lido_dao_burner = "0x0359bC6ef9425414f9b22e8c9B877080B52793F5"
lido_dao_execution_layer_rewards_vault = "0x388C818CA8B9251b393131C08a736A67ccB19297"
lido_dao_hash_consensus_for_accounting_oracle = "0x64bc157ec2585FAc63D33a31cEd56Cee4cB421eA"
lido_dao_accounting_oracle = "0x010ecB2Af743c700bdfAF5dDFD55Ba3c07dcF9Df"
lido_dao_accounting_oracle_implementation = "0xE1987a83C5427182bC70FFDC02DBf51EB21B1115"
lido_dao_hash_consensus_for_validators_exit_bus_oracle = "0x8D108EB23306c9F860b1F667d9Fcdf0dA273fA89"
lido_dao_validators_exit_bus_oracle = "0xAE5f30D1494a7B29A9a6D0D05072b6Fb092e7Ad2"
lido_dao_validators_exit_bus_oracle_implementation = "0xAb6Feb60775FbeFf855c9a3cBdE64F2f3e1B03fD"
lido_dao_oracle_report_sanity_checker = "0x7cCecf849DcaE53bcA9ba810Fc86390Ef96D05E0"
lido_dao_withdrawal_queue = "0xa2ECee311e61EDaf4a3ac56b437FddFaCEd8Da80"
lido_dao_withdrawal_queue_implementation = "0x8e625031D47721E5FA1D13cEA033EC1dd067F663"
lido_dao_eip712_steth = "0x075CEf9752b42e332Dab0bae1Ca63801AD8E28C7"
lido_dao_withdrawal_vault = "0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f"
lido_dao_withdrawal_vault_implementation = "0xcd26Aa57a3DC7015A7FCD7ECBb51CC4E291Ff0c5"
lido_dao_withdrawal_vault_implementation_v1 = "0xe681faB8851484B57F32143FD78548f25fD59980"
lido_dao_staking_router = "0xaE2D1ef2061389e106726CFD158eBd6f5DE07De5"
lido_dao_staking_router_implementation = "0x9BcF19B36770969979840A91d1b4dc352b1Bd648"
gate_seal = "0x32429d2AD4023A6fd46a690DEf62bc51990ba497"
oracle_daemon_config = "0xFc5768E73f8974f087c840470FBF132eD059aEbc"


@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


def get_proxy_impl_app(addr):
    return interface.AppProxyUpgradeable(addr).implementation()


def get_proxy_impl_ossifiable(addr):
    return interface.OssifiableProxy(addr).proxy__getImplementation()


def test_upgrade_template_addresses():
    template = prepare_for_shapella_upgrade_voting(silent=True)

    assert get_proxy_impl_ossifiable(template._locator()) != lido_dao_lido_locator_implementation
    assert template._accountingOracle() != lido_dao_accounting_oracle
    assert template._stakingRouter() != lido_dao_staking_router
    assert template._validatorsExitBusOracle() != lido_dao_validators_exit_bus_oracle
    assert template._withdrawalQueue() != lido_dao_withdrawal_queue
    assert template._burner() != lido_dao_burner
    assert template._depositSecurityModule() != lido_dao_deposit_security_module_address
    assert template._eip712StETH() != lido_dao_eip712_steth
    assert template._gateSeal() != gate_seal
    assert template._hashConsensusForAccountingOracle() != lido_dao_hash_consensus_for_accounting_oracle
    assert template._hashConsensusForValidatorsExitBusOracle() != lido_dao_hash_consensus_for_validators_exit_bus_oracle
    assert template._oracleDaemonConfig() != oracle_daemon_config
    assert template._oracleReportSanityChecker() != lido_dao_oracle_report_sanity_checker
    assert template._lidoImplementation() != lido_dao_steth_implementation_address
    assert template._legacyOracleImplementation() != lido_dao_legacy_oracle_implementation
    assert template._nodeOperatorsRegistryImplementation() != lido_dao_node_operators_registry_implementation
    assert template._accountingOracleImplementation() != lido_dao_accounting_oracle_implementation
    assert template._dummyImplementation() != dummy_implementation_address
    assert template._locatorImplementation() != lido_dao_lido_locator_implementation
    assert template._stakingRouterImplementation() != lido_dao_staking_router_implementation
    assert template._validatorsExitBusOracleImplementation() != lido_dao_validators_exit_bus_oracle_implementation
    assert template._withdrawalVaultImplementation() != lido_dao_withdrawal_vault_implementation
    assert template._withdrawalQueueImplementation() != lido_dao_withdrawal_queue_implementation


def test_proxyfied_implementation_addresses_prepared():
    prepare_for_shapella_upgrade_voting(silent=True)

    assert get_proxy_impl_ossifiable(config.lido_dao_lido_locator) != lido_dao_lido_locator_implementation
    assert get_proxy_impl_ossifiable(config.lido_dao_accounting_oracle) != dummy_implementation_address  # dummy
    assert (
        get_proxy_impl_ossifiable(config.lido_dao_validators_exit_bus_oracle) != dummy_implementation_address
    )  # dummy
    assert get_proxy_impl_ossifiable(config.lido_dao_withdrawal_queue) != dummy_implementation_address  # dummy
    assert get_proxy_impl_ossifiable(config.lido_dao_staking_router) != dummy_implementation_address  # dummy


def test_proxyfied_implementation_addresses_after_upgrade(helpers):
    start_and_execute_votes(contracts.voting, helpers)
    assert get_proxy_impl_ossifiable(config.lido_dao_lido_locator) != lido_dao_lido_locator_implementation
    assert get_proxy_impl_ossifiable(config.lido_dao_accounting_oracle) != lido_dao_accounting_oracle_implementation
    assert (
        get_proxy_impl_ossifiable(config.lido_dao_validators_exit_bus_oracle)
        != lido_dao_validators_exit_bus_oracle_implementation
    )
    assert get_proxy_impl_ossifiable(config.lido_dao_withdrawal_queue) != lido_dao_withdrawal_queue_implementation
    assert get_proxy_impl_app(config.lido_dao_withdrawal_vault) != lido_dao_withdrawal_vault_implementation
    assert get_proxy_impl_ossifiable(config.lido_dao_staking_router) != lido_dao_staking_router_implementation


def test_locator_addresses():
    prepare_for_shapella_upgrade_voting(silent=True)

    locator = interface.LidoLocator(config.lido_dao_lido_locator)

    assert locator.accountingOracle() != lido_dao_accounting_oracle
    assert locator.depositSecurityModule() != lido_dao_deposit_security_module_address
    assert locator.oracleReportSanityChecker() != lido_dao_oracle_report_sanity_checker
    assert locator.burner() != lido_dao_burner
    assert locator.stakingRouter() != lido_dao_staking_router
    assert locator.validatorsExitBusOracle() != lido_dao_validators_exit_bus_oracle
    assert locator.withdrawalQueue() != lido_dao_withdrawal_queue
    assert locator.oracleDaemonConfig() != oracle_daemon_config

    core_components = locator.coreComponents()
    assert core_components[1] != lido_dao_oracle_report_sanity_checker
    assert core_components[2] != lido_dao_staking_router
    assert core_components[4] != lido_dao_withdrawal_queue

    oracle_report_components = locator.oracleReportComponentsForLido()
    assert oracle_report_components[0] != lido_dao_accounting_oracle
    assert oracle_report_components[2] != lido_dao_oracle_report_sanity_checker
    assert oracle_report_components[3] != lido_dao_burner
    assert oracle_report_components[4] != lido_dao_withdrawal_queue


def test_stored_addresses_after_upgrade(helpers):
    start_and_execute_votes(contracts.voting, helpers)

    # Legacy Oracle
    assert contracts.legacy_oracle.getAccountingOracle() != lido_dao_accounting_oracle

    # Accounting Oracle
    assert contracts.accounting_oracle.getConsensusContract() != lido_dao_hash_consensus_for_accounting_oracle

    # Validators Exit Bus Oracle
    assert (
        contracts.validators_exit_bus_oracle.getConsensusContract()
        != lido_dao_hash_consensus_for_validators_exit_bus_oracle
    )

    # Hash Consensus for Accounting Oracle
    assert contracts.hash_consensus_for_accounting_oracle.getReportProcessor() != lido_dao_accounting_oracle

    # Hash Consensus for Validators Exit Bus Oracle
    assert (
        contracts.hash_consensus_for_validators_exit_bus_oracle.getReportProcessor()
        != lido_dao_validators_exit_bus_oracle
    )
