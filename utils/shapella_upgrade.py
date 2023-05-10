from brownie import ShapellaUpgradeTemplate, interface
from brownie.network.account import LocalAccount
from utils.config import (
    contracts,
    LIDO_LOCATOR_IMPL,
    LIDO_V2_UPGRADE_TEMPLATE,
    prompt_bool,
    get_priority_fee,
    get_max_fee,
    get_is_live,
    get_deployer_account,
    DEPLOYER_EOA_LOCATOR,
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
