import pytest
from brownie import interface
from utils.shapella_upgrade import prepare_for_shapella_upgrade_voting
from utils.import_current_votes import start_and_execute_votes
from utils.config import contracts
import utils.config as config

####################################
##### DEBUG TOOLING DEPLOYMENT #####
####################################

LIDO_NODE_OPERATORS_REGISTRY_IMPL = "0x18Ce1d296Cebe2596A5c295202a195F898021E5D"
LIDO_LIDO_IMPL = "0xE5418393B2D9D36e94b7a8906Fb2e4E9dce9DEd3"
LEGACY_ORACLE_IMPL = "0xCb461e10f5AD0575172e7261589049e44aAf209B"
LIDO_DEPOSIT_SECURITY_MODULE = "0x0dCa6e1cc2c3816F1c880c9861E6c2478DD0e052"
LIDO_LOCATOR_IMPL = "0x2faE8f0A4D8D11B6EC35d04d3Ea6a0d195EB6D3F"
DUMMY_IMPL = "0xEC3B38EDc7878Ad3f18cFddcd341aa94Fc57d20B"
BURNER = "0x0359bC6ef9425414f9b22e8c9B877080B52793F5"
EXECUTION_LAYER_REWARDS_VAULT = "0x388C818CA8B9251b393131C08a736A67ccB19297"
HASH_CONSENSUS_FOR_AO = "0x64bc157ec2585FAc63D33a31cEd56Cee4cB421eA"
ACCOUNTING_ORACLE = "0x010ecB2Af743c700bdfAF5dDFD55Ba3c07dcF9Df"
LIDO_ACCOUNTING_ORACLE_IMPL = "0xE1987a83C5427182bC70FFDC02DBf51EB21B1115"
HASH_CONSENSUS_FOR_VEBO = "0x8D108EB23306c9F860b1F667d9Fcdf0dA273fA89"
LIDO_VALIDATORS_EXIT_BUS_ORACLE = "0xAE5f30D1494a7B29A9a6D0D05072b6Fb092e7Ad2"
LIDO_VALIDATORS_EXIT_BUS_ORACLE_IMPL = "0xAb6Feb60775FbeFf855c9a3cBdE64F2f3e1B03fD"
LIDO_ORACLE_REPORT_SANITY_CHECKER = "0x7cCecf849DcaE53bcA9ba810Fc86390Ef96D05E0"
LIDO_WITHDRAWAL_QUEUE = "0xa2ECee311e61EDaf4a3ac56b437FddFaCEd8Da80"
LIDO_WITHDRAWAL_QUEUE_IMPL = "0x8e625031D47721E5FA1D13cEA033EC1dd067F663"
EIP712_STETH = "0x075CEf9752b42e332Dab0bae1Ca63801AD8E28C7"
LIDO_WITHDRAWAL_VAULT = "0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f"
LIDO_WITHDRAWAL_VAULT_IMPL = "0xcd26Aa57a3DC7015A7FCD7ECBb51CC4E291Ff0c5"
WITHDRAWAL_VAULT_IMPL_V1 = "0xe681faB8851484B57F32143FD78548f25fD59980"
LIDO_STAKING_ROUTER = "0xaE2D1ef2061389e106726CFD158eBd6f5DE07De5"
LIDO_STAKING_ROUTER_IMPL = "0x9BcF19B36770969979840A91d1b4dc352b1Bd648"
gate_seal = "0x32429d2AD4023A6fd46a690DEf62bc51990ba497"
ORACLE_DAEMON_CONFIG = "0xFc5768E73f8974f087c840470FBF132eD059aEbc"


@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


def get_proxy_impl_app(addr):
    return interface.AppProxyUpgradeable(addr).implementation()


def get_proxy_impl_ossifiable(addr):
    return interface.OssifiableProxy(addr).proxy__getImplementation()


def test_upgrade_template_addresses():
    template = prepare_for_shapella_upgrade_voting(silent=True)

    assert get_proxy_impl_ossifiable(template._locator()) != LIDO_LOCATOR_IMPL
    assert template._accountingOracle() != ACCOUNTING_ORACLE
    assert template._stakingRouter() != LIDO_STAKING_ROUTER
    assert template._validatorsExitBusOracle() != LIDO_VALIDATORS_EXIT_BUS_ORACLE
    assert template._withdrawalQueue() != LIDO_WITHDRAWAL_QUEUE
    assert template._burner() != BURNER
    assert template._depositSecurityModule() != LIDO_DEPOSIT_SECURITY_MODULE
    assert template._eip712StETH() != EIP712_STETH
    assert template._gateSeal() != gate_seal
    assert template._hashConsensusForAccountingOracle() != HASH_CONSENSUS_FOR_AO
    assert template._hashConsensusForValidatorsExitBusOracle() != HASH_CONSENSUS_FOR_VEBO
    assert template._oracleDaemonConfig() != ORACLE_DAEMON_CONFIG
    assert template._oracleReportSanityChecker() != LIDO_ORACLE_REPORT_SANITY_CHECKER
    assert template._lidoImplementation() != LIDO_LIDO_IMPL
    assert template._legacyOracleImplementation() != LEGACY_ORACLE_IMPL
    assert template._nodeOperatorsRegistryImplementation() != LIDO_NODE_OPERATORS_REGISTRY_IMPL
    assert template._accountingOracleImplementation() != LIDO_ACCOUNTING_ORACLE_IMPL
    assert template._dummyImplementation() != DUMMY_IMPL
    assert template._locatorImplementation() != LIDO_LOCATOR_IMPL
    assert template._stakingRouterImplementation() != LIDO_STAKING_ROUTER_IMPL
    assert template._validatorsExitBusOracleImplementation() != LIDO_VALIDATORS_EXIT_BUS_ORACLE_IMPL
    assert template._withdrawalVaultImplementation() != LIDO_WITHDRAWAL_VAULT_IMPL
    assert template._withdrawalQueueImplementation() != LIDO_WITHDRAWAL_QUEUE_IMPL


