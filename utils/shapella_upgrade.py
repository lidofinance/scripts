from brownie import ShapellaUpgradeTemplate, interface
from utils.config import (
    contracts,
    lido_dao_lido_locator_implementation,
    ldo_vote_executors_for_tests,
    shapella_upgrade_template,
    prompt_bool,
)
from pprint import pprint

# Private constant taken from Lido contract
INITIAL_TOKEN_HOLDER = "0x000000000000000000000000000000000000dead"


def topup_initial_token_holder(lido, funder):
    lido.transfer(INITIAL_TOKEN_HOLDER, 2, {"from": funder})


def deploy_shapella_upgrade_template(deployer):
    template = ShapellaUpgradeTemplate.deploy({"from": deployer})
    return template


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
        "_validatorsExitBusOracleImplementation": template._withdrawalVaultImplementation(),
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


def transfer_ownership_to_template(owner, template):
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

    transfer_proxy_admin_to_template(contracts.accounting_oracle)
    transfer_proxy_admin_to_template(contracts.lido_locator)
    transfer_proxy_admin_to_template(contracts.staking_router)
    transfer_proxy_admin_to_template(contracts.validators_exit_bus_oracle)
    transfer_proxy_admin_to_template(contracts.withdrawal_queue)


def prepare_for_shapella_upgrade_voting(temporary_admin, silent=False):
    if shapella_upgrade_template != "":
        template = ShapellaUpgradeTemplate.at(shapella_upgrade_template)
        print(f"=== Using upgrade template from config {template.address} ===")
    else:
        template = deploy_shapella_upgrade_template(temporary_admin)
        print(f"=== Deployed upgrade template {template.address} ===")

    # Need this, otherwise Lido.finalizeUpgradeV2 reverts
    print("=== Top up 0xdead with a bit of steth (aka The Stone) ===")
    topup_initial_token_holder(contracts.lido, temporary_admin)
    assert contracts.lido.balanceOf(INITIAL_TOKEN_HOLDER) > 0

    assert interface.OssifiableProxy(contracts.lido_locator).proxy__getAdmin() == temporary_admin
    interface.OssifiableProxy(contracts.lido_locator).proxy__upgradeTo(
        lido_dao_lido_locator_implementation, {"from": temporary_admin}
    )
    print(f"=== Upgrade lido locator implementation to {lido_dao_lido_locator_implementation} ===")

    if not silent:
        print(f"!!! Going to transfer ownership to contract {template.address}. This is IRREVERSIBLE!")
        print("Does it look good? [yes/no]")
        resume = prompt_bool()
        while resume is None:
            resume = prompt_bool()
        if not resume:
            print("Trying to continue without transferring ownership to the upgrade template.")
            return None

    transfer_ownership_to_template(temporary_admin, template.address)
    return template
