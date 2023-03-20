"""
Tests for voting ???
"""
from scripts.upgrade_shapella_goerli import start_vote
from utils.shapella_upgrade import load_shapella_deploy_config
from utils.test.tx_tracing_helpers import *
from utils.config import contracts, ldo_vote_executors_for_tests, lido_dao_lido_locator_implementation
from brownie.network.transaction import TransactionReceipt
from brownie import interface
from brownie import ShapellaUpgradeTemplate
from pprint import pprint


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
    bypass_events_decoding,
    accounts,
    ldo_holder,
):
    config = load_shapella_deploy_config()
    debug_locator_addresses(contracts.lido_locator.address)

    lido_new_implementation = config["app:lido"]["implementation"]
    nor_new_implementation = config["app:node-operators-registry"]["implementation"]
    oracle_new_implementation = config["app:oracle"]["implementation"]
    # temporary_admin = config["temporaryAdmin"]

    lido_repo: interface.Repo = contracts.lido_app_repo
    lido_old_app = lido_repo.getLatest()

    # template = prepare_for_voting(accounts, temporary_admin)

    # START VOTE
    vote_id, _, template = start_vote({"from": ldo_holder}, True)
    # template = interface.ShapellaUpgradeContract(template_address)

    # DEBUG: Uncomment if want to make part of the upgrade as a separate tx
    # template.startUpgrade({'from': contracts.voting.address})

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=contracts.voting, skip_time=3 * 60 * 60 * 24
    )
    print(f"UPGRADE TX GAS USED: {tx.gas_used}")

    # DEBUG: Uncomment if want to make part of the upgrade as a separate tx
    # template.finishUpgrade({'from': contracts.voting.address})

    # Template checks
    assert template.isUpgradeFinished()

    # Lido app upgrade
    lido_new_app = lido_repo.getLatest()
    assert_app_update(lido_new_app, lido_old_app, lido_new_implementation)
    lido_proxy = interface.AppProxyUpgradeable(contracts.lido)
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