def test_proxyfied_implementation_addresses_prepared():
    prepare_for_shapella_upgrade_voting(silent=True)

    assert get_proxy_impl_ossifiable(config.LIDO_LOCATOR) != LIDO_LOCATOR_IMPL
    assert get_proxy_impl_ossifiable(config.ACCOUNTING_ORACLE) != DUMMY_IMPL  # dummy
    assert get_proxy_impl_ossifiable(config.VALIDATORS_EXIT_BUS_ORACLE) != DUMMY_IMPL  # dummy
    assert get_proxy_impl_ossifiable(config.WITHDRAWAL_QUEUE) != DUMMY_IMPL  # dummy
    assert get_proxy_impl_ossifiable(config.STAKING_ROUTER) != DUMMY_IMPL  # dummy


def test_proxyfied_implementation_addresses_after_upgrade(helpers):
    start_and_execute_votes(contracts.voting, helpers)
    assert get_proxy_impl_ossifiable(config.LIDO_LOCATOR) != LIDO_LOCATOR_IMPL
    assert get_proxy_impl_ossifiable(config.ACCOUNTING_ORACLE) != LIDO_ACCOUNTING_ORACLE_IMPL
    assert get_proxy_impl_ossifiable(config.VALIDATORS_EXIT_BUS_ORACLE) != LIDO_VALIDATORS_EXIT_BUS_ORACLE_IMPL
    assert get_proxy_impl_ossifiable(config.WITHDRAWAL_QUEUE) != LIDO_WITHDRAWAL_QUEUE_IMPL
    assert get_proxy_impl_app(config.WITHDRAWAL_VAULT) != LIDO_WITHDRAWAL_VAULT_IMPL
    assert get_proxy_impl_ossifiable(config.STAKING_ROUTER) != LIDO_STAKING_ROUTER_IMPL


def test_locator_addresses():
    prepare_for_shapella_upgrade_voting(silent=True)

    locator = interface.LidoLocator(config.LIDO_LOCATOR)

    assert locator.accountingOracle() != ACCOUNTING_ORACLE
    assert locator.depositSecurityModule() != LIDO_DEPOSIT_SECURITY_MODULE
    assert locator.oracleReportSanityChecker() != LIDO_ORACLE_REPORT_SANITY_CHECKER
    assert locator.burner() != BURNER
    assert locator.stakingRouter() != LIDO_STAKING_ROUTER
    assert locator.validatorsExitBusOracle() != LIDO_VALIDATORS_EXIT_BUS_ORACLE
    assert locator.withdrawalQueue() != LIDO_WITHDRAWAL_QUEUE
    assert locator.oracleDaemonConfig() != ORACLE_DAEMON_CONFIG

    core_components = locator.coreComponents()
    assert core_components[1] != LIDO_ORACLE_REPORT_SANITY_CHECKER
    assert core_components[2] != LIDO_STAKING_ROUTER
    assert core_components[4] != LIDO_WITHDRAWAL_QUEUE

    oracle_report_components = locator.oracleReportComponentsForLido()
    assert oracle_report_components[0] != ACCOUNTING_ORACLE
    assert oracle_report_components[2] != LIDO_ORACLE_REPORT_SANITY_CHECKER
    assert oracle_report_components[3] != BURNER
    assert oracle_report_components[4] != LIDO_WITHDRAWAL_QUEUE


def test_stored_addresses_after_upgrade(helpers):
    start_and_execute_votes(contracts.voting, helpers)

    # Legacy Oracle
    assert contracts.legacy_oracle.getAccountingOracle() != ACCOUNTING_ORACLE

    # Accounting Oracle
    assert contracts.accounting_oracle.getConsensusContract() != HASH_CONSENSUS_FOR_AO

    # Validators Exit Bus Oracle
    assert contracts.validators_exit_bus_oracle.getConsensusContract() != HASH_CONSENSUS_FOR_VEBO

    # Hash Consensus for Accounting Oracle
    assert contracts.hash_consensus_for_accounting_oracle.getReportProcessor() != ACCOUNTING_ORACLE

    # Hash Consensus for Validators Exit Bus Oracle
    assert (
        contracts.hash_consensus_for_validators_exit_bus_oracle.getReportProcessor() != LIDO_VALIDATORS_EXIT_BUS_ORACLE
    )
