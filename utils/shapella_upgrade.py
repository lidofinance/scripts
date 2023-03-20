from brownie import ShapellaUpgradeTemplate, interface
from utils.config import (
    contracts,
    network_name,
    lido_dao_lido_locator_implementation,
    ldo_vote_executors_for_tests,
)
import json
from pprint import pprint

# Private constant taken from Lido contract
INITIAL_TOKEN_HOLDER = "0x000000000000000000000000000000000000dead"


def load_shapella_deploy_config():
    config_files = {
        "local-fork": "scripts/deployed-mainnet-fork-shapella-upgrade.json",
        "goerli-fork": "scripts/deployed-goerlishapella-upgrade.json",
    }
    with open(config_files[network_name()]) as fp:
        return json.load(fp)


def topup_initial_token_holder(lido, funder):
    lido.transfer(INITIAL_TOKEN_HOLDER, 2, {"from": funder})


def deploy_template_implementation(deployer):
    template_implementation = ShapellaUpgradeTemplate.deploy({"from": deployer})
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


def prepare_for_voting(temporary_admin):
    print("=== Do the on-chain preparations before starting the vote ===")
    # TODO: topup the holder on the live network and remove this
    steth_holder = ldo_vote_executors_for_tests[0]
    topup_initial_token_holder(contracts.lido, steth_holder)

    # Need this, otherwise Lido.finalizeUpgradeV2 reverts
    assert contracts.lido.balanceOf(INITIAL_TOKEN_HOLDER) > 0

    template = deploy_template_implementation(temporary_admin)
    pprint(get_template_configuration(template))
    interface.OssifiableProxy(contracts.lido_locator).proxy__upgradeTo(
        lido_dao_lido_locator_implementation, {"from": temporary_admin}
    )
    pass_ownership_to_template(temporary_admin, template)
    return template
