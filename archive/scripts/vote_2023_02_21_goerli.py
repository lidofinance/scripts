"""
Voting 21/02/2023.
1. Add TRP top up EVM script factory 0x43f33C52156d1Fb2eA24d82aBfD342E69835E79f

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

    TRP_topup_factory = interface.TopUpAllowedRecipients("0x43f33C52156d1Fb2eA24d82aBfD342E69835E79f")
    TRP_registry = interface.AllowedRecipientRegistry("0x8C96a6522aEc036C4a384f8B7e05D93d6f3Dae39")

    call_script_items = [
        # 1. Add TRP top up EVM script factory 0x43f33C52156d1Fb2eA24d82aBfD342E69835E79f
        add_evmscript_factory(
            factory=TRP_topup_factory,
            permissions=create_permissions(finance, "newImmediatePayment")
            + create_permissions(TRP_registry, "updateSpentAmount")[2:],
        ),
    ]

    vote_desc_items = [
        "1) Add TRP top up EVM script factory 0x43f33C52156d1Fb2eA24d82aBfD342E69835E79f",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, silent) and create_vote(vote_items, tx_params)


def main():
    vote_id, _ = start_vote({"from": get_deployer_account(), "max_fee": "300 gwei", "priority_fee": "2 gwei"})

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
