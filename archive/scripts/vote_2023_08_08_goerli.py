

"""
Voting 08/08/2023.
Add ET setup for Rewards Share program in stETH
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
    contracts,
    get_is_live,
    get_priority_fee,
)

from utils.easy_track import (
    add_evmscript_factory,
    create_permissions,
    remove_evmscript_factory
)


def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    rewards_share_topup_factory = interface.TopUpAllowedRecipients("0x5Bb391170899A7b8455A442cca65078ff3E1639C")
    rewards_share_add_recipient_factory = interface.AddAllowedRecipient("0x51916FC3D24CbE19c5e981ae8650668A1F5cF19B")
    rewards_share_remove_recipient_factory = interface.RemoveAllowedRecipient("0x932aab3D6057ed2Beef95471414831C4535600E9")
    rewards_share_registry = interface.AllowedRecipientRegistry("0x8b59609f4bEa230E565Ae0C3C7b6913746Df1cF2")

    call_script_items = [
        # 1.
        add_evmscript_factory(
            factory=rewards_share_topup_factory,
            permissions=create_permissions(contracts.finance, "newImmediatePayment")
            + create_permissions(rewards_share_registry, "updateSpentAmount")[2:],
        ),
        # 2.
        add_evmscript_factory(
            factory=rewards_share_add_recipient_factory,
            permissions=create_permissions(rewards_share_registry, "addRecipient"),
        ),
        # 3.
        add_evmscript_factory(
            factory=rewards_share_remove_recipient_factory,
            permissions=create_permissions(rewards_share_registry, "removeRecipient"),
        ),
    ]

    vote_desc_items = [
        "1) Add Rewards Share Program top up EVM script factory 0x5Bb391170899A7b8455A442cca65078ff3E1639C",
        "2) Add Rewards Share Program add recipient EVM script factory 0x51916FC3D24CbE19c5e981ae8650668A1F5cF19B",
        "3) Add Rewards Share Program remove recipient EVM script factory 0x932aab3D6057ed2Beef95471414831C4535600E9",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)
    return confirm_vote_script(vote_items, silent) and list(create_vote(vote_items, tx_params))


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
