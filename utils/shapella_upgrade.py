from brownie import ShapellaUpgradeTemplate, interface
from brownie.network.account import LocalAccount
from utils.config import (
    contracts,
    lido_dao_lido_locator_implementation,
    lido_dao_withdrawal_queue,
    lido_dao_validators_exit_bus_oracle,
    gate_seal_factory_address,
    lido_dao_template_address,
    gate_seal_address,
    prompt_bool,
    get_priority_fee,
    get_max_fee,
    get_is_live,
    get_deployer_account,
    deployer_eoa,
    deployer_eoa_locator,
)

# Private constant taken from Lido contract
INITIAL_TOKEN_HOLDER = "0x000000000000000000000000000000000000dEaD"

TIMESTAMP_FIRST_SECOND_OF_JULY_2023_UTC = 1688169600


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
        tx_params["max_fee"] = get_max_fee()
    return tx_params


def assert_locator_deployer_eoa_is_impersonated():
    assert not get_is_live(), "Must not run any preliminary steps on live network!"
    deployer_account = get_deployer_account()
    assert not isinstance(deployer_account, LocalAccount), "mainnet deployer oea must be impersonated in tests"
    assert get_deployer_account() != deployer_eoa_locator


def prepare_deploy_gate_seal(deployer):
    gate_seal_factory = interface.GateSealFactory(gate_seal_factory_address)
    committee = deployer
    seal_duration = 6 * 24 * 60 * 60  # 6 days
    sealables = [lido_dao_withdrawal_queue, lido_dao_validators_exit_bus_oracle]
    expiry_timestamp = 1713139200  # 2024-04-15 00:00GMT
    tx = gate_seal_factory.create_gate_seal(
        committee, seal_duration, sealables, expiry_timestamp, get_tx_params(deployer)
    )
    deployed_gate_seal_address = tx.events[0]["gate_seal"]
    assert deployed_gate_seal_address == gate_seal_address
    print(f"GateSeal deployed at {gate_seal_address}")


def prepare_deploy_upgrade_template(deployer):
    template = ShapellaUpgradeTemplate.deploy(get_tx_params(deployer))
    print(f"=== Deployed upgrade template {template.address} ===")
    return template


def prepare_upgrade_locator_impl(admin):
    assert_locator_deployer_eoa_is_impersonated()

    assert interface.OssifiableProxy(contracts.lido_locator).proxy__getAdmin() == admin
    interface.OssifiableProxy(contracts.lido_locator).proxy__upgradeTo(
        lido_dao_lido_locator_implementation, get_tx_params(admin)
    )
    print(f"=== Upgrade lido locator implementation to {lido_dao_lido_locator_implementation} ===")


def prepare_transfer_ownership_to_template_no_locator(owner, template):
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
    transfer_proxy_admin_to_template(contracts.staking_router)
    transfer_proxy_admin_to_template(contracts.validators_exit_bus_oracle)
    transfer_proxy_admin_to_template(contracts.withdrawal_queue)


def prepare_transfer_locator_ownership_to_template(admin, template):
    assert_locator_deployer_eoa_is_impersonated()
    interface.OssifiableProxy(contracts.lido_locator).proxy__changeAdmin(template, get_tx_params(admin))


def prepare_for_shapella_upgrade_voting(silent=False):
    if not silent:
        ask_shapella_upgrade_confirmation(lido_dao_template_address, lido_dao_lido_locator_implementation)

    # To get sure the "stone" is in place
    assert contracts.lido.balanceOf(INITIAL_TOKEN_HOLDER) > 0

    # Deploy the upgrade template if needed
    template = prepare_deploy_upgrade_template(deployer_eoa)

    prepare_deploy_gate_seal(deployer_eoa)

    prepare_transfer_ownership_to_template_no_locator(deployer_eoa, template.address)

    prepare_upgrade_locator_impl(deployer_eoa_locator)

    prepare_transfer_locator_ownership_to_template(deployer_eoa_locator, template.address)

    return template
