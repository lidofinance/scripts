"""
Voting 31/01/2023.
Add ET setup for Gas Supply in stETH
Remove reWARDs and referral programs
!! Goerli only
"""

import time

from typing import Dict, Tuple, Optional, List

from brownie import interface
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.easy_track import add_evmscript_factory, create_permissions
from utils.permission_parameters import Param, SpecialArgumentID, ArgumentValue, Op

from utils.config import (
    get_deployer_account,
    contracts
)

from utils.easy_track import (
    add_evmscript_factory,
    create_permissions,
    remove_evmscript_factory
)


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    gas_supply_topup_factory = interface.TopUpAllowedRecipients("0x960CcA0BE6419e9684796Ce3ABE980E8a2d0cd80")
    gas_supply_add_recipient_factory = interface.AddAllowedRecipient("0xa2286d37Af8F8e84428151bF72922c5Fe5c1EeED")
    gas_supply_remove_recipient_factory = interface.RemoveAllowedRecipient("0x48D01979eD9e6CE70a6496B111F5728f9a547C96")
    gas_supply_registry = interface.AllowedRecipientRegistry("0xF08a5f00824D4554a1FBebaE726609418dc819fb")

    reWARDs_topup_factory = interface.TopUpAllowedRecipients("0x8180949ac41EF18e844ff8dafE604a195d86Aea9")
    reWARDs_add_recipient_factory = interface.AddAllowedRecipient("0x5560d40b00EA3a64E9431f97B3c79b04e0cdF6F2")
    reWARDs_remove_recipient_factory = interface.RemoveAllowedRecipient("0x31B68d81125E52fE1aDfe4076F8945D1014753b5")

    referral_LDO_topup_factory = interface.TopUpAllowedRecipients("0xB1E898faC74c377bEF16712Ba1CD4738606c19Ee")
    referral_LDO_add_recipient_factory = interface.AddAllowedRecipient("0xe54ca3e867C52a34d262E94606C7A9371AB820c9")
    referral_LDO_remove_recipient_factory = interface.RemoveAllowedRecipient("0x2A0c343087c6cFB721fFa20608A6eD0473C71275")

    referral_DAI_topup_factory = interface.TopUpAllowedRecipients("0x9534A77029D57E249c467E5A1E0854cc26Cd75A0")
    referral_DAI_add_recipient_factory = interface.AddAllowedRecipient("0x734458219BE229F6631F083ea574EBACa2f9bEaf")
    referral_DAI_remove_recipient_factory = interface.RemoveAllowedRecipient("0x5FEC0bcd7519C4fE41eca5Fe1dD94345fA100A67")

    reWARDs_LDO_topup_factory = interface.TopUpAllowedRecipients("0xD928dC9E4DaBeE939d3237A4f41983Ff5B6308dB")
    reWARDs_LDO_add_recipient_factory = interface.AddAllowedRecipient("0x3Ef70849FdBEe7b1F0A43179A3f788A8949b8abe")
    reWARDs_LDO_remove_recipient_factory = interface.RemoveAllowedRecipient("0x6c2e12D9C1d6e3dE146A7519eCbcb79c96Fe3146")

    call_script_items = [
        # 1.
        add_evmscript_factory(
            factory=gas_supply_topup_factory,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(gas_supply_registry, "updateSpentAmount")[2:],
        ),
        # 2.
        add_evmscript_factory(
            factory=gas_supply_add_recipient_factory,
            permissions=create_permissions(gas_supply_registry, "addRecipient"),
        ),
        # 3.
        add_evmscript_factory(
            factory=gas_supply_remove_recipient_factory,
            permissions=create_permissions(gas_supply_registry, "removeRecipient"),
        ),
        # 4-6
        remove_evmscript_factory(factory=reWARDs_topup_factory),
        remove_evmscript_factory(factory=reWARDs_add_recipient_factory),
        remove_evmscript_factory(factory=reWARDs_remove_recipient_factory),
        # 7-9
        remove_evmscript_factory(factory=referral_LDO_topup_factory),
        remove_evmscript_factory(factory=referral_LDO_add_recipient_factory),
        remove_evmscript_factory(factory=referral_LDO_remove_recipient_factory),
        # 10-12
        remove_evmscript_factory(factory=referral_DAI_topup_factory),
        remove_evmscript_factory(factory=referral_DAI_add_recipient_factory),
        remove_evmscript_factory(factory=referral_DAI_remove_recipient_factory),
        # 13-15
        remove_evmscript_factory(factory=reWARDs_LDO_topup_factory),
        remove_evmscript_factory(factory=reWARDs_LDO_add_recipient_factory),
        remove_evmscript_factory(factory=reWARDs_LDO_remove_recipient_factory),
    ]

    vote_desc_items = [
        "1) Add Gas Supply top up EVM script factory 0x960CcA0BE6419e9684796Ce3ABE980E8a2d0cd80",
        "2) Add Gas Supply add recipient EVM script factory 0xa2286d37Af8F8e84428151bF72922c5Fe5c1EeED",
        "3) Add Gas Supply remove recipient EVM script factory 0x48D01979eD9e6CE70a6496B111F5728f9a547C96",
        "4) Remove reWARDS top up EVM script factory",
        "5) Remove reWARDS add recipient EVM script factory",
        "6) Remove reWARDS remove recipient EVM script factory",
        "7) Remove referral LDO top up EVM script factory",
        "8) Remove referral LDO add recipient EVM script factory",
        "9) Remove referral LDO remove recipient EVM script factory",
        "10) Remove referral DAI top up EVM script factory",
        "11) Remove referral DAI add recipient EVM script factory",
        "12) Remove referral DAI remove recipient EVM script factory",
        "13) Remove reWARDS LDO top up EVM script factory",
        "14) Remove reWARDS LDO add recipient EVM script factory",
        "15) Remove reWARDS LDO remove recipient EVM script factory",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    vote_id, _ = start_vote({"from": get_deployer_account(), "max_fee": "300 gwei", "priority_fee": "2 gwei"})

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
