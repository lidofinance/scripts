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

def get_tx_params(deployer):
    tx_params = {"from": deployer}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()
        tx_params["max_fee"] = get_max_fee()
    return tx_params


def prepare_transfer_locator_ownership_to_template(admin, template):
    interface.OssifiableProxy(contracts.lido_locator).proxy__changeAdmin(template, get_tx_params(admin))
