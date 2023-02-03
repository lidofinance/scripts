"""
Voting 31/01/2023.
1. Add referral program top up EVM script factory 0x9534A77029D57E249c467E5A1E0854cc26Cd75A0
2. Add referral program add recipient EVM script factory 0x734458219BE229F6631F083ea574EBACa2f9bEaf
3. Add referral program remove recipient EVM script factory 0x5FEC0bcd7519C4fE41eca5Fe1dD94345fA100A67

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
    lido_dao_finance_address,
)


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    finance = interface.Finance(lido_dao_finance_address)

    rewards_topup_factory = interface.TopUpAllowedRecipients("0x9534A77029D57E249c467E5A1E0854cc26Cd75A0")
    rewards_add_recipient_factory = interface.AddAllowedRecipient("0x734458219BE229F6631F083ea574EBACa2f9bEaf")
    rewards_remove_recipient_factory = interface.RemoveAllowedRecipient("0x5FEC0bcd7519C4fE41eca5Fe1dD94345fA100A67")
    rewards_registry = interface.AllowedRecipientRegistry("0x8fB566b1e78e603a86b97ada5FcA858764dF4088")

    call_script_items = [
        # 1. Add referral program top up EVM script factory 0x9534A77029D57E249c467E5A1E0854cc26Cd75A0
        add_evmscript_factory(
            factory=rewards_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(rewards_registry, "updateSpentAmount")[2:],
        ),
        # 2. Add referral program add recipient EVM script factory 0x734458219BE229F6631F083ea574EBACa2f9bEaf
        add_evmscript_factory(
            factory=rewards_add_recipient_factory,
            permissions=create_permissions(rewards_registry, "addRecipient"),
        ),
        # 3. Add referral program remove recipient EVM script factory 0x5FEC0bcd7519C4fE41eca5Fe1dD94345fA100A67
        add_evmscript_factory(
            factory=rewards_remove_recipient_factory,
            permissions=create_permissions(rewards_registry, "removeRecipient"),
        ),
    ]

    vote_desc_items = [
        "1) Add referral program top up EVM script factory 0x9534A77029D57E249c467E5A1E0854cc26Cd75A0",
        "2) Add referral program add recipient EVM script factory 0x734458219BE229F6631F083ea574EBACa2f9bEaf",
        "3) Add referral program remove recipient EVM script factory 0x5FEC0bcd7519C4fE41eca5Fe1dD94345fA100A67",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    vote_id, _ = start_vote({"from": get_deployer_account(), "max_fee": "300 gwei", "priority_fee": "2 gwei"})

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
