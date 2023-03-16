"""
Tests for voting ???
"""
from scripts.vote_shapella import start_vote, load_shapella_deploy_config
from utils.test.tx_tracing_helpers import *
from utils.config import contracts, ldo_vote_executors_for_tests, lido_dao_lido_locator_implementation
from brownie.network.transaction import TransactionReceipt
from brownie import interface
from brownie import ShapellaUpgradeTemplate
from pprint import pprint


# Private constant taken from Lido contract
INITIAL_TOKEN_HOLDER = "0x000000000000000000000000000000000000dead"


def topup_initial_token_holder(lido, funder):
    lido.transfer(INITIAL_TOKEN_HOLDER, 2, {"from": funder})


def deploy_template_implementation(deployer):
    template_config = load_shapella_deploy_config()

    withdrawal_credentials = "0x0123456789"
    gate_seal = contracts.voting.address
    template_args = [
        contracts.lido_locator.address,
        contracts.eip712_steth.address,
        contracts.voting.address,
        contracts.node_operators_registry.address,
        contracts.hash_consensus_for_accounting_oracle.address,
        contracts.hash_consensus_for_validators_exit_bus_oracle,
        gate_seal,
        withdrawal_credentials,
        template_config["nodeOperatorsRegistry"]["parameters"]["stuckPenaltyDelay"],
    ]
    config_implementations = [
        template_config["withdrawalQueueERC721"]["implementation"],
        template_config["stakingRouter"]["implementation"],
        template_config["accountingOracle"]["implementation"],
        template_config["validatorsExitBusOracle"]["implementation"],
        template_config["dummyImplementation"]["address"],
        lido_dao_lido_locator_implementation,
    ]

    template_implementation = ShapellaUpgradeTemplate.deploy(template_args, config_implementations, {"from": deployer})
    return template_implementation


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


def pass_ownership_to_template(owner, template):
    admin_role = interface.AccessControlEnumerable(contracts.burner).DEFAULT_ADMIN_ROLE()

    def transfer_oz_admin_to_template(contract):
        interface.AccessControlEnumerable(contract).grantRole(admin_role, template, {"from": owner})
        interface.AccessControlEnumerable(contract).revokeRole(admin_role, owner, {"from": owner})

    def transfer_proxy_admin_to_template(contract):
        interface.OssifiableProxy(contract).proxy__changeAdmin(template, {"from": owner})

    contracts.deposit_security_module.setOwner(template, {"from": owner})

    transfer_oz_admin_to_template(contracts.burner)
    transfer_oz_admin_to_template(contracts.hash_consensus_for_accounting_oracle)
    transfer_oz_admin_to_template(contracts.hash_consensus_for_validators_exit_bus_oracle)

    transfer_proxy_admin_to_template(contracts.staking_router)
    transfer_proxy_admin_to_template(contracts.accounting_oracle)
    transfer_proxy_admin_to_template(contracts.validators_exit_bus_oracle)
    transfer_proxy_admin_to_template(contracts.withdrawal_queue)
    transfer_proxy_admin_to_template(contracts.lido_locator)


def prepare_for_voting(accounts, temporary_admin):
    # TODO: topup the holder on the live network and remove this
    steth_holder = ldo_vote_executors_for_tests[0]
    topup_initial_token_holder(contracts.lido, steth_holder)

    # Need this, otherwise Lido.finalizeUpgradeV2 reverts
    assert contracts.lido.balanceOf(INITIAL_TOKEN_HOLDER) > 0

    template = deploy_template_implementation(accounts[0])
    pprint(get_template_configuration(template))
    interface.OssifiableProxy(contracts.lido_locator).proxy__upgradeTo(
        lido_dao_lido_locator_implementation, {"from": temporary_admin}
    )
    pass_ownership_to_template(temporary_admin, template)
    return template


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
    temporary_admin = config["temporaryAdmin"]

    lido_repo: interface.Repo = contracts.lido_app_repo
    lido_old_app = lido_repo.getLatest()

    template = prepare_for_voting(accounts, temporary_admin)

    # START VOTE
    vote_id, _ = start_vote({"from": ldo_holder}, True, template)

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