from brownie import ShapellaUpgradeTemplate, interface
from utils.config import (
    contracts,
    lido_dao_lido_locator_implementation,
    shapella_upgrade_template_address,
    prompt_bool,
)

# Private constant taken from Lido contract
INITIAL_TOKEN_HOLDER = "0x000000000000000000000000000000000000dEaD"


def topup_initial_token_holder(lido, funder):
    lido.transfer(INITIAL_TOKEN_HOLDER, 2, {"from": funder})


def deploy_shapella_upgrade_template(deployer):
    template = ShapellaUpgradeTemplate.deploy({"from": deployer})
    return template


def transfer_ownership_to_template(owner, template):
    admin_role = interface.AccessControlEnumerable(contracts.burner).DEFAULT_ADMIN_ROLE()

    def transfer_oz_admin_to_template(contract):
        assert interface.AccessControlEnumerable(contract).getRoleMember(admin_role, 0) == owner
        interface.AccessControlEnumerable(contract).grantRole(admin_role, template, {"from": owner})
        interface.AccessControlEnumerable(contract).revokeRole(admin_role, owner, {"from": owner})

    def transfer_proxy_admin_to_template(contract):
        assert interface.OssifiableProxy(contract).proxy__getAdmin() == owner
        interface.OssifiableProxy(contract).proxy__changeAdmin(template, {"from": owner})

    assert contracts.deposit_security_module.getOwner() == owner
    contracts.deposit_security_module.setOwner(template, {"from": owner})

    transfer_oz_admin_to_template(contracts.burner)
    transfer_oz_admin_to_template(contracts.hash_consensus_for_accounting_oracle)
    transfer_oz_admin_to_template(contracts.hash_consensus_for_validators_exit_bus_oracle)

    transfer_proxy_admin_to_template(contracts.accounting_oracle)
    transfer_proxy_admin_to_template(contracts.lido_locator)
    transfer_proxy_admin_to_template(contracts.staking_router)
    transfer_proxy_admin_to_template(contracts.validators_exit_bus_oracle)
    transfer_proxy_admin_to_template(contracts.withdrawal_queue)


def ask_confirmation(silent, template_address):
    if not silent:
        print(f"!!! Going to transfer ownership to contract {template_address}. This is IRREVERSIBLE!")
        print("Does it look good? [yes/no]")
        resume = prompt_bool()
        while resume is None:
            resume = prompt_bool()
        if not resume:
            print("Trying to continue without transferring ownership to the upgrade template.")
            return None


def prepare_for_shapella_upgrade_voting(temporary_admin, silent=False):
    if shapella_upgrade_template_address != "":
        template = ShapellaUpgradeTemplate.at(shapella_upgrade_template_address)
        print(f"=== Using upgrade template from config {template.address} ===")
    else:
        template = deploy_shapella_upgrade_template(temporary_admin)
        print(f"=== Deployed upgrade template {template.address} ===")

    # To get sure the "stone" is in place
    assert contracts.lido.balanceOf(INITIAL_TOKEN_HOLDER) > 0

    ask_confirmation(silent, template.address)

    assert interface.OssifiableProxy(contracts.lido_locator).proxy__getAdmin() == temporary_admin
    interface.OssifiableProxy(contracts.lido_locator).proxy__upgradeTo(
        lido_dao_lido_locator_implementation, {"from": temporary_admin}
    )
    print(f"=== Upgrade lido locator implementation to {lido_dao_lido_locator_implementation} ===")

    transfer_ownership_to_template(temporary_admin, template.address)
    return template
