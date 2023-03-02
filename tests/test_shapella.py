"""
Tests for voting ???
"""
from scripts.vote_shapella import start_vote, load_shapella_deploy_config
from utils.test.tx_tracing_helpers import *
from utils.config import contracts, lido_dao_steth_address, ldo_vote_executors_for_tests, lido_dao_voting_address
from brownie.network.transaction import TransactionReceipt
from brownie import interface
from brownie import ShapellaUpgradeTemplate
from pprint import pprint


# Private constant taken from Lido contract
INITIAL_TOKEN_HOLDER = "0xdead000000000000000000000000000000000000"


def topup_initial_token_holder(lido, funder):
    lido.transfer(INITIAL_TOKEN_HOLDER, 2, {"from": funder})


def deploy_template_implementation(deployer):
    template_config = load_shapella_deploy_config()

    withdrawal_credentials = "0x0123456789"
    gate_seal = lido_dao_voting_address
    template_args = [
        template_config["lidoLocator"]["address"],
        template_config["eip712StETH"]["address"],
        lido_dao_voting_address,
        template_config["app:node-operators-registry"]["proxyAddress"],
        template_config["hashConsensusForAccounting"]["address"],
        template_config["hashConsensusForValidatorsExitBus"]["address"],
        gate_seal,
        withdrawal_credentials,
        template_config["app:node-operators-registry"]["parameters"]["stuckPenaltyDelay"],
    ]
    config_implementations = [
        template_config["withdrawalQueueERC721"]["implementation"],
        template_config["stakingRouter"]["implementation"],
        template_config["accountingOracle"]["implementation"],
        template_config["validatorsExitBusOracle"]["implementation"],
    ]

    template_implementation = ShapellaUpgradeTemplate.deploy(template_args, config_implementations, {"from": deployer})
    return template_implementation


def bind_template_implementation(proxy, implementation):
    template = interface.OssifiableProxy(proxy)
    template.proxy__upgradeTo(implementation, {"from": lido_dao_voting_address})


def get_template_configuration(template_address):
    template = ShapellaUpgradeTemplate.at(template_address)
    config = {
        "_accountingOracleConsensusVersion": template._accountingOracleConsensusVersion(),
        "_validatorsExitBusOracleConsensusVersion": template._validatorsExitBusOracleConsensusVersion(),
        "_nodeOperatorsRegistryStakingModuleType": template._nodeOperatorsRegistryStakingModuleType(),
        "_locator": template._locator(),
        "_eip712StETH": template._eip712StETH(),
        "_voting": template._voting(),
        "_nodeOperatorsRegistry": template._nodeOperatorsRegistry(),
        "_hashConsensusForAccountingOracle": template._hashConsensusForAccountingOracle(),
        "_hashConsensusForValidatorsExitBusOracle": template._hashConsensusForValidatorsExitBusOracle(),
        "_gateSeal": template._gateSeal(),
        "_withdrawalCredentials": template._withdrawalCredentials(),
        "_nodeOperatorsRegistryStuckPenaltyDelay": template._nodeOperatorsRegistryStuckPenaltyDelay(),
        "_hardforkTimestamp": template._hardforkTimestamp(),
        "_withdrawalQueueImplementation": template._withdrawalQueueImplementation(),
        "_stakingRouterImplementation": template._stakingRouterImplementation(),
        "_accountingOracleImplementation": template._accountingOracleImplementation(),
        "_validatorsExitBusOracleImplementation": template._validatorsExitBusOracleImplementation(),
    }
    return config


def debug_locator_addresses(locator_address):
    locator = interface.LidoLocator(locator_address)
    locator_config = {
        "accountingOracle": locator.accountingOracle(),
        "depositSecurityModule": locator.depositSecurityModule(),
        "elRewardsVault": locator.elRewardsVault(),
        "legacyOracle": locator.legacyOracle(),
        "lido": locator.lido(),
        "oracleReportSanityChecker": locator.oracleReportSanityChecker(),
        "postTokenRebaseReceiver": locator.postTokenRebaseReceiver(),
        "burner": locator.burner(),
        "stakingRouter": locator.stakingRouter(),
        "treasury": locator.treasury(),
        "validatorsExitBusOracle": locator.validatorsExitBusOracle(),
        "withdrawalQueue": locator.withdrawalQueue(),
        "withdrawalVault": locator.withdrawalVault(),
        "oracleDaemonConfig": locator.oracleDaemonConfig(),
    }
    pprint(locator_config)


def test_vote(
    helpers,
    accounts,
    ldo_holder,
    dao_voting,
    vote_id_from_env,
    bypass_events_decoding,
    ldo_token,
    dao_agent,
    lido,
):
    config = load_shapella_deploy_config()
    debug_locator_addresses(config["lidoLocator"]["address"])

    lido_new_implementation = config["app:lido"]["implementation"]
    nor_new_implementation = config["app:node-operators-registry"]["implementation"]
    oracle_new_implementation = config["app:oracle"]["implementation"]
    template_address = config["shapellaUpgradeTemplate"]["address"]

    lido_repo: interface.Repo = contracts.lido_app_repo
    lido_old_app = lido_repo.getLatest()

    # TODO: remove this
    steth_holder = ldo_vote_executors_for_tests[0]
    topup_initial_token_holder(lido, steth_holder)

    # Need this, otherwise Lido.finalizeUpgradeV2 reverts
    assert lido.balanceOf(INITIAL_TOKEN_HOLDER) > 0

    template_implementation = deploy_template_implementation(accounts[0])

    # START VOTE
    vote_id, _ = start_vote({"from": ldo_holder}, True, template_implementation)

    print("template proxy address", template_address)
    template = ShapellaUpgradeTemplate.at(template_address)

    # DEBUG: Uncomment if want to upgrade as a separate tx
    # bind_template_implementation(template_address, template_implementation)

    pprint(get_template_configuration(template_implementation))

    # DEBUG: Uncomment if want to upgrade as a separate tx
    # template.startUpgrade({'from': lido_dao_voting_address})

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )
    print(f"GAS USED: {tx.gas_used}")

    # DEBUG: Uncomment if want to upgrade as a separate tx
    # template.finishUpgrade({'from': lido_dao_voting_address})

    # Template checks
    assert template.isUpgradeFinished()

    # Lido app upgrade
    lido_new_app = lido_repo.getLatest()
    assert_app_update(lido_new_app, lido_old_app, lido_new_implementation)
    lido_proxy = interface.AppProxyUpgradeable(lido_dao_steth_address)
    assert lido_proxy.implementation() == lido_new_implementation, "Proxy should be updated"

    if bypass_events_decoding:
        return

    display_voting_events(tx)
    evs = group_voting_events(tx)


def assert_app_update(new_app, old_app, contract_address):
    assert old_app[1] != new_app[1], "Address should change"
    assert new_app[1] == contract_address, "New address should match"
    assert new_app[0][0] == old_app[0][0] + 1, "Major version should increment"

    # TODO: uncomment
    # assert old_app[2] == new_app[2], "Content uri remains"
