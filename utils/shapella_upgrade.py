from brownie import ShapellaUpgradeTemplate, GateSealMock, interface
from utils.config import (
    contracts,
    lido_dao_lido_locator_implementation,
    shapella_upgrade_template_address,
    prompt_bool,
    get_priority_fee,
    get_is_live,
)

# Private constant taken from Lido contract
INITIAL_TOKEN_HOLDER = "0x000000000000000000000000000000000000dEaD"

TIMESTAMP_FIRST_SECOND_OF_JULY_2023 = 1688155200


def ask_shapella_upgrade_confirmation(template_address, locator_implementation):
    print(f"!!! Going to do preliminary shapella upgrade actions. Namely:")
    print(f"  - upgrade LidoLocator proxy implementation to {locator_implementation}")
    print(f"  - transfer OZ admin and proxy ownership to the upgrade template {template_address}.")
    print(f"This is IRREVERSIBLE!")
    print("Does it look good? [yes/no]")
    resume = prompt_bool()
    while resume is None:
        resume = prompt_bool()
    if not resume:
        raise RuntimeError("User termination execution")


def get_tx_params(deployer):
    tx_params = {"from": deployer}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()
    return tx_params


def prepare_deploy_gate_seal_mock(deployer):
    gate_seal = GateSealMock.deploy(
        contracts.withdrawal_queue, contracts.validators_exit_bus_oracle, get_tx_params(deployer)
    )
    print(f"GateSealMock deployed at {gate_seal.address}")


def prepare_deploy_upgrade_template(deployer):
    template = ShapellaUpgradeTemplate.deploy(TIMESTAMP_FIRST_SECOND_OF_JULY_2023, get_tx_params(deployer))
    print(f"=== Deployed upgrade template {template.address} ===")
    return template


def prepare_upgrade_locator(admin):
    assert interface.OssifiableProxy(contracts.lido_locator).proxy__getAdmin() == admin
    interface.OssifiableProxy(contracts.lido_locator).proxy__upgradeTo(
        lido_dao_lido_locator_implementation, get_tx_params(admin)
    )
    print(f"=== Upgrade lido locator implementation to {lido_dao_lido_locator_implementation} ===")


def prepare_transfer_ownership_to_template(owner, template):
    admin_role = interface.AccessControlEnumerable(contracts.burner).DEFAULT_ADMIN_ROLE()
    tx_params = get_tx_params(owner)

    def transfer_oz_admin_to_template(contract):
        assert interface.AccessControlEnumerable(contract).getRoleMember(admin_role, 0) == owner
        interface.AccessControlEnumerable(contract).grantRole(admin_role, template, tx_params)
        interface.AccessControlEnumerable(contract).revokeRole(admin_role, owner, tx_params)

    def transfer_proxy_admin_to_template(contract):
        assert interface.OssifiableProxy(contract).proxy__getAdmin() == owner
        interface.OssifiableProxy(contract).proxy__changeAdmin(template, tx_params)

    assert contracts.deposit_security_module.getOwner() == owner
    contracts.deposit_security_module.setOwner(template, tx_params)

    transfer_oz_admin_to_template(contracts.burner)
    transfer_oz_admin_to_template(contracts.hash_consensus_for_accounting_oracle)
    transfer_oz_admin_to_template(contracts.hash_consensus_for_validators_exit_bus_oracle)

    transfer_proxy_admin_to_template(contracts.accounting_oracle)
    transfer_proxy_admin_to_template(contracts.lido_locator)
    transfer_proxy_admin_to_template(contracts.staking_router)
    transfer_proxy_admin_to_template(contracts.validators_exit_bus_oracle)
    transfer_proxy_admin_to_template(contracts.withdrawal_queue)


def prepare_for_shapella_upgrade_voting(temporary_admin, silent=False):
    assert silent or shapella_upgrade_template_address != ""
    if not silent:
        ask_shapella_upgrade_confirmation(shapella_upgrade_template_address, lido_dao_lido_locator_implementation)

    prepare_deploy_gate_seal_mock(temporary_admin)

    # Deploy the upgrade template if needed
    if shapella_upgrade_template_address == "":
        template = prepare_deploy_upgrade_template(temporary_admin)
    else:
        template = ShapellaUpgradeTemplate.at(shapella_upgrade_template_address)
        print(f"=== Using upgrade template from config {template.address} ===")

    # To get sure the "stone" is in place
    assert contracts.lido.balanceOf(INITIAL_TOKEN_HOLDER) > 0

    prepare_upgrade_locator(temporary_admin)

    prepare_transfer_ownership_to_template(temporary_admin, template.address)

    return template
